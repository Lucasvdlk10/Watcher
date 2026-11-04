import pytest
from leia_watcher.ui_prefs import load_mode,set_mode

def test_ui_preference_is_separate_from_core(tmp_path,monkeypatch):
    monkeypatch.setenv('LEIA_WATCHER_HOME',str(tmp_path))
    assert load_mode()=='auto'
    set_mode('off');assert load_mode()=='off'
    set_mode('reduced');assert load_mode()=='reduced'
    assert not (tmp_path/'config.json').exists()

@pytest.mark.parametrize('bad',['full',None,True,'120fps',''])
def test_bad_motion_disallowed(tmp_path,monkeypatch,bad):
    monkeypatch.setenv('LEIA_WATCHER_HOME',str(tmp_path))
    with pytest.raises(ValueError):set_mode(bad)
