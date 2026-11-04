"""Authenticated local admin IPC. No write-capable HTTP endpoint exists."""
import csv
import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from multiprocessing.connection import Listener,Client
from pathlib import Path
from .config import home,load,validate,write_atomic,new_root,secured_dir
from .security import secret
from .db import now


def address():
    if os.name=='nt':
        import getpass
        import hashlib
        who=hashlib.sha256((getpass.getuser()+str(home())).encode()).hexdigest()[:20]
        return r'\\.\pipe\LEIAWatcher-'+who
    return str(home()/'data'/'admin.sock')

def family():return 'AF_PIPE' if os.name=='nt' else 'AF_UNIX'

def request(command,**args):
    key=bytes.fromhex(secret('admin.secret'))
    conn=Client(address(),family=family(),authkey=key)
    try:
        conn.send({'command':command,'args':args})
        if not conn.poll(60):raise TimeoutError('Admin service did not respond')
        result=conn.recv()
        if not result['ok']:raise RuntimeError(result['error'])
        return result['result']
    finally:conn.close()

class Admin:
    def __init__(self,engine,db):
        self.engine=engine;self.db=db;self.jobs={};self.listener=None;self.closed=False
    def start(self):
        addr=address()
        if os.name!='nt' and Path(addr).exists():
            # Running core holds a lock; stale socket can be safely deleted.
            Path(addr).unlink()
        self.listener=Listener(addr,family=family(),authkey=bytes.fromhex(secret('admin.secret')))
        if os.name!='nt':os.chmod(addr,0o600)
        threading.Thread(target=self._loop,name='leia-admin',daemon=True).start()
    def shutdown(self):
        self.closed=True
        try:self.listener.close()
        except Exception:pass
        if os.name!='nt':
            try:Path(address()).unlink()
            except OSError:pass
    def _loop(self):
        while not self.closed:
            try:conn=self.listener.accept()
            except (OSError,EOFError):break
            threading.Thread(target=self._worker,args=(conn,),daemon=True).start()
    def _worker(self,conn):
        try:
            message=conn.recv()
            if not isinstance(message,dict):raise ValueError('Invalid command')
            result=self.dispatch(message.get('command'),message.get('args') or {})
            conn.send({'ok':True,'result':result})
        except Exception as exc:
            try:conn.send({'ok':False,'error':f'{type(exc).__name__}: {exc}'})
            except Exception:pass
        finally:conn.close()
    def _update(self,config):
        old=self.engine.config
        old_by_id={r['id']:r for r in old['roots']}
        for r in config['roots']:
            prev=old_by_id.get(r['id'])
            if prev:
                old_rules=dict(prev.get('ruleset',{}));new_rules=dict(r.get('ruleset',{}))
                old_rules.pop('version',None);new_rules.pop('version',None)
                policies_changed=any(r.get(k)!=prev.get(k) for k in ('exclusions','conflict_policy','allow_overwrite','output_path','mode'))
                if (old_rules!=new_rules or policies_changed) and int(r.get('ruleset',{}).get('version',1))<=int(prev.get('ruleset',{}).get('version',1)):
                    r['ruleset']['version']=int(prev['ruleset'].get('version',1))+1
        validate(config)
        with self.engine.lock:
            db_backup=self.db.backup()
            try:
                self.db.apply_roots(config['roots'])
                write_atomic(home()/'config.json',config)
                self.engine.config=config
                self.engine.signatures.clear()
                if self.engine.native:
                    # Rebind observers after configuration changes; retains existing active handlers.
                    self.engine.native.start(config['roots'])
                self.db.audit('CONFIG_APPLY','OK',reason='CONFIG_VERSION_1',details={'roots':len(config['roots'])})
            except Exception:
                # If db mutation succeeded but file write failed, immediately sync previous roots.
                try:self.db.apply_roots(old['roots'])
                except Exception:pass
                raise
        return {'status':'applied','roots':len(config['roots']),'backup':db_backup}
    def dispatch(self,cmd,p):
        e=self.engine;db=self.db
        if cmd=='ping':return {'version':'3.0.0','no_llm':True,'db':db.health()}
        if cmd=='status':
            return {'roots':db.rows('SELECT root_id,name,canonical_path,mode,health,enabled,last_scan_finished_at FROM watched_roots ORDER BY name'),
              'paused':list(e.paused),'jobs':self.jobs,'pending':len(db.operations_pending()),'database':db.health()}
        if cmd=='ui_snapshot':
            from .ui_queries import ui_snapshot
            return ui_snapshot(db,e)
        if cmd=='ui_list':
            from .ui_queries import ui_list
            return ui_list(db,p['entity'],filters=p.get('filters',{}),page=p.get('page',0),limit=p.get('limit',40))
        if cmd=='roots':return e.config['roots']
        if cmd=='add_root':
            selected=Path(p['path']).expanduser().resolve()
            display_name=str(p.get('name','')).strip() or selected.name or str(selected)
            r=new_root(display_name,str(selected),p.get('mode','TRACK_ONLY'))
            if r['mode']=='ORGANIZE':
                profiles={'TYPE':['type'],'TYPE_DATE':['type','date'],'DATE':['date']}
                profile=p.get('organization_profile','TYPE')
                if profile not in profiles:raise ValueError('Invalid organization profile')
                r['ruleset']['path_steps']=profiles[profile]
                r['output_path']=str(selected);r['organize_in_place']=True;r['recursive']=False
                r['organize_loose_folders']=bool(p.get('organize_loose_folders',False))
                r['loose_folders_target']='Pastas avulsas'
                activate=bool(p.get('activate',False))
                if activate and p.get('confirmation')!='I_CONFIRM_FILE_MOVES':
                    raise PermissionError('Explicit confirmation of file moves is required')
                r['enabled']=activate
            c=json.loads(json.dumps(e.config));c['roots'].append(r)
            return {'root':r,'apply':self._update(c)}
        if cmd=='update_root':
            r=p['root'];rid=r['id'];c=json.loads(json.dumps(e.config))
            if not any(x['id']==rid for x in c['roots']):raise KeyError('Unknown root')
            c['roots']=[r if x['id']==rid else x for x in c['roots']]
            return self._update(c)
        if cmd=='remove_root':
            c=json.loads(json.dumps(e.config));rid=p['root_id']
            c['roots']=[r for r in c['roots'] if r['id']!=rid]
            e.paused.discard(rid)
            return self._update(c)
        if cmd=='activate':
            rid=p['root_id'];r=e.validate_root(rid)
            if r['mode']=='ORGANIZE' and p.get('confirmation') != 'I_CONFIRM_FILE_MOVES':raise PermissionError('Explicit confirmation of file moves is required')
            c=json.loads(json.dumps(e.config))
            for x in c['roots']:
                if x['id']==rid:x['enabled']=True
            result=self._update(c)
            result['job']=self._start_scan(rid)
            return result
        if cmd=='pause':
            with e.lock:e.paused.add(p['root_id']);db.root_health(p['root_id'],'PAUSED')
            return {'paused':p['root_id']}
        if cmd=='resume':
            with e.lock:e.paused.discard(p['root_id']);e.signatures.pop(p['root_id'],None)
            return {'resumed':p['root_id']}
        if cmd=='preview':
            return e.scan(p['root_id'],dry_run=True,limit=min(int(p.get('limit',50)),200))
        if cmd=='scan':return {'job':self._start_scan(p['root_id'])}
        if cmd=='job':return self.jobs.get(p['job_id'],{'error':'Unknown job'})
        if cmd=='undo':return e.undo(p.get('root_id'))
        if cmd=='backup':return {'path':db.backup()}
        if cmd=='export':
            kind=p.get('kind','audit')
            if kind not in ('audit','operations','files'):raise ValueError('Invalid export type')
            table={'audit':'audit_events','operations':'operations','files':'file_entries'}[kind]
            path=Path(p['path']).expanduser().absolute()
            if path.suffix.lower() not in ('.csv','.json'):raise ValueError('Only JSON or CSV exports are supported')
            # Exports are explicit local admin actions, never API download endpoints.
            rows=db.rows('SELECT * FROM '+table+' ORDER BY rowid DESC LIMIT 100000')
            if kind=='operations':
                for r in rows:
                    for key in ('precondition_json','postcondition_json','source_hash_sha256'):r.pop(key,None)
            if path.suffix.lower()=='.json':
                write_atomic(path,rows)
            else:
                secured_dir(path.parent)
                with open(path,'w',newline='',encoding='utf-8-sig') as fh:
                    writer=csv.DictWriter(fh,fieldnames=list(rows[0]) if rows else ['empty'])
                    writer.writeheader();writer.writerows(rows)
            return {'exported':len(rows),'path':str(path)}
        if cmd=='files':return db.rows('SELECT filename,relative_path,root_id,size_bytes,status,seen_at FROM file_entries ORDER BY seen_at DESC LIMIT 200')
        if cmd=='audit':return db.rows('SELECT audit_id,occurred_at,action,outcome,reason_code,root_id FROM audit_events ORDER BY audit_id DESC LIMIT 200')
        if cmd=='operations':return db.rows('SELECT operation_id,root_id,stage,source_path,destination_path,created_at,error_code FROM operations ORDER BY created_at DESC LIMIT 200')
        if cmd=='stop':
            e.stop.set()
            return {'stopping':True}
        raise ValueError('Unknown or forbidden command')
    def _start_scan(self,rid):
        job=uuid.uuid4().hex[:12];self.jobs[job]={'status':'RUNNING','root_id':rid,'started_at':now()}
        def runner():
            try:
                result=self.engine.scan(rid)
                self.jobs[job]={'status':'DONE','result':result,'finished_at':now()}
            except Exception as exc:
                self.jobs[job]={'status':'FAILED','error':str(exc),'finished_at':now()}
        threading.Thread(target=runner,name=f'scan-{rid}',daemon=True).start()
        return job
