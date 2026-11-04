import importlib.util
import json
import sqlite3
from pathlib import Path
import pytest

FILE=Path(__file__).parents[1]/'scripts'/'upgrade_helper.py'
spec=importlib.util.spec_from_file_location('upgrade_helper',FILE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_backup_restore_includes_wal_commits_and_preserves_secrets(tmp_path):
    data=tmp_path/'home';(data/'data').mkdir(parents=True)
    (data/'config.json').write_text('{"schema_version":1}')
    (data/'data'/'admin.secret').write_text('DO_NOT_COPY')
    db=sqlite3.connect(data/'data'/'watcher.db')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE a (id INTEGER, name TEXT)')
    db.execute('INSERT INTO a VALUES (1, "original")');db.commit()
    backup=tmp_path/'snap'
    mod.snapshot(data,backup)
    assert not (backup/'admin.secret').exists()
    assert not (backup/'data'/'admin.secret').exists()
    assert (backup/'manifest.json').exists()
    db.execute('DELETE FROM a');db.commit();db.close()
    (data/'config.json').write_text('{"schema_version":2}')
    mod.restore(data,backup)
    c=sqlite3.connect(data/'data'/'watcher.db')
    assert c.execute('SELECT name FROM a').fetchall()==[('original',)]
    c.close()
    assert json.loads((data/'config.json').read_text())['schema_version']==1
    assert (data/'data'/'admin.secret').read_text()=='DO_NOT_COPY'


def test_does_not_overwrite_an_existing_snapshot(tmp_path):
    a=tmp_path/'base';a.mkdir();b=tmp_path/'backup';b.mkdir()
    with pytest.raises(FileExistsError):mod.snapshot(a,b)


def test_bad_json_is_rejected_without_snapshot(tmp_path):
    a=tmp_path/'base';a.mkdir();(a/'config.json').write_text('not-json')
    with pytest.raises(ValueError):mod.snapshot(a,tmp_path/'backup')
