import hashlib
from importlib.resources import files


def test_interface_uses_watcher_specific_logo_assets():
    assets=files('leia_watcher').joinpath('assets')
    expected={
        'leia_watcher_48.png':'a6fb62c8fda93f57965398056b48080cee1192439892169edf23c6f78e6765fb',
        'leia_watcher_256.png':'1282bc99fc893fd3009e23b22c5c7937e7ab0489543de634150159b462c44541',
    }
    for name,digest in expected.items():
        assert hashlib.sha256(assets.joinpath(name).read_bytes()).hexdigest()==digest
