import pytest
from leia_watcher.ui_queries import ui_list,ui_snapshot
from leia_watcher.db import Database


@pytest.mark.parametrize('entity',['files','audit','operations'])
def test_empty_table(db_env,entity):
    db,_=db_env
    result=ui_list(db,entity)
    assert result=={'items':[],'total':0,'page':0,'limit':40,'has_more':False}


@pytest.fixture
def db_env(tmp_path,monkeypatch):
    monkeypatch.setenv('LEIA_WATCHER_HOME',str(tmp_path/'app'))
    db=Database()
    yield db,tmp_path
    db.close()


@pytest.mark.parametrize('bad_entity',['../../data','fs_events','users','','FILES',None])
def test_no_raw_table_access(db_env,bad_entity):
    db,_=db_env
    with pytest.raises((ValueError,TypeError)):ui_list(db,bad_entity)


@pytest.mark.parametrize('page,limit',[(0,0),(0,101),(-1,40),(100001,10),('2',40),(0,'50')])
def test_bounded_pagination(db_env,page,limit):
    db,_=db_env
    with pytest.raises(ValueError):ui_list(db,'files',page=page,limit=limit)


@pytest.mark.parametrize('filters',[{'bogus':'x'},{'q':5},{'q':'x'*241},'text',{'root_id':5}])
def test_rejects_unsafe_filters(db_env,filters):
    db,_=db_env
    with pytest.raises(ValueError):ui_list(db,'files',filters=filters)


def test_pagination_search_does_not_expose_private_payload(db_env):
    db,path=db_env
    root=path/'samples';root.mkdir()
    from leia_watcher.config import new_root
    config=new_root('Safe',str(root))
    db.apply_roots([config])
    for filename in ('test%_alpha.pdf','book.docx','notes.pdf'):
        f=root/filename;f.write_bytes(b'safe');db.index(config['id'],root,f,f.stat())
    result=ui_list(db,'files',filters={'q':'%'},limit=1)
    assert result['total']==1
    assert result['items'][0]['filename']=='test%_alpha.pdf'
    assert 'canonical_path' not in result['items'][0]
    result2=ui_list(db,'files',filters={'q':'_alpha'})
    assert result2['total']==1
    result3=ui_list(db,'files',filters={'root_id':config['id']},limit=2,page=1)
    assert result3['total']==3
    assert result3['has_more'] is False
    assert len(result3['items'])==1


def test_snapshot_is_read_only(db_env):
    db,_=db_env
    class E: paused=set()
    result=ui_snapshot(db,E())
    assert result['no_llm'] is True
    assert result['hermes_read_only'] is True
    assert result['files_count']==0
    assert result['current_files_count']==0
    assert result['legacy_files_count']==0
    assert result['database']=='ok'
    assert 'admin.secret' not in str(result)


def _legacy(db,event_id,name,path,ts='2026-01-01T00:00:00+00:00'):
    with db.txn() as c:
        c.execute('''INSERT INTO legacy_download_events(event_id,ts,action,status,name,extension,category,original_path,current_path,size_bytes,undone,imported_at,source_database)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (event_id,ts,'MOVE','OK',name,'.pdf','PDFs',path,path,123,0,ts,'legacy.sqlite'))


def test_snapshot_counts_current_and_legacy_catalog(db_env):
    db,path=db_env
    root=path/'samples';root.mkdir()
    from leia_watcher.config import new_root
    config=new_root('Safe',str(root));db.apply_roots([config])
    f=root/'current.pdf';f.write_bytes(b'x');db.index(config['id'],root,f,f.stat())
    _legacy(db,'old-1','old.pdf',str(root/'old.pdf'))
    class E: paused=set()
    snap=ui_snapshot(db,E())
    assert snap['current_files_count']==1
    assert snap['legacy_files_count']==1
    assert snap['files_count']==2


def test_files_list_includes_legacy_and_deduplicates_current_path(db_env):
    db,path=db_env
    root=path/'samples';root.mkdir()
    from leia_watcher.config import new_root
    config=new_root('Safe',str(root));db.apply_roots([config])
    f=root/'same.pdf';f.write_bytes(b'x');db.index(config['id'],root,f,f.stat())
    _legacy(db,'old-same','same.pdf',str(f))
    _legacy(db,'old-only','old.pdf',str(root/'old.pdf'))
    result=ui_list(db,'files')
    assert result['total']==2
    names={x['filename']:x['status'] for x in result['items']}
    assert names['same.pdf']!='LEGACY'
    assert names['old.pdf']=='LEGACY'
