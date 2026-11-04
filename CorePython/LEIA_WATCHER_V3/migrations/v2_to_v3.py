"""Watcher 2 -> 3 data migration gate (NO-OP).

V3 only changes UI and package metadata. Schema version remains 1.
Explicitly inspect existing data before upgrading without rewriting it.
"""
import json
import sqlite3
from pathlib import Path


def validate_compatible(data_home):
    home=Path(data_home)
    cfg=json.loads((home/'config.json').read_text(encoding='utf-8'))
    if cfg.get('schema_version') != 1:
        raise RuntimeError('Expected Watcher config schema 1; no automatic migration attempted')
    db_path=home/'data'/'watcher.db'
    if not db_path.is_file():
        raise RuntimeError('Existing SQLite database not found')
    c=sqlite3.connect(f'file:{db_path.as_posix()}?mode=ro',uri=True)
    try:
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('SQLite integrity check failed')
        names={x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'watched_roots','file_entries','operations','audit_events'}.issubset(names):
            raise RuntimeError('Database tables missing; upgrade canceled')
    finally:c.close()
    return {'config_schema':1,'db_integrity':'ok','migration':'NOOP','filesystem_changes':0}


if __name__=='__main__':
    import sys
    print(json.dumps(validate_compatible(sys.argv[1]),ensure_ascii=False))
