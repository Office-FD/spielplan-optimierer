"""Solver-Konstanten. Ligaspezifische Daten werden per Wizard eingegeben."""

from typing import Dict

# ── Solver-Gewichte ───────────────────────────────────────────────────────────
# round_balance: Skala 2.0 (analog sw_fair), bestraft quadrierte Abweichung der
# Heimspiel-Anzahl pro Runde vom Mittelwert. Default in der UI: 0 (aus).
WEIGHT_SCALES = {
    'switch':        80.0,
    'sw_fair':        2.0,
    'trav_fair':      0.02,
    'travel':         0.05,
    'dst_eff':        0.03,
    'round_balance':  2.0,
}
WEIGHT_LABELS = [
    ('switch',        'Heimrecht-Wechsel maximieren'),
    ('sw_fair',       'Fairness bei Heimrecht-Wechseln'),
    ('trav_fair',     'Fairness bei Reisekilometern'),
    ('travel',        'Gesamtkilometer minimieren'),
    ('dst_eff',       'DST-Reiseeffizienz'),
    ('round_balance', 'Heim-Balance pro Runde'),
]

KM_PAUSCHALE   = 0.20
UNREACHABLE_KM = 9999

# ── Team-Farben (zyklisch, beliebig viele Teams) ─────────────────────────────
_TEAM_COLOR_LIST = [
    'FFF4B3', 'FFE566', 'FFD9B3', 'FFB366',
    'FFCCCC', 'FF9999', 'E6D9FF', 'CCAAFF',
    'D9EBFF', '99CCFF', 'D9F0D9', '99DD99',
    'E8F5E9', 'A5D6A7', 'FFF9C4', 'F0F4C3',
    'FCE4EC', 'F48FB1', 'E3F2FD', '90CAF9',
]


def get_team_color(idx: int) -> str:
    """Hex-Farbcode fuer Team-Index idx, zyklisch fuer beliebig viele Teams."""
    return _TEAM_COLOR_LIST[idx % len(_TEAM_COLOR_LIST)]


# Backward-kompatibles Dict (wird in excel_output.py importiert)
class _TeamColorDict(dict):
    def __missing__(self, k):
        return get_team_color(k)

TEAM_COLORS: Dict[int, str] = _TeamColorDict({i: get_team_color(i) for i in range(20)})
