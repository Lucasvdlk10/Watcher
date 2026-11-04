"""Read-only, bounded dashboard queries through the existing authenticated IPC.

Deliberately separate from the Hermes HTTP API: no new HTTP write route.
"""

ENTITIES = {
    'files': ('file_entries', 'seen_at', ('file_id','filename','relative_path','root_id','extension','size_bytes','status','seen_at'),
              {'root_id':'root_id', 'extension':'extension','status':'status'}, ('filename','relative_path')),
    'audit': ('audit_events', 'audit_id', ('audit_id','occurred_at','action','outcome','reason_code','root_id'),
              {'root_id':'root_id', 'action':'action','outcome':'outcome'}, ('action','reason_code')),
    'operations': ('operations', 'created_at', ('operation_id','root_id','operation_kind','stage','source_path','destination_path','created_at','error_code'),
              {'root_id':'root_id','stage':'stage'}, ('source_path','destination_path','operation_kind')),
}


def ui_list(db, entity, *, filters=None, page=0, limit=40):
    if entity not in ENTITIES: raise ValueError('Invalid entity')
    if not isinstance(page,int) or page<0 or page>100000:raise ValueError('Invalid page')
    if not isinstance(limit,int) or not 1<=limit<=100:raise ValueError('Invalid limit')
    filters=filters or {}
    if not isinstance(filters,dict):raise ValueError('Invalid filters')
    if entity=='files':return _ui_files(db,filters,page,limit)
    table,order,columns,allowed,search=ENTITIES[entity]
    parts=[];params=[]
    for key,value in filters.items():
        if value is None or value=='':continue
        if not isinstance(value,str) or len(value)>240:raise ValueError('Invalid filter value')
        if key=='q':
            escaped=value.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            parts.append('('+ ' OR '.join(f'{name} LIKE ? ESCAPE \'\\\'' for name in search)+')')
            params.extend(['%'+escaped+'%']*len(search))
        elif key in allowed:
            parts.append(allowed[key]+'=?');params.append(value)
        else:raise ValueError('Unknown filter')
    where=(' WHERE '+' AND '.join(parts)) if parts else ''
    # Fixed identifiers come exclusively from the table above; filters are SQL parameters.
    total=db.rows('SELECT COUNT(*) AS n FROM '+table+where,tuple(params))[0]['n']
    sql=f'SELECT {", ".join(columns)} FROM {table}{where} ORDER BY {order} DESC LIMIT ? OFFSET ?'
    items=db.rows(sql,tuple(params+[limit,page*limit]))
    return {'items':items,'total':total,'page':page,'limit':limit,'has_more':(page+1)*limit<total}


def _ui_files(db,filters,page,limit):
    """Unified current + imported Downloads Watcher catalog.

    Current file_entries win when the same normalized path exists in both
    databases. Legacy rows stay searchable without pretending they were seen
    by the current filesystem scanner.
    """
    allowed={'root_id':'root_id','extension':'extension','status':'status'}
    parts=[];params=[]
    for key,value in filters.items():
        if value is None or value=='':continue
        if not isinstance(value,str) or len(value)>240:raise ValueError('Invalid filter value')
        if key=='q':
            escaped=value.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            parts.append("(filename LIKE ? ESCAPE '\\' OR relative_path LIKE ? ESCAPE '\\')")
            params.extend(['%'+escaped+'%','%'+escaped+'%'])
        elif key in allowed:parts.append(allowed[key]+'=?');params.append(value)
        else:raise ValueError('Unknown filter')
    where=(' WHERE '+' AND '.join(parts)) if parts else ''
    catalog='''WITH catalog AS (
      SELECT file_id,filename,relative_path,root_id,extension,size_bytes,status,seen_at,canonical_path AS source_path
      FROM file_entries
      UNION ALL
      SELECT 'legacy:'||l.event_id,l.name,l.current_path,'root-downloads',l.extension,l.size_bytes,'LEGACY',l.ts,l.current_path
      FROM legacy_download_events l
      WHERE NOT EXISTS (
        SELECT 1 FROM file_entries f
        WHERE lower(replace(f.canonical_path,'/',char(92)))=lower(replace(l.current_path,'/',char(92)))
      )
    )'''
    total=db.rows(catalog+' SELECT COUNT(*) AS n FROM catalog'+where,tuple(params))[0]['n']
    columns='file_id,filename,relative_path,root_id,extension,size_bytes,status,seen_at'
    items=db.rows(catalog+f' SELECT {columns} FROM catalog{where} ORDER BY seen_at DESC LIMIT ? OFFSET ?',
                  tuple(params+[limit,page*limit]))
    return {'items':items,'total':total,'page':page,'limit':limit,'has_more':(page+1)*limit<total}


def ui_snapshot(db, engine):
    roots=db.rows('SELECT root_id,name,canonical_path,mode,health,enabled,last_scan_finished_at FROM watched_roots ORDER BY name')
    current_count=db.rows('SELECT COUNT(*) AS n FROM file_entries')[0]['n']
    legacy_count=db.rows('SELECT COUNT(*) AS n FROM legacy_download_events')[0]['n']
    count=db.rows('''SELECT COUNT(*) AS n FROM (
      SELECT lower(replace(canonical_path,'/',char(92))) AS path_key FROM file_entries
      UNION
      SELECT lower(replace(current_path,'/',char(92))) AS path_key FROM legacy_download_events
    )''')[0]['n']
    undo_count=db.rows("SELECT COUNT(*) AS n FROM operations o WHERE o.operation_kind='MOVE' AND o.stage='MOVED' AND NOT EXISTS (SELECT 1 FROM operations u WHERE u.undo_of_operation_id=o.operation_id AND u.stage IN ('UNDONE','UNDO_PREPARED','NEEDS_ATTENTION'))")[0]['n']
    return {'undo_eligible':undo_count,'roots':roots,'files_count':count,
            'current_files_count':current_count,'legacy_files_count':legacy_count,
            'pending':len(db.operations_pending()),
            'paused':list(engine.paused),'database':db.health(),
            'recent':db.rows('SELECT occurred_at,action,outcome,reason_code,root_id FROM audit_events ORDER BY audit_id DESC LIMIT 6'),
            'no_llm':True,'hermes_read_only':True,'api_host':'127.0.0.1'}
