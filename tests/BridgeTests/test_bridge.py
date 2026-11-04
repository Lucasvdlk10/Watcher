import importlib.util
import io
import json
import pathlib
import sys
from unittest.mock import Mock

SOURCE=pathlib.Path(__file__).resolve().parents[2] / 'Bridge' / 'watcher_bridge.py'
modspec=importlib.util.spec_from_file_location('watcher_bridge_v4',SOURCE)
bridge=importlib.util.module_from_spec(modspec)
modspec.loader.exec_module(bridge)


def test_bad_command_disallowed():
    import pytest
    with pytest.raises(ValueError):
        bridge.safe_request('stop',{})


def test_args_size_guard():
    import pytest
    with pytest.raises(ValueError):
        bridge.safe_request('ping',{'a':'a'*150001})


def test_incorrect_payload_rejected():
    import pytest
    with pytest.raises(ValueError):
        bridge.safe_request('status', [1,2])


def test_malformed_stdio_fails_closed():
    buf=io.StringIO()
    bridge.serve(['not-json\n'],buf)
    x=json.loads(buf.getvalue())
    assert x['ok'] is False and 'Traceback' not in x['error']


def test_denied_activation_without_confirmation(monkeypatch):
    import leia_watcher.admin
    admin_call=Mock()
    monkeypatch.setattr(leia_watcher.admin,'request',admin_call)
    import pytest
    with pytest.raises(PermissionError):
        bridge.safe_request('activate',{'root_id':'x'})
    admin_call.assert_not_called()


def test_valid_ping_uses_core_admin_ipc(monkeypatch):
    import leia_watcher.admin
    request=Mock(return_value={'version':'3.0.0','db':'ok','no_llm':True})
    monkeypatch.setattr(leia_watcher.admin,'request',request)
    r=bridge.safe_request('ping',{})
    assert r['no_llm'] and request.call_args.args[0]=='ping'


def test_origin_filter_runs_before_pagination(monkeypatch):
    import leia_watcher.admin
    def fake(command, **kw):
        assert command=='ui_list' and kw['entity']=='files'
        rows=[{'status':'LEGACY','filename':'old-a'},{'status':'PRESENT','filename':'new-a'},
              {'status':'LEGACY','filename':'old-b'},{'status':'PRESENT','filename':'new-b'}]
        return {'items':rows,'has_more':False}
    monkeypatch.setattr(leia_watcher.admin,'request',fake)
    result=bridge.safe_request('ui_files_origin',{'origin':'Históricos','page':1,'limit':1,'filters':{}})
    assert result['total']==2 and result['items'][0]['filename']=='old-b'


def test_rules_apply_requires_confirmation(monkeypatch):
    import leia_watcher.admin
    from leia_watcher.config import new_root
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as d:
        r=new_root('Samples',d,'TRACK_ONLY')
        monkeypatch.setattr(leia_watcher.admin,'request',lambda command,**a:[r] if command=='roots' else None)
        import pytest
        with pytest.raises(PermissionError):
            bridge.safe_request('rules_apply',{'root_id':r['id'],'rows':[],'steps':['type']})


def test_rule_validation_does_not_write(monkeypatch):
    import leia_watcher.admin
    from leia_watcher.config import new_root
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as d:
        r=new_root('Samples',d,'TRACK_ONLY');calls=[]
        def fake(cmd,**a):
            calls.append(cmd)
            if cmd=='roots':return [r]
            raise AssertionError('Unexpected mutation')
        monkeypatch.setattr(leia_watcher.admin,'request',fake)
        result=bridge.safe_request('rules_validate',{'root_id':r['id'],'rows':[],'steps':['type']})
        assert result['valid'] and calls==['roots']
