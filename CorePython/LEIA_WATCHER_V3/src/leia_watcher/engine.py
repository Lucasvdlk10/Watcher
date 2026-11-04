"""Scan/reconcile, deterministic moves, journal recovery and guarded undo."""
import contextlib
import ctypes
import json
import os
import shutil
import stat
import threading
import time
from pathlib import Path
from .config import home,inside
from .db import Database,now
from .rules import evaluate,excluded,origin_evidence
from .security import safe_regular,fingerprint,digest,same

class Conflict(Exception):pass


def exclusive_check(path):
    """Windows shared-handle probe prevents moving known-open writers where possible."""
    if os.name!='nt':
        with open(path,'rb') as f:f.read(0)
        return
    from ctypes import wintypes
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    create=k.CreateFileW
    create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    create.restype=wintypes.HANDLE
    # READ access with sharing READ only: reject writers or deleters that cannot share.
    h=create(str(path),0x80000000,1,None,3,0x80,None)
    if h in (-1,ctypes.c_void_p(-1).value):raise PermissionError('ERR_NOT_STABLE: file is open/inaccessible')
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    k.CloseHandle(h)


def rename_no_replace(src,dst):
    """Atomic no-replace move within one volume, OS-specific."""
    if os.name=='nt':
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.MoveFileExW.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_ulong]
        if not k.MoveFileExW(str(src),str(dst),0):raise ctypes.WinError(ctypes.get_last_error())
        return
    # Linux renameat2 noreplace. If unavailable use link+unlink (same volume only).
    import platform
    libc=ctypes.CDLL(None,use_errno=True)
    if hasattr(libc,'renameat2'):
        rc=libc.renameat2(-100,os.fsencode(src),-100,os.fsencode(dst),1)
        if rc==0:return
        err=ctypes.get_errno()
        if err not in (38,22):raise OSError(err,os.strerror(err),str(src))
    os.link(src,dst,follow_symlinks=False)
    os.unlink(src)


def capture(path):
    f=fingerprint(path)
    f['sha256']=digest(path)
    return f


def ensure_dirs(root,target):
    p=Path(target).parent
    if not inside(root['path'],p):raise ValueError('ERR_PATH_UNSAFE: destination outside root')
    for d in reversed([p,*[a for a in p.parents if inside(root['path'],a) and str(a)!=str(Path(root['path']))]]):
        if not inside(root['path'],d):continue
        if not d.exists():d.mkdir(exist_ok=True)
        if d.is_symlink() or getattr(d.lstat(),'st_file_attributes',0)&0x400:raise ValueError('ERR_PATH_UNSAFE: destination via reparse point')


def clean_dirs(dirpath,stop):
    while dirpath!=stop and dirpath!=dirpath.parent:
        try:dirpath.rmdir()
        except OSError:break
        dirpath=dirpath.parent

class Watcher:
    def __init__(self,db,config,stability_delay=1.05):
        self.db=db;self.config=config;self.delay=stability_delay
        self.lock=threading.RLock()
        self.paused=set()
        self.stop=threading.Event()
        self.thread=None
        self.signatures={}
        self.last_reconcile={}
        # Retention maintenance must not block startup or the local IPC.
        self.last_retention=time.monotonic()
        self.last_errors={}
        self.native=None

    def roots(self):return {r['id']:r for r in self.config['roots']}

    def validate_root(self,rid):
        r=self.roots().get(rid)
        if not r:raise KeyError('Unknown root')
        return r

    def start(self):
        self.recover()
        if os.name=='nt':
            from .native import WindowsEvents
            self.native=WindowsEvents()
            self.native.start(self.config['roots'])
        self.thread=threading.Thread(target=self._loop,name='leia-observer',daemon=True)
        self.thread.start()

    def shutdown(self):
        self.stop.set()
        if self.native:self.native.close()
        if self.thread:self.thread.join(timeout=6)

    def _loop(self):
        """Periodic delta detection + full reconciliation; does not require cloud or watchdog."""
        while not self.stop.is_set():
            with self.lock:
                if time.monotonic()-self.last_retention > 86400:
                    self.db.prune_events(int(self.config.get('event_retention_days',90)))
                    self.last_retention=time.monotonic()
                notifications,overflows=self.native.drain() if self.native else ([],set())
                dirty={rid for rid,action,path in notifications}
                for rid,action,path in notifications:
                    if rid in self.roots() and path:
                        try:self.db.event(rid,action,path,source='WATCHER')
                        except Exception:pass
                    if action=='OVERFLOW':overflows.add(rid)
                for rid in overflows:
                    self.db.audit('EVENT_GAP','DEGRADED',rid,reason='ERR_WATCHER_OVERFLOW')
                    self.signatures.pop(rid,None)
                for rid,r in self.roots().items():
                    if not r.get('enabled',True) or rid in self.paused:continue
                    try:
                        # On Windows trust native hints for fast wakeups; full reconcile catches missed events.
                        before=self.signatures.get(rid)
                        if self.native and rid not in dirty and rid not in overflows and before is not None and time.monotonic()-self.last_reconcile.get(rid,0)<int(self.config.get('reconcile_interval_seconds',900)):
                            continue
                        current=self._snapshot(r)
                        first=before is None
                        if first or time.monotonic()-self.last_reconcile.get(rid,0)>=int(self.config.get('reconcile_interval_seconds',900)):
                            self.scan(rid,auto=True)
                            self.last_reconcile[rid]=time.monotonic()
                        elif current!=before:
                            removed=set(before)-set(current)
                            added=set(current)-set(before)
                            changed={p for p in current.keys()&before.keys() if current[p]!=before[p]}
                            if len(removed)+len(added)+len(changed)>20000:
                                self.db.audit('EVENT_GAP','DEGRADED',rid,reason='ERR_WATCHER_OVERFLOW')
                                self.scan(rid,auto=True)
                            else:
                                for p in sorted(added|changed):
                                    self.handle(r,Path(p),automated=True)
                                for p in sorted(removed):
                                    self.db.event(rid,'REMOVED',p,'','WATCHER')
                                    self.db.execute("UPDATE file_entries SET status='MISSING_UNCONFIRMED',updated_at=? WHERE root_id=? AND canonical_path=?",(now(),rid,p))
                            self.db.root_health(rid,'WATCHING')
                        self.signatures[rid]=self._snapshot(r)
                    except (OSError,ValueError,PermissionError) as exc:
                        self.last_errors[rid]=str(exc)
                        self.db.root_health(rid,'OFFLINE' if not Path(r['path']).exists() else 'DEGRADED')
                        self.db.audit('WATCH_ERROR','FAILED',rid,reason=type(exc).__name__,details={'error':str(exc)[:160]})
                        self.signatures.pop(rid,None)
            self.stop.wait(int(self.config.get('scan_interval_seconds',5)))

    def _walk(self,r):
        root=Path(r['path'])
        if not root.is_dir():raise FileNotFoundError('ERR_ROOT_UNAVAILABLE')
        if root.is_symlink():raise ValueError('ERR_PATH_UNSAFE')
        for base,dirs,files in os.walk(root,followlinks=False):
            safe_dirs=[]
            for d in dirs:
                p=Path(base)/d
                if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:continue
                if d in ('.git','node_modules','__pycache__','$RECYCLE.BIN','System Volume Information'):continue
                if r['mode']=='ORGANIZE' and inside(r.get('output_path') or Path(r['path'])/'_LEIA_Organizado',p):continue
                if inside(home(),p) or inside(p,home()):continue
                if any(excluded(p/('__dummy__'),r) for _ in (0,)):continue
                safe_dirs.append(d)
            dirs[:]=safe_dirs if r.get('recursive',True) else []
            for filename in files:
                p=Path(base)/filename
                if p.is_symlink() or excluded(p,r):continue
                try:
                    st=p.lstat()
                    if not stat.S_ISREG(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:continue
                except OSError:continue
                yield p,st

    def _snapshot(self,r):
        return {str(p):(s.st_size,s.st_mtime_ns,s.st_ino) for p,s in self._walk(r)}

    def scan(self,rid,auto=False,dry_run=False,limit=None):
        with self.lock:
            r=self.validate_root(rid)
            if not Path(r['path']).is_dir():
                self.db.root_health(rid,'OFFLINE');return {'error':'ERR_ROOT_UNAVAILABLE'}
            start=self.db.scan_begin(rid) if not dry_run else None
            counts={'indexed':0,'moved':0,'skipped':0,'errors':0,'preview':[]}
            complete=False
            try:
                if not dry_run:self._organize_loose_dirs(r)
                for p,st in self._walk(r):
                    if limit is not None and sum(counts[k] for k in ('indexed','moved','skipped','errors'))>=limit:break
                    if self.stop.is_set():break
                    try:
                        result=self.handle(r,p,dry_run=dry_run,automated=auto)
                        if result['action']=='MOVE':counts['moved']+=1
                        elif result['action']=='PREVIEW':counts['preview'].append(result);counts['indexed']+=1
                        elif result['action']=='INDEX':counts['indexed']+=1
                        else:counts['skipped']+=1
                    except (OSError,ValueError,Conflict) as e:
                        if isinstance(e,ValueError) and str(e).startswith('ERR_PATH_UNSAFE: hardlinked file'):
                            counts['skipped']+=1
                            self.db.audit('SCAN_FILE','SKIPPED',rid,reason='ERR_PATH_UNSAFE_HARDLINK',details={'file':str(p)})
                        else:
                            counts['errors']+=1
                            self.db.audit('SCAN_FILE','FAILED',rid,reason=type(e).__name__,details={'error':str(e)[:160],'file':str(p)})
                complete=True
            finally:
                if not dry_run and complete and not self.stop.is_set() and limit is None:self.db.scan_end(rid,start)
                elif not dry_run:self.db.root_health(rid,'DEGRADED')
            return counts

    def _organize_loose_dirs(self,r):
        """Move only non-standard top-level folders into Pastas avulsas.

        Category folders generated by the active rules are protected. This is
        intentionally limited to non-recursive in-place Downloads roots.
        """
        if not (r.get('mode')=='ORGANIZE' and r.get('organize_in_place') is True
                and r.get('recursive') is False and r.get('organize_loose_folders')):
            return 0
        root=Path(r['path']);target_name=r.get('loose_folders_target','Pastas avulsas')
        from .rules import component
        component(target_name)
        protected={target_name.casefold(),'_leia_organizado'}
        ruleset=r.get('ruleset',{})
        protected.update(str(x.get('target','')).casefold() for x in ruleset.get('rules',[]) if x.get('target'))
        if ruleset.get('fallback_folder'):protected.add(str(ruleset['fallback_folder']).casefold())
        destination_root=root/target_name
        moved=0
        for src in sorted(root.iterdir(),key=lambda p:p.name.casefold()):
            if not src.is_dir() or src.name.casefold() in protected:continue
            if src.is_symlink() or getattr(src.lstat(),'st_file_attributes',0)&0x400:continue
            if src.name in ('.git','node_modules','__pycache__','$RECYCLE.BIN','System Volume Information'):continue
            destination_root.mkdir(exist_ok=True)
            dst=destination_root/src.name
            if dst.exists():
                for i in range(2,10000):
                    candidate=destination_root/f'{src.name} ({i})'
                    if not candidate.exists():dst=candidate;break
                else:raise Conflict('ERR_NAME_COLLISION')
            rename_no_replace(src,dst)
            self.db.audit('LOOSE_FOLDER_MOVED','OK',r['id'],reason='PASTAS_AVULSAS',
                          details={'source':str(src),'destination':str(dst)})
            moved+=1
        return moved

    def stable(self,path,root):
        s=path.stat()
        # Creation age prevents rename while downloaded: three observations spread >= 2 seconds.
        state=(s.st_size,s.st_mtime_ns,s.st_ino)
        for _ in range(2):
            if self.stop.wait(self.delay):raise Conflict('Interrupted before stable')
            safe_regular(path,root)
            t=path.stat()
            if (t.st_size,t.st_mtime_ns,t.st_ino)!=state:raise Conflict('ERR_NOT_STABLE')
        exclusive_check(path)
        return t

    def handle(self,r,path,dry_run=False,automated=False):
        path=Path(path)
        if excluded(path,r):return {'action':'SKIP','reason':'EXCLUDED'}
        safe_regular(path,r)
        st=path.stat(); evidence=origin_evidence(path)
        dec=evaluate(r,path,st,evidence)
        if dry_run:return {'action':'PREVIEW','source':str(path),'destination':dec.target,'decision':dec.action,'reason':dec.reason,'rules':dec.rule_ids}
        fid=self.db.index(r['id'],r['path'],path,st,'INDEXED',evidence)
        if dec.action!='MOVE' or r['id'] in self.paused or not r.get('enabled',True):
            self.db.event(r['id'],'INDEX',path,'','SCAN' if not automated else 'WATCHER')
            return {'action':'INDEX','reason':dec.reason}
        # Successful scan is the only trigger of a move; no API read side effects.
        try:self.stable(path,r)
        except (Conflict,OSError,PermissionError) as exc:
            self.db.audit('STABILITY','SKIPPED',r['id'],reason='ERR_NOT_STABLE',details={'file':str(path),'error':str(exc)[:160]})
            return {'action':'SKIP','reason':'ERR_NOT_STABLE'}
        dest=self.move(r,path,Path(dec.target),fid)
        return {'action':'MOVE','destination':str(dest),'rules':dec.rule_ids}

    def move(self,r,src,dst,fid=None):
        with self.lock:
            if r['mode']!='ORGANIZE' or r['id'] in self.paused:raise Conflict('ROOT_IS_READONLY_OR_PAUSED')
            safe_regular(src,r)
            allowed=Path(r.get('output_path') or Path(r['path'])/'_LEIA_Organizado')
            if not inside(allowed,dst):raise Conflict('ERR_PATH_UNSAFE')
            if src==dst:raise Conflict('SOURCE_EQUALS_DESTINATION')
            if src.stat().st_dev!=Path(r['path']).stat().st_dev:raise Conflict('ERR_COPY_ACROSS_VOLUME')
            ensure_dirs(r,dst)
            if dst.parent.stat().st_dev!=src.stat().st_dev:raise Conflict('ERR_COPY_ACROSS_VOLUME')
            policy=r.get('conflict_policy','RENAME');backup=None
            if dst.exists():
                if policy=='SKIP':raise Conflict('ERR_NAME_COLLISION')
                if policy=='RENAME':
                    stem=dst.stem;suffix=dst.suffix
                    for i in range(2,10000):
                        candidate=dst.with_name(f'{stem} ({i}){suffix}')
                        if not candidate.exists():dst=candidate;break
                    else:raise Conflict('ERR_NAME_COLLISION')
                elif policy=='OVERWRITE':
                    if not r.get('allow_overwrite'):raise Conflict('ERR_OVERWRITE_DISALLOWED')
                    safe_regular(dst,r)
                    backup=home()/'backups'/'replaced'/r['id']/(dst.name+'.'+__import__('uuid').uuid4().hex+'.backup')
                    from .config import secured_dir
                    secured_dir(backup.parent)
            pre=capture(src)
            if not same(src,pre,pre['sha256']):raise Conflict('ERR_SOURCE_CHANGED')
            # Journal commit before any change.
            op=self.db.create_op(r['id'],fid,src,dst,pre,r.get('ruleset',{}),backup=backup)
            try:
                self.db.stage(op,'MOVING')
                if backup:
                    expected=capture(dst)
                    # On the same drive, preserve existing file without overwriting.
                    if backup.parent.stat().st_dev!=dst.stat().st_dev:raise Conflict('ERR_COPY_ACROSS_VOLUME_BACKUP')
                    rename_no_replace(dst,backup)
                    if digest(backup)!=expected['sha256']:raise Conflict('BACKUP_MISMATCH')
                if not same(src,pre,pre['sha256']):raise Conflict('ERR_SOURCE_CHANGED')
                safe_regular(src,r)
                rename_no_replace(src,dst)
                post=capture(dst)
                if post['sha256']!=pre['sha256'] or src.exists():raise Conflict('ERR_POSTCONDITION')
                self.db.stage(op,'MOVED',post)
                self.db.event(r['id'],'MOVED',dst,src,'WATCHER',op)
                try:
                    self.db.index(r['id'],r['path'],dst,dst.stat(),'MOVED',origin_evidence(dst))
                except OSError:pass
                return dst
            except BaseException as exc:
                self.db.stage(op,'NEEDS_ATTENTION',code='ERR_MOVE_UNCERTAIN',detail=str(exc))
                # If backup exists and destination is absent and source intact, restore backup safely.
                if backup and backup.exists() and not dst.exists():
                    try:rename_no_replace(backup,dst)
                    except OSError:pass
                raise

    def last_undo_eligible(self,rid=None):
        sql="SELECT * FROM operations o WHERE operation_kind='MOVE' AND stage='MOVED' AND NOT EXISTS (SELECT 1 FROM operations u WHERE u.undo_of_operation_id=o.operation_id AND u.stage IN ('UNDONE','UNDO_PREPARED','NEEDS_ATTENTION'))"
        args=[]
        if rid:sql+=' AND root_id=?';args.append(rid)
        sql+=' ORDER BY created_at DESC LIMIT 1'
        rows=self.db.rows(sql,args)
        return rows[0] if rows else None

    def undo(self,rid=None):
        with self.lock:
            op=self.last_undo_eligible(rid)
            if not op:raise Conflict('ERR_UNDO_NO_ELIGIBLE_OPERATION')
            src=Path(op['source_path']);dst=Path(op['destination_path'])
            root=self.roots().get(op['root_id'])
            if not root:
                saved=self.db.rows('SELECT config_json FROM watched_roots WHERE root_id=?',(op['root_id'],))
                if not saved:raise Conflict('ERR_UNDO_ROOT_UNKNOWN')
                root=json.loads(saved[0]['config_json'])
            if src.exists():raise Conflict('ERR_UNDO_CONFLICT: original source path occupied')
            post=json.loads(op['postcondition_json'] or '{}')
            if not same(dst,post,post.get('sha256')):raise Conflict('ERR_UNDO_CONFLICT: destination changed')
            safe_regular(dst,root)
            backup=Path(op['replaced_backup_path']) if op['replaced_backup_path'] else None
            if backup and not backup.is_file():raise Conflict('ERR_UNDO_CONFLICT: backup missing')
            ensure_dirs(root,src)
            reverse=self.db.create_op(op['root_id'],op['file_id'],dst,src,capture(dst),{'id':op['rule_set_id'],'version':op['rule_set_version']},kind='UNDO',undo_of=op['operation_id'])
            try:
                rename_no_replace(dst,src)
                if backup:rename_no_replace(backup,dst)
                self.db.stage(reverse,'UNDONE',capture(src))
                self.db.event(op['root_id'],'UNDONE',src,dst,'WATCHER',reverse)
                self.db.index(op['root_id'],root['path'],src,src.stat(),'INDEXED',origin_evidence(src))
                return {'operation_id':op['operation_id'],'undo_id':reverse,'restored':str(src)}
            except BaseException as exc:
                self.db.stage(reverse,'NEEDS_ATTENTION',code='ERR_UNDO_CONFLICT',detail=str(exc))
                raise

    def recover(self):
        for op in self.db.operations_pending():
            src,dst=Path(op['source_path']),Path(op['destination_path'])
            pre=json.loads(op['precondition_json'])
            try:
                if op['operation_kind']=='MOVE':
                    if dst.exists() and not src.exists() and digest(dst)==pre.get('sha256'):
                        self.db.stage(op['operation_id'],'MOVED',capture(dst))
                        self.db.audit('RECOVERY','OK',op['root_id'],op['operation_id'],'RECONCILED_MOVED')
                    elif src.exists() and not dst.exists() and not op['replaced_backup_path']:
                        self.db.stage(op['operation_id'],'FAILED',code='RECOVERED_NOT_MOVED')
                    else:self.db.stage(op['operation_id'],'NEEDS_ATTENTION',code='ERR_MOVE_UNCERTAIN')
                elif op['operation_kind']=='UNDO':
                    if dst.exists() and not src.exists() and digest(dst)==pre.get('sha256'):
                        self.db.stage(op['operation_id'],'UNDONE',capture(dst))
                    else:self.db.stage(op['operation_id'],'NEEDS_ATTENTION',code='ERR_UNDO_UNCERTAIN')
            except OSError:self.db.stage(op['operation_id'],'NEEDS_ATTENTION',code='RECOVERY_ACCESS_ERROR')
