import json
from pathlib import Path
import pytest
from leia_watcher.admin import Admin
from leia_watcher.config import load

def test_admin_add_organize_is_disabled(env):
    root,r,c,db,e=env
    adm=Admin(e,db)
    new_dir=root.parent/'other';new_dir.mkdir()
    res=adm.dispatch('add_root',{'name':'Downloads','path':str(new_dir),'mode':'ORGANIZE'})
    assert res['root']['enabled'] is False
    assert len(load()['roots'])==2

def test_admin_add_uses_directory_name_when_display_name_blank(env):
    root,r,c,db,e=env;adm=Admin(e,db)
    new_dir=root.parent/'Projetos do Lucas';new_dir.mkdir()
    res=adm.dispatch('add_root',{'name':'','path':str(new_dir),'mode':'TRACK_ONLY'})
    assert res['root']['name']=='Projetos do Lucas'

def test_admin_add_organization_profile_and_activate(env):
    root,r,c,db,e=env;adm=Admin(e,db)
    new_dir=root.parent/'incoming';new_dir.mkdir()
    res=adm.dispatch('add_root',{'name':'','path':str(new_dir),'mode':'ORGANIZE',
        'organization_profile':'TYPE_DATE','activate':True,'confirmation':'I_CONFIRM_FILE_MOVES'})
    added=res['root']
    assert added['enabled'] is True
    assert added['output_path']==str(new_dir.resolve())
    assert added['organize_in_place'] is True and added['recursive'] is False
    assert added['ruleset']['path_steps']==['type','date']

def test_admin_rejects_unknown_organization_profile(env):
    root,r,c,db,e=env;adm=Admin(e,db)
    new_dir=root.parent/'incoming';new_dir.mkdir()
    with pytest.raises(ValueError,match='organization profile'):
        adm.dispatch('add_root',{'name':'X','path':str(new_dir),'mode':'ORGANIZE','organization_profile':'MAGIC'})

def test_admin_activation_confirmation(env):
    root,r,c,db,e=env
    r['mode']='ORGANIZE';r['enabled']=False
    from leia_watcher.config import validate
    validate(c)
    adm=Admin(e,db)
    with pytest.raises(PermissionError):adm.dispatch('activate',{'root_id':r['id']})

def test_admin_roots_command(env):
    root,r,c,db,e=env
    adm=Admin(e,db)
    assert adm.dispatch('roots',{})[0]['id']==r['id']

def test_admin_forbidden(env):
    root,r,c,db,e=env
    with pytest.raises(ValueError):Admin(e,db).dispatch('delete_all_files',{})

def test_admin_config_invalid_preserves_previous(env):
    root,r,c,db,e=env;adm=Admin(e,db)
    bad=json.loads(json.dumps(r));bad['mode']='DELETOR'
    with pytest.raises(ValueError):adm.dispatch('update_root',{'root':bad})
    assert e.config['roots'][0]['mode']=='TRACK_ONLY'

def test_backup_integrity(env):
    root,r,c,db,e=env
    path=Admin(e,db).dispatch('backup',{})['path']
    from sqlite3 import connect
    with connect(path) as d:assert d.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

def test_export_csv(env,tmp_path):
    root,r,c,db,e=env
    out=tmp_path/'export.csv'
    x=Admin(e,db).dispatch('export',{'kind':'audit','path':str(out)})
    assert out.exists() and x['exported']==0

def test_pause_resume(env):
    root,r,c,db,e=env;adm=Admin(e,db)
    adm.dispatch('pause',{'root_id':r['id']});assert r['id'] in e.paused
    adm.dispatch('resume',{'root_id':r['id']});assert r['id'] not in e.paused
