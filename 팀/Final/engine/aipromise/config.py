"""config.yaml 읽기. 경로는 engine 폴더 기준으로 풉니다."""
import os
import yaml

ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _abs(path: str) -> str:
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(ENGINE_DIR, path))


def load_config(path: str = None) -> dict:
    path = path or os.path.join(ENGINE_DIR, "config.yaml")
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key, value in list(cfg["paths"].items()):
        if value:
            cfg["paths"][key] = _abs(value)
    cfg.setdefault("keywords", None)
    return cfg


def company_cfg(cfg: dict, key: str) -> dict:
    """companies(핵심 기업)에서 찾고, 없으면 candidates(시연용 기업, --company나 --companies로 이름을 줄 때 씀)에서 찾습니다."""
    pool = {**(cfg.get("candidates") or {}), **cfg["companies"]}
    if key not in pool:
        raise SystemExit(f"config.yaml에 '{key}' 기업이 없습니다. 있는 기업: {list(cfg['companies'])}, "
                         f"후보 기업: {list(cfg.get('candidates') or {})}")
    c = dict(pool[key])
    c["key"] = key
    return c


def work_dir(cfg: dict, company_key: str) -> str:
    d = os.path.join(cfg["paths"]["work_dir"], company_key)
    os.makedirs(d, exist_ok=True)
    return d
