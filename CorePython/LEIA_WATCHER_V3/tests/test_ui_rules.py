import copy
import pytest
from leia_watcher.ui_rules import apply_rows,rule_values,split_csv
from leia_watcher.rules import validate_rules

@pytest.fixture
def rs():
    return {'id':'rules-original','version':8,'path_steps':['type'],
            'fallback_folder':'Outros','creation_fallback':'MTIME','size_bands':[],
            'rules':[{'id':'a','kind':'type','target':'Imagens','extensions':['.png','.jpg'],
                      'enabled':True,'priority':99,'custom_legacy':42}]}

def test_preserves_unknown_fields_and_rule_ids(rs):
    before=copy.deepcopy(rs)
    result=apply_rows(rs,[{'id':'a','kind':'type','target':'Fotos','values':'.webp, .png','enabled':False}],['type'])
    assert rs==before
    assert result['id']=='rules-original'
    assert result['version']==8
    assert result['rules'][0]['id']=='a'
    assert result['rules'][0]['custom_legacy']==42
    assert result['rules'][0]['extensions']==['.webp','.png']
    assert result['rules'][0]['enabled'] is False

@pytest.mark.parametrize('kind,vals,expected',[('type','.png, .jpeg',['.png','.jpeg']),
 ('keyword','contrato, urgente',['contrato','urgente']),('source','WEB, UNKNOWN',['WEB','UNKNOWN'])])
def test_editor_maps_list_values(rs,kind,vals,expected):
    r=apply_rows(rs,[{'id':'foo','kind':kind,'target':'Coisas','values':vals}], [kind])['rules'][0]
    field={'type':'extensions','keyword':'keywords','source':'categories'}[kind]
    assert r[field]==expected
    assert rule_values(r).split(', ')==expected


def test_size_bytes(rs):
    r=apply_rows(rs,[{'id':'size-1','kind':'size','target':'Grandes','values':'1024, 2048'}],['size'])['rules'][0]
    assert r['min_bytes']==1024 and r['max_bytes']==2048
    assert rule_values(r)=='1024, 2048'


def test_date(rs):
    r=apply_rows(rs,[{'id':'time','kind':'date','values':'YYYY/MM'}],['date'])['rules'][0]
    assert r['pattern']=='YYYY/MM'


@pytest.mark.parametrize('value',['../outside','C:\\system','com1','Outros/Docs'])
def test_prevent_unsafe_folder_names(rs,value):
    with pytest.raises(ValueError):apply_rows(rs,[],['type'],value)


def test_duplicate_ids_rejected(rs):
    row={'id':'a','kind':'type','target':'Docs','values':'.pdf'}
    with pytest.raises(ValueError):apply_rows(rs,[row,row],['type'])


def test_ruleset_version_kept_for_atomic_admin_increment(rs):
    updated=apply_rows(rs,[{'id':'a','kind':'type','target':'Imagens','values':'.png'}],['type','date'])
    assert updated['version']==8
    assert updated['path_steps']==['type','date']


def test_csv_input():
    assert split_csv(' abc, , def,  ') == ['abc','def']
