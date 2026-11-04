from pathlib import Path
from types import SimpleNamespace
import os
import pytest
from leia_watcher.rules import component,validate_rules,evaluate,extension,excluded,origin_evidence
from leia_watcher.config import new_root,validate

@pytest.mark.parametrize('name', ['..','CON','.','', 'aux.txt', 'com1', 'x:y','foo/hi','a\\b','bad.','bad ','__'*200])
def test_malicious_component(name):
    with pytest.raises(ValueError):component(name)

@pytest.mark.parametrize('name,expected',[('name.tar.gz','.tar.gz'),('test.PDF','.pdf'),('README',''),('archive.zip','.zip')])
def test_extension(name,expected):assert extension(name)==expected

def test_type_then_date(env):
    root,r,*_=env;r['mode']='ORGANIZE';r['ruleset']['path_steps']=['type','date']
    p=root/'photo.jpg';p.write_bytes(b'a');st=p.stat()
    dec=evaluate(r,p,st)
    assert dec.action=='MOVE' and '/Imagens/' in dec.target.replace('\\','/')
    assert 'photos' not in dec.target

def test_track_only_unchanged(env):
    root,r,*_=env;p=root/'hello.txt';p.write_text('ok')
    assert evaluate(r,p,p.stat()).action=='INDEX'

def test_fallback(env):
    root,r,*_=env;r['mode']='ORGANIZE';r['ruleset']['path_steps']=['type']
    p=root/'unsure.mystery';p.write_text('x')
    assert 'Outros' in evaluate(r,p,p.stat()).target

def test_keyword(env):
    root,r,*_=env;r['mode']='ORGANIZE';r['ruleset']['path_steps']=['keyword'];r['ruleset']['rules']=[{'id':'bill','kind':'keyword','target':'Financeiro','keywords':['ação']}]
    p=root/'acao-outubro.txt';p.write_text('a')
    assert '/Financeiro/' in evaluate(r,p,p.stat()).target.replace('\\','/')

def test_size_band(env):
    root,r,*_=env;r['mode']='ORGANIZE';r['ruleset']['path_steps']=['size'];r['ruleset']['size_bands']=[{'label':'Grande','min_bytes':0,'max_bytes':None}]
    p=root/'x.x';p.write_bytes(b'123')
    assert '/Grande/' in evaluate(r,p,p.stat()).target.replace('\\','/')

def test_source_evidence_unknown(env):
    root,r,*_=env;p=root/'mail.eml';p.write_text('x')
    assert origin_evidence(p)['category']=='UNKNOWN'

def test_bad_bands():
    with pytest.raises(ValueError):validate_rules({'size_bands':[{'label':'A','min_bytes':0,'max_bytes':10},{'label':'B','min_bytes':9,'max_bytes':20}]})

def test_bad_duplicate_rule():
    with pytest.raises(ValueError):validate_rules({'rules':[{'id':'x','kind':'type','extensions':[]},{'id':'x','kind':'type','extensions':[]}]})

def test_output_excluded(env):
    root,r,*_=env;r['mode']='ORGANIZE'
    p=root/'_LEIA_Organizado'/'file.txt'
    assert excluded(p,r)

def test_in_place_output_does_not_exclude_root_files(env):
    root,r,cfg,*_=env
    r['mode']='ORGANIZE';r['output_path']=str(root);r['organize_in_place']=True;r['recursive']=False;r['ruleset']['path_steps']=['type']
    validate(cfg)
    p=root/'arquivo.zip';p.write_bytes(b'x')
    assert not excluded(p,r)
    dec=evaluate(r,p,p.stat())
    assert Path(dec.target).parent == root/'Compactados'

@pytest.mark.parametrize('filename',['part.crdownload','abc.part','thing.tmp','~$test.xlsx'])
def test_temporary_files_excluded(env,filename):
    root,r,*_=env
    assert excluded(root/filename,r)

def test_overlapping_roots_block(env):
    root,r,cfg,*_=env
    new=new_root('nested',str(root),'ORGANIZE');new['path']=str(root)
    cfg['roots'].append(new)
    with pytest.raises(ValueError):validate(cfg)

def test_origin_not_inferred_by_folder(env):
    root,r,*_=env;p=root/'email'/'letter.docx';p.parent.mkdir();p.write_text('x')
    assert origin_evidence(p)['category']=='UNKNOWN'
