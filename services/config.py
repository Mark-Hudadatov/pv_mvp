from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

def load_yaml(name: str):
    with open(DATA / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# lazy singletons
_defaults = None
_tariffs = None
_scen = None

def defaults():
    global _defaults
    if _defaults is None:
        _defaults = load_yaml("defaults.yaml")
    return _defaults

def tariffs():
    global _tariffs
    if _tariffs is None:
        _tariffs = load_yaml("tariffs.yaml")
    return _tariffs

def scen():
    global _scen
    if _scen is None:
        _scen = load_yaml("scenarios.yaml")
    return _scen

def pick_scenario(key: str, name: str = "base"):
    return scen()[key][name]

def nominal_rate_from_real(r_real: float, cpi: float) -> float:
    """Convert real discount to nominal given CPI."""
    return (1 + r_real) * (1 + cpi) - 1
