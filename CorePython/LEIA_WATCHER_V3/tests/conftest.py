import os
from pathlib import Path
import pytest
from leia_watcher.config import new_root, validate
from leia_watcher.db import Database
from leia_watcher.engine import Watcher

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv('LEIA_WATCHER_HOME',str(tmp_path/'app'))
    root=tmp_path/'samples';root.mkdir()
    r=new_root('Sample',str(root),'TRACK_ONLY')
    cfg={'schema_version':1,'api':{'host':'127.0.0.1','port':8766},'scan_interval_seconds':5,'reconcile_interval_seconds':900,'roots':[r]}
    validate(cfg)
    db=Database();db.apply_roots(cfg['roots'])
    engine=Watcher(db,cfg,stability_delay=.002)
    yield root,r,cfg,db,engine
    engine.stop.set();db.close()
