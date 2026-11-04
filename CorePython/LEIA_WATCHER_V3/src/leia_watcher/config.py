"""Versioned configuration with all dangerous operations opt-in."""
import json
import os
import tempfile
import uuid
from pathlib import Path

APP_VERSION = 1


def home():
    base = os.environ.get("LEIA_WATCHER_HOME")
    return Path(base).expanduser().resolve() if base else (Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "LEIA" / "Watcher").resolve()


def initial_config():
    return {"schema_version": 1, "api": {"host": "127.0.0.1", "port": 8766}, "scan_interval_seconds": 5, "reconcile_interval_seconds": 900, "roots": []}


def secured_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(path, 0o700)
    return path


def write_atomic(path, value):
    path = Path(path)
    secured_dir(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=".leia_", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def load(path=None):
    path = Path(path) if path else home() / "config.json"
    if not path.exists():
        c = initial_config()
        write_atomic(path, c)
        return c
    obj = json.loads(path.read_text(encoding="utf-8"))
    validate(obj)
    return obj


def inside(parent, child):
    """True when child equals or is contained in parent. Resolve for existing links."""
    a, b = Path(parent).resolve(), Path(child).resolve()
    return a == b or a in b.parents


def canonical(path):
    return os.path.normcase(str(Path(path).expanduser().resolve()))


def validate(c):
    from .rules import validate_rules
    if not isinstance(c, dict) or c.get("schema_version") != 1: raise ValueError("ERR_CONFIG_INVALID: schema_version")
    a = c.get("api", {})
    if a.get("host", "127.0.0.1") != "127.0.0.1": raise ValueError("API must bind only to 127.0.0.1")
    if not (1024 <= int(a.get("port", 8766)) <= 65535): raise ValueError("Invalid API port")
    if not 1 <= int(c.get("scan_interval_seconds", 5)) <= 3600: raise ValueError("Invalid scan interval")
    if not 5 <= int(c.get("reconcile_interval_seconds", 900)) <= 86400: raise ValueError("Invalid rescan interval")
    roots = c.get("roots", [])
    if not isinstance(roots, list) or len(roots) > 128: raise ValueError("Too many roots")
    ids, paths = set(), set()
    for r in roots:
        if not isinstance(r, dict): raise ValueError("Invalid root")
        if r.get("id") in ids or not r.get("id") or not isinstance(r.get("name"), str): raise ValueError("Duplicate/invalid root id")
        ids.add(r["id"])
        if r.get("mode") not in ("TRACK_ONLY", "ORGANIZE"): raise ValueError("Invalid root mode")
        p = Path(r["path"]).expanduser().resolve()
        if not p.is_absolute() or not p.is_dir(): raise ValueError(f"Root directory unavailable: {p}")
        if canonical(p) in paths: raise ValueError("Duplicate root path")
        paths.add(canonical(p))
        if r.get("mode") == "ORGANIZE":
            if os.name == "nt" and str(p).startswith("\\\\"): raise ValueError("Organize UNC not supported")
            out = Path(r.get("output_path") or p / "_LEIA_Organizado").expanduser().resolve()
            if not inside(p, out): raise ValueError("Output must be within its root")
            if out == p and not (r.get("organize_in_place") is True and r.get("recursive") is False):
                raise ValueError("Output may equal root only with organize_in_place=true and recursive=false")
            if inside(home(), p) or inside(p, home()): raise ValueError("Watcher application data may not be organized")
            if r.get("allow_cross_volume"): raise ValueError("Cross-volume moves not supported")
            if r.get("conflict_policy", "RENAME") not in ("RENAME", "SKIP", "OVERWRITE"): raise ValueError("Invalid collision policy")
            if r.get("conflict_policy") == "OVERWRITE" and not r.get("allow_overwrite", False): raise ValueError("Overwrite requires allow_overwrite=true")
        validate_rules(r.get("ruleset", {}))
    for i, a in enumerate(roots):
        for b in roots[i+1:]:
            if a.get("enabled", True) and b.get("enabled", True) and (a["mode"] == "ORGANIZE" or b["mode"] == "ORGANIZE"):
                if inside(a["path"], b["path"]) or inside(b["path"], a["path"]):
                    raise ValueError("Active overlapping roots prohibited")
    return c


def new_root(name, path, mode="TRACK_ONLY"):
    p = Path(path).expanduser().resolve()
    return {"id": "root-"+uuid.uuid4().hex[:12], "name": name, "path": str(p), "mode": mode,
        "output_path": str(p / "_LEIA_Organizado") if mode == "ORGANIZE" else None,
        "enabled": True, "recursive": True, "conflict_policy": "RENAME", "allow_overwrite": False,
        "exclusions": ["**/.git/**", "**/node_modules/**", "**/__pycache__/**"],
        "ruleset": {"id": "rules-"+uuid.uuid4().hex[:8], "version": 1, "path_steps": ["type", "date"] if mode == "ORGANIZE" else [],
        "creation_fallback": "MTIME", "fallback_folder": "Outros", "rules": [
            {"id": "images", "kind": "type", "target": "Imagens", "extensions": [".png", ".jpeg", ".jpg", ".webp", ".gif"]},
            {"id": "docs", "kind": "type", "target": "Documentos", "extensions": [".pdf", ".docx", ".txt", ".xlsx", ".pptx"]},
            {"id": "archives", "kind": "type", "target": "Compactados", "extensions": [".zip", ".7z", ".rar", ".tar.gz"]}], "size_bands": []}}
