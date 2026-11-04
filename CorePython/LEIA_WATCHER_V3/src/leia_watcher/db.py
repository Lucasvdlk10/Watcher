"""Serialized SQLite ledger and versioned root configuration."""
import contextlib
import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime,timezone
from pathlib import Path
from .config import home,secured_dir

def now():return datetime.now(timezone.utc).isoformat()
def j(x):return json.dumps(x,ensure_ascii=False,default=str)

class Database:
    def __init__(self,path=None):
        self.path=Path(path or home()/"data"/"watcher.db")
        secured_dir(self.path.parent)
        self.lock=threading.RLock()
        self.con=sqlite3.connect(str(self.path),timeout=5,isolation_level=None,check_same_thread=False)
        self.con.row_factory=sqlite3.Row
        self.con.execute('PRAGMA foreign_keys=ON')
        self.con.execute('PRAGMA journal_mode=WAL')
        self.con.execute('PRAGMA busy_timeout=5000')
        if __import__('os').name != 'nt':
            try:__import__('os').chmod(self.path,0o600)
            except OSError:pass
        self._init()

    def _init(self):
        import importlib.resources
        sql=importlib.resources.files('leia_watcher').joinpath('schema.sql').read_text(encoding='utf8')
        with self.lock:
            self.con.executescript(sql)
            checksum=hashlib.sha256(sql.encode()).hexdigest()
            self.con.execute('INSERT OR IGNORE INTO schema_migrations VALUES (?,?,?)',(1,now(),checksum))
            # Avoid a full multi-gigabyte ledger scan on every startup.
            # Full integrity_check remains an explicit diagnostic/backup gate.
            self.con.execute('PRAGMA schema_version').fetchone()

    def execute(self,sql,args=()):
        with self.lock:return self.con.execute(sql,args)

    def rows(self,sql,args=()):
        with self.lock:return [dict(x) for x in self.con.execute(sql,args).fetchall()]

    @contextlib.contextmanager
    def txn(self):
        with self.lock:
            self.con.execute('BEGIN IMMEDIATE')
            try:
                yield self.con
                self.con.execute('COMMIT')
            except BaseException:
                self.con.execute('ROLLBACK')
                raise

    def apply_roots(self,roots):
        with self.txn() as c:
            old={r['root_id'] for r in c.execute('SELECT root_id FROM watched_roots')}
            new={r['id'] for r in roots}
            for r in roots:
                # preserve history when a root is removed: disable rather than delete
                output=r.get('output_path') or (str(Path(r['path'])/'_LEIA_Organizado') if r['mode']=='ORGANIZE' else None)
                fields=(r['id'],r['name'],str(Path(r['path']).resolve()),r['mode'],int(r.get('enabled',True)),int(r.get('recursive',True)),output,j(r),r.get('ruleset',{}).get('id','rules'),int(r.get('ruleset',{}).get('version',1)),now(),now())
                c.execute('''INSERT INTO watched_roots(root_id,name,canonical_path,mode,enabled,recursive,output_path,config_json,ruleset_id,ruleset_version,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(root_id) DO UPDATE SET
                name=excluded.name,canonical_path=excluded.canonical_path,mode=excluded.mode,enabled=excluded.enabled,recursive=excluded.recursive,output_path=excluded.output_path,config_json=excluded.config_json,ruleset_id=excluded.ruleset_id,ruleset_version=excluded.ruleset_version,updated_at=excluded.updated_at''',fields)
                s=r.get('ruleset',{})
                c.execute('INSERT OR IGNORE INTO rule_sets(ruleset_id,version,root_id,definition_json,applied_at) VALUES(?,?,?,?,?)',(s.get('id','rules'),int(s.get('version',1)),r['id'],j(s),now()))
                c.execute('INSERT OR IGNORE INTO checkpoints(root_id,needs_rescan,updated_at) VALUES(?,1,?)',(r['id'],now()))
                c.execute('UPDATE checkpoints SET needs_rescan=1,reason=?,updated_at=? WHERE root_id=?',('CONFIG_APPLY',now(),r['id']))
            for rid in old-new:
                c.execute('UPDATE watched_roots SET enabled=0,health=?,updated_at=? WHERE root_id=?',('REMOVED',now(),rid))

    def root_health(self,rid,health):
        self.execute('UPDATE watched_roots SET health=?,updated_at=? WHERE root_id=?',(health,now(),rid))

    def scan_begin(self,rid):
        stamp=now()
        self.execute('UPDATE watched_roots SET health=?,last_scan_started_at=? WHERE root_id=?',('SCANNING',stamp,rid))
        return stamp

    def scan_end(self,rid,stamp):
        with self.txn() as c:
            c.execute('UPDATE watched_roots SET health=?,last_scan_finished_at=? WHERE root_id=?',('WATCHING',now(),rid))
            c.execute("UPDATE file_entries SET status='MISSING_UNCONFIRMED',updated_at=? WHERE root_id=? AND seen_at<? AND status IN ('INDEXED','SEEN')",(now(),rid,stamp))
            c.execute('UPDATE checkpoints SET last_successful_scan_at=?,scan_generation=scan_generation+1,needs_rescan=0,reason=NULL,updated_at=? WHERE root_id=?',(now(),now(),rid))

    def event(self,rid,etype,path=None,old_path=None,source='SCAN',operation_id=None):
        with self.txn() as c:
            cur=c.execute('INSERT INTO fs_events(root_id,observed_at,event_type,path,old_path,source,processed,operation_id) VALUES(?,?,?,?,?,?,?,?)',(rid,now(),etype,str(path) if path else None,str(old_path) if old_path else None,source,1,operation_id))
            return cur.lastrowid

    def audit(self,action,outcome,rid=None,opid=None,reason='',details=None,actor='core'):
        with self.txn() as c:
            return c.execute('INSERT INTO audit_events(operation_id,root_id,occurred_at,action,outcome,reason_code,safe_details_json,actor) VALUES(?,?,?,?,?,?,?,?)',(opid,rid,now(),action,outcome,reason,j(details or {}),actor)).lastrowid

    def index(self,rid,rootpath,path,st,status='INDEXED',origin=None,seen=None):
        from .rules import extension
        from .security import fingerprint
        f=fingerprint(path)
        ident=f'{f["dev"]}:{f["ino"]}'
        file_id=uuid.uuid5(uuid.NAMESPACE_URL,f'{rid}/{ident}').hex
        rel=str(Path(path).relative_to(Path(rootpath)))
        fields=(file_id,rid,rel,str(path),ident,Path(path).name,extension(Path(path).name),st.st_size,
            (datetime.fromtimestamp(getattr(st,'st_birthtime',st.st_ctime if __import__('os').name=='nt' else st.st_mtime),timezone.utc).isoformat() if hasattr(st,'st_birthtime') or __import__('os').name=='nt' else None),
            datetime.fromtimestamp(st.st_mtime,timezone.utc).isoformat(),seen or now(),now(),status,
            (origin or {}).get('category','UNKNOWN'),j(origin or {}),j({'mtime_ns':st.st_mtime_ns}),now())
        with self.txn() as c:
            # A file recreated at the same path may have a different inode.
            c.execute('DELETE FROM file_entries WHERE root_id=? AND relative_path=? AND file_id<>?',(rid,rel,file_id))
            c.execute('''INSERT INTO file_entries(file_id,root_id,relative_path,canonical_path,identity_key,filename,extension,size_bytes,created_at_fs,modified_at_fs,seen_at,last_verified_at,status,origin_category,origin_evidence_json,file_attrs_json,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET relative_path=excluded.relative_path,canonical_path=excluded.canonical_path,filename=excluded.filename,extension=excluded.extension,size_bytes=excluded.size_bytes,created_at_fs=excluded.created_at_fs,modified_at_fs=excluded.modified_at_fs,seen_at=excluded.seen_at,last_verified_at=excluded.last_verified_at,status=excluded.status,origin_category=excluded.origin_category,origin_evidence_json=excluded.origin_evidence_json,file_attrs_json=excluded.file_attrs_json,updated_at=excluded.updated_at''',fields)
        return file_id

    def operations_pending(self):
        return self.rows("SELECT * FROM operations WHERE stage IN ('PREPARED','MOVING','UNDO_PREPARED') ORDER BY created_at")

    def create_op(self,rid,fid,src,dst,pre,rule,kind='MOVE',undo_of=None,backup=None):
        op=uuid.uuid4().hex
        with self.txn() as c:
            c.execute('''INSERT INTO operations(operation_id,root_id,file_id,operation_kind,source_path,destination_path,stage,rule_set_id,rule_set_version,reason_code,precondition_json,source_size_bytes,source_identity,source_mtime_ns,source_hash_sha256,replaced_backup_path,undo_of_operation_id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (op,rid,fid,kind,str(src),str(dst),'PREPARED' if kind=='MOVE' else 'UNDO_PREPARED',rule.get('id'),rule.get('version',1),'RULE_MATCH' if kind=='MOVE' else 'USER_UNDO',j(pre),pre.get('size'),f"{pre.get('dev')}:{pre.get('ino')}",pre.get('mtime_ns'),pre.get('sha256'),str(backup) if backup else None,undo_of,now()))
        self.audit('OPERATION_PREPARED','OK',rid,op,'PREPARED',{'source':str(src),'destination':str(dst)})
        return op

    def stage(self,opid,stage,post=None,code=None,detail=None):
        with self.txn() as c:
            c.execute('''UPDATE operations SET stage=?, postcondition_json=COALESCE(?,postcondition_json), error_code=?,error_detail=?,started_at=COALESCE(started_at,?),completed_at=CASE WHEN ? IN ('MOVED','UNDONE','FAILED','NEEDS_ATTENTION') THEN ? ELSE completed_at END WHERE operation_id=?''',
                      (stage,j(post) if post else None,code,str(detail)[:200] if detail else None,now(),stage,now(),opid))
        self.audit('OPERATION_STAGE',stage,opid=opid,reason=code or stage)

    def prune_events(self,days=90):
        from datetime import timedelta
        if days<7 or days>3650:raise ValueError('Retention must be between 7 and 3650 days')
        cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        with self.txn() as c:
            rows=c.execute('DELETE FROM fs_events WHERE observed_at<?',(cutoff,)).rowcount
        if rows:self.audit('EVENT_RETENTION','OK',reason='RETENTION_DAYS',details={'deleted':rows,'days':days})
        return rows

    def backup(self,target=None):
        target=Path(target or home()/"backups"/(f'watcher-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.db'))
        secured_dir(target.parent)
        with self.lock:
            dest=sqlite3.connect(target)
            try:self.con.backup(dest); dest.close()
            finally:
                if dest:dest.close()
        return str(target)

    def health(self):
        self.execute('SELECT 1').fetchone()
        return 'ok'
    def close(self):
        with self.lock:self.con.close()
