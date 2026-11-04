"""Offline, stdlib-only consistent SQLite upgrade backup/rollback.

Run ONLY while Watcher core is confirmed stopped. Never copy a live SQLite
file: sqlite3.Connection.backup() handles WAL. No secret keys are exported.
"""
import argparse
import json
import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def snapshot(data, dest):
    data,dest=Path(data).resolve(),Path(dest).resolve()
    dest.mkdir(parents=True,exist_ok=False)
    os.chmod(dest,0o700)
    config=data/'config.json'
    if config.exists():
        json.loads(config.read_text(encoding='utf8'))
        shutil.copy2(config,dest/'config.json')
    db=data/'data'/'watcher.db'
    if db.exists():
        source=sqlite3.connect(f'file:{db.as_posix()}?mode=ro',uri=True)
        target=sqlite3.connect(str(dest/'watcher.db'))
        try:
            source.backup(target)
            assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite backup invalid'
        finally:target.close();source.close()
    (dest/'manifest.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
        'has_config':config.exists(),'has_db':db.exists(),'contains_secrets':False},indent=2),encoding='utf8')
    return dest


def restore(data, backup):
    data,backup=Path(data).resolve(),Path(backup).resolve()
    m=json.loads((backup/'manifest.json').read_text(encoding='utf8'))
    if m.get('has_db'):
        db=backup/'watcher.db'
        conn=sqlite3.connect(str(db));ok=conn.execute('PRAGMA integrity_check').fetchone()[0];conn.close()
        if ok!='ok':raise RuntimeError('Backup SQLite failed integrity_check')
    # The installer must have stopped the core before this is called.
    (data/'data').mkdir(parents=True,exist_ok=True)
    if m.get('has_config'):
        json.loads((backup/'config.json').read_text(encoding='utf8'))
        shutil.copy2(backup/'config.json',data/'config.json')
    if m.get('has_db'):
        for suffix in ('-wal','-shm'):
            stale=data/'data'/('watcher.db'+suffix)
            if stale.exists():stale.unlink()
        shutil.copy2(backup/'watcher.db',data/'data'/'watcher.db')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=('snapshot','restore','check'))
    ap.add_argument('data');ap.add_argument('backup')
    args=ap.parse_args()
    if args.action=='snapshot':snapshot(args.data,args.backup)
    elif args.action=='restore':restore(args.data,args.backup)
    else:
        db=Path(args.data)/'data'/'watcher.db'
        if db.exists():
            c=sqlite3.connect(str(db));assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';c.close()
    print(args.action.upper()+'_OK')
if __name__=='__main__':main()
