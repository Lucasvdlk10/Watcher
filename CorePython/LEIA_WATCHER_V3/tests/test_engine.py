from pathlib import Path
import json
import pytest
from leia_watcher.config import validate
from leia_watcher.engine import Conflict,Watcher
from leia_watcher.db import now


def org(env):
    root,r,cfg,db,e=env
    r['mode']='ORGANIZE';r['enabled']=True
    validate(cfg);db.apply_roots([r])
    return root,r,cfg,db,e

def test_track_scan_no_moves(env):
    root,r,cfg,db,e=env
    p=root/'myfile.pdf';p.write_bytes(b'data')
    result=e.scan(r['id'])
    assert result['indexed']==1 and p.read_bytes()==b'data'
    assert len(db.rows('SELECT * FROM operations'))==0

def test_organize_move_and_undo(env):
    root,r,cfg,db,e=org(env)
    p=root/'original.pdf';p.write_bytes(b'abc123')
    result=e.scan(r['id'])
    assert result['moved']==1
    moved=list((root/'_LEIA_Organizado').rglob('original.pdf'))
    assert len(moved)==1 and moved[0].read_bytes()==b'abc123'
    ret=e.undo();assert ret['restored']==str(p)
    assert p.read_bytes()==b'abc123' and not moved[0].exists()
    assert len(db.rows("SELECT * FROM operations WHERE stage='UNDONE'"))==1

def test_in_place_organizes_file_and_loose_folder(env):
    root,r,cfg,db,e=env
    r['mode']='ORGANIZE';r['output_path']=str(root);r['organize_in_place']=True;r['recursive']=False;r['ruleset']['path_steps']=['type']
    r['organize_loose_folders']=True;r['loose_folders_target']='Pastas avulsas'
    db.apply_roots(cfg['roots'])
    archive=root/'novo.zip';archive.write_bytes(b'zip')
    loose=root/'Projeto solto';loose.mkdir();(loose/'a.txt').write_text('a')
    (root/'Compactados').mkdir()
    result=e.scan(r['id'])
    assert result['moved']==1
    assert (root/'Compactados'/'novo.zip').is_file()
    assert (root/'Pastas avulsas'/'Projeto solto'/'a.txt').is_file()
    assert (root/'Compactados').is_dir()

def test_collision_rename(env):
    root,r,cfg,db,e=org(env);r['ruleset']['path_steps']=['type'];db.apply_roots([r])
    p=root/'a.pdf';p.write_bytes(b'latest')
    out=root/'_LEIA_Organizado'/'Documentos';out.mkdir(parents=True);(out/'a.pdf').write_bytes(b'keep')
    assert e.scan(r['id'])['moved']==1
    assert (out/'a.pdf').read_bytes()==b'keep'
    assert (out/'a (2).pdf').read_bytes()==b'latest'


def test_hardlinked_build_artifact_is_safely_skipped_without_failure(env):
    root,r,cfg,db,e=env
    original=root/'artifact.bin';original.write_bytes(b'build-cache')
    linked=root/'artifact-link.bin'
    import os
    os.link(original,linked)
    result=e.scan(r['id'])
    assert result['errors']==0
    assert result['skipped']==2
    audit=db.rows("SELECT action,outcome,reason_code FROM audit_events WHERE action='SCAN_FILE'")
    assert audit and all(row['outcome']=='SKIPPED' for row in audit)
    assert all(row['reason_code']=='ERR_PATH_UNSAFE_HARDLINK' for row in audit)


def test_skip_collision(env):
    root,r,cfg,db,e=org(env);r['ruleset']['path_steps']=['type'];r['conflict_policy']='SKIP'
    p=root/'a.pdf';p.write_text('original');out=root/'_LEIA_Organizado'/'Documentos';out.mkdir(parents=True);(out/'a.pdf').write_text('existing')
    assert e.scan(r['id'])['errors']==1
    assert p.read_text()=='original' and (out/'a.pdf').read_text()=='existing'

def test_undo_changed_destination_fails(env):
    root,r,cfg,db,e=org(env);p=root/'a.pdf';p.write_bytes(b'original')
    assert e.scan(r['id'])['moved']==1
    dst=next((root/'_LEIA_Organizado').rglob('a.pdf'))
    dst.write_bytes(b'changed')
    with pytest.raises(Conflict,match='changed'):e.undo()
    assert not p.exists() and dst.read_bytes()==b'changed'

def test_undo_collision_fails(env):
    root,r,cfg,db,e=org(env);p=root/'a.pdf';p.write_bytes(b'original')
    assert e.scan(r['id'])['moved']==1
    p.write_bytes(b'unrelated')
    with pytest.raises(Conflict,match='occupied'):e.undo()
    assert p.read_bytes()==b'unrelated'

def test_repeated_scan_idempotent(env):
    root,r,cfg,db,e=org(env);p=root/'one.pdf';p.write_bytes(b'abc')
    assert e.scan(r['id'])['moved']==1
    assert e.scan(r['id'])['moved']==0
    assert len(db.rows("SELECT * FROM operations WHERE operation_kind='MOVE'"))==1

def test_dry_run_no_mutation(env):
    root,r,cfg,db,e=org(env);p=root/'a.pdf';p.write_bytes(b'data')
    res=e.scan(r['id'],dry_run=True)
    assert res['preview'][0]['decision']=='MOVE'
    assert p.exists() and len(db.rows('SELECT * FROM operations'))==0

def test_paused_no_move(env):
    root,r,cfg,db,e=org(env)
    e.paused.add(r['id']);p=root/'pause.pdf';p.write_bytes(b'data')
    assert e.scan(r['id'])['indexed']==1 and p.exists()

def test_recovery_postrename_before_sql(env):
    root,r,cfg,db,e=org(env);p=root/'doc.pdf';p.write_bytes(b'important')
    from leia_watcher.engine import capture,ensure_dirs,rename_no_replace
    d=root/'_LEIA_Organizado'/'x.pdf';ensure_dirs(r,d)
    o=db.create_op(r['id'],None,p,d,capture(p),r['ruleset']);db.stage(o,'MOVING');rename_no_replace(p,d)
    e.recover();assert db.rows('SELECT stage FROM operations WHERE operation_id=?',(o,))[0]['stage']=='MOVED'
    assert d.read_bytes()==b'important'

def test_recovery_ambiguous_preserves_bytes(env):
    root,r,cfg,db,e=org(env)
    from leia_watcher.engine import capture
    p=root/'a.pdf';p.write_text('src');d=root/'b.pdf';d.write_text('dst')
    o=db.create_op(r['id'],None,p,d,capture(p),r['ruleset'])
    e.recover();assert db.rows('SELECT stage FROM operations WHERE operation_id=?',(o,))[0]['stage']=='NEEDS_ATTENTION'
    assert p.exists() and d.exists()

def test_remove_marks_unconfirmed(env):
    root,r,cfg,db,e=env;p=root/'a.txt';p.write_text('123')
    e.scan(r['id']);p.unlink();e.scan(r['id'])
    assert db.rows('SELECT status FROM file_entries')[0]['status']=='MISSING_UNCONFIRMED'

def test_offline_preserves_inventory(env):
    root,r,cfg,db,e=env;p=root/'a.txt';p.write_text('x')
    e.scan(r['id']);p.unlink();root.rmdir()
    assert e.scan(r['id'])['error']=='ERR_ROOT_UNAVAILABLE'
    assert db.rows('SELECT status FROM file_entries')[0]['status']=='INDEXED'

def test_duplicate_scan_root_hash(env):
    root,r,cfg,db,e=env;p=root/'hello';p.write_text('x')
    e.scan(r['id']);e.scan(r['id'])
    assert len(db.rows('SELECT * FROM file_entries'))==1

def test_overwrite_backup_and_undo(env):
    root,r,cfg,db,e=org(env);r['ruleset']['path_steps']=['type'];r['conflict_policy']='OVERWRITE';r['allow_overwrite']=True
    validate(cfg)
    p=root/'a.pdf';p.write_text('new-file')
    out=root/'_LEIA_Organizado'/'Documentos';out.mkdir(parents=True);d=out/'a.pdf';d.write_text('previous-file')
    assert e.scan(r['id'])['moved']==1
    assert d.read_text()=='new-file'
    assert e.undo()['restored']==str(p)
    assert p.read_text()=='new-file' and d.read_text()=='previous-file'
