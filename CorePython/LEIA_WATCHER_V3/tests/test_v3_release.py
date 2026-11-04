"""V3-specific release regression tests. No edits to a real user home."""
from pathlib import Path
from importlib.resources import files
import inspect
import json

from leia_watcher import __version__,admin,api,engine,ui,ui_kit,ui_prefs
from leia_watcher.config import initial_config,validate

ROOT=Path(__file__).parents[1]

def test_v3_package_and_semantics():
    assert __version__=='3.0.0'
    assert admin.Admin.dispatch is not None
    assert 'ui_snapshot' in inspect.getsource(admin.Admin.dispatch)
    assert "'version':'3.0.0'" in inspect.getsource(admin.Admin.dispatch)

def test_official_assets_present_locally():
    a=files('leia_watcher').joinpath('assets')
    for name in ('leia_watcher_256.png','leia_watcher_48.png','leia_dark.ico','obsidian_wave.png'):
        assert a.joinpath(name).is_file(),name
    for key,_,_ in ui.PAGES:
        for st in ('active','idle'):
            assert a.joinpath(f'nav_{key}_{st}.png').is_file()

def test_gui_is_actual_core_client_not_fake_data():
    text=inspect.getsource(ui.App)
    assert "request('ui_snapshot')" in text
    assert "request('roots')" in text
    assert "request('ui_list'" in text
    assert "subprocess.Popen([sys.executable,'-m','leia_watcher.main']" in text
    assert 'fake_data' not in text and 'Math.random' not in text

def test_ui_mode_and_no_read_write_network():
    assert ui_prefs.VALID_MODES=={'auto','reduced','off'}
    assert 'http' not in inspect.getsource(ui.App._load_all)
    assert '#090A0C'==ui_kit.BG
    assert '#F4F5F6'==ui_kit.FG

def test_baseline_contract_guards_still_in_core():
    cfg=initial_config()
    assert cfg['api']['host']=='127.0.0.1'
    assert cfg['roots']==[]
    validate(cfg)
    source=inspect.getsource(api)
    assert 'POST' not in source or '405' in source
    assert '127.0.0.1' in inspect.getsource(admin) or '127.0.0.1' in source

def test_wheel_has_no_internet_dependencies():
    project=(ROOT/'pyproject.toml').read_text()
    assert 'dependencies = []' in project
    assert 'PySide6' not in project
    assert 'QtWebEngine' not in project

def test_upgrade_is_v2_inplace_and_data_safe():
    installer=(ROOT/'scripts/install.ps1').read_text()
    rollback=(ROOT/'scripts/rollback.ps1').read_text()
    for token in ('2.0.0','3.0.0','snapshot','--no-index','--no-deps','--force-reinstall', 'config.json','upgrade_helper.py'):
        assert token in installer
    assert 'latest-v3.txt' in installer and 'latest-v3.txt' in rollback
    assert 'RestoreSnapshot' in rollback
    assert 'RESTAURAR-DADOS' in rollback
    assert '2.0.0' in rollback

def test_original_configuration_preserved_in_upgrade():
    install=(ROOT/'scripts/install.ps1').read_text()
    assert 'new_root' not in install
    assert 'Copy-Item -LiteralPath $OldWheel' in install  # only wheel copied, never Downloads
    assert 'Remove-Item -Recurse' not in install
    assert 'write_atomic' not in install

def test_home_uses_existing_windows_location():
    from leia_watcher import config
    assert 'LEIA' in inspect.getsource(config.home)
    assert 'Watcher' in inspect.getsource(config.home)


def test_explicit_noop_migration_is_safe(tmp_path):
    import importlib.util,sqlite3
    path=ROOT/'migrations/v2_to_v3.py'
    spec=importlib.util.spec_from_file_location('leia_v3_migration',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    data=tmp_path/'home';(data/'data').mkdir(parents=True)
    (data/'config.json').write_text('{"schema_version":1}',encoding='utf8')
    con=sqlite3.connect(data/'data'/'watcher.db')
    for t in ('watched_roots','file_entries','operations','audit_events'):
        con.execute(f'CREATE TABLE {t}(id INTEGER)')
    con.commit();con.close()
    before=(data/'data'/'watcher.db').read_bytes()
    assert module.validate_compatible(data)['migration']=='NOOP'
    assert (data/'data'/'watcher.db').read_bytes()==before
    assert r'migrations\v2_to_v3.py' in (ROOT/'scripts/install.ps1').read_text()
