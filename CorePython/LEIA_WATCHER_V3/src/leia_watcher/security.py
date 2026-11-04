"""Local secrets, robust path validation and fingerprint helpers."""
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from .config import home, secured_dir, inside


def secret(name):
    p=home()/"data"/name
    secured_dir(p.parent)
    if p.exists():return p.read_text(encoding='ascii').strip()
    value=secrets.token_hex(32)
    fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='ascii') as f:f.write(value)
    if os.name=='nt':
        import subprocess
        # On NTFS, deny inherited broad ACEs; failure is reported rather than silently granting access.
        who=os.environ.get('USERNAME','')
        if who:
            pth=str(p)
            r=subprocess.run(['icacls',pth,'/inheritance:r','/grant:r',f'{who}:R'],capture_output=True)
            if r.returncode!=0:raise PermissionError('Could not restrict secret file ACL')
    return value


def safe_regular(path,root,strict=True):
    """Reject links and reparse points at every path segment before mutation."""
    p=Path(path).absolute(); base=Path(root['path']).absolute()
    if not inside(base,p):raise ValueError('ERR_PATH_UNSAFE: escapes root')
    rel=p.relative_to(base)
    for node in [base]+[base.joinpath(*rel.parts[:i]) for i in range(1,len(rel.parts)+1)]:
        try:s=node.lstat()
        except FileNotFoundError:
            if strict:raise
            continue
        if node.is_symlink() or getattr(s,'st_file_attributes',0)&0x400:
            raise ValueError('ERR_PATH_UNSAFE: symlink or reparse point')
    if strict:
        s=p.stat()
        if not stat.S_ISREG(s.st_mode):raise ValueError('ERR_PATH_UNSAFE: not regular file')
        if s.st_nlink>1:raise ValueError('ERR_PATH_UNSAFE: hardlinked file')
    return p


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def fingerprint(path):
    s=Path(path).stat()
    return {'size':s.st_size,'mtime_ns':s.st_mtime_ns,'dev':s.st_dev,'ino':s.st_ino}


def same(path, snap, hash_value=None):
    try:
        f=fingerprint(path)
        if any(f[k]!=snap[k] for k in ('size','mtime_ns','dev','ino')):return False
        return hash_value is None or digest(path)==hash_value
    except OSError:return False
