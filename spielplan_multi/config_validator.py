"""Constraint-Vorab-Prüfung vor dem Solver-Start.

Prüft die Liga-Konfiguration auf häufige Probleme und gibt verständliche
Fehlermeldungen und Hinweise zurück – ohne Streamlit-Abhängigkeit.

B-L4 (Code-Review Runde 6 Sprint R1): Validator-Konsolidierung
- Die Liga-spezifischen Checks sind in `_validate_league_common()` extrahiert.
- `validate()` (UI/Wizard-Daten als Dicts) und `validate_cfgs()` (LeagueConfig-
  Objekte) sind dünne Adapter, die das Kontext-Objekt zusammenbauen und
  zusätzliche UI-only-Checks (Kalender, DST-Routing, Co-Home) ergänzen.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple
import numpy as np

if TYPE_CHECKING:
    from .league_types import LeagueConfig


# ── Gemeinsamer Validierungs-Kontext ─────────────────────────────────────────

@dataclass
class _LeagueValCtx:
    """Aggregierter Validierungs-Input fuer eine Liga.

    `name_md` formatiert den Liga-Namen fuer die Fehlermeldung (UI: '**{name}**',
    CLI: '{name}') — beide Aufrufer setzen das.
    """
    lid:          str
    name_md:      str               # gerenderte Namens-Anrede (mit oder ohne **bold**)
    teams:        List[str]
    n_md:         int
    n_rounds:     int
    gpd:          int                # games_per_team_per_day
    n_active:     int                # 0 = alle Teams
    dst_blocks:   List[Tuple[int, int]]
    blocked:      Dict[str, List[int]]
    forced_home:  Dict[str, List[int]]
    pinned:       List[dict]
    dist:         Optional[np.ndarray]


def _has_nan(arr) -> bool:
    """np.isnan auf int-Arrays wirft TypeError in numpy 1.24+; float-Arrays OK."""
    try:
        return bool(np.isnan(arr).any())
    except TypeError:
        return False


# ── Liga-Validierung (gemeinsamer Kern) ──────────────────────────────────────

def _validate_league_common(
    ctx:   _LeagueValCtx,
    _err:  Callable[[Optional[str], str], None],
    _warn: Callable[[Optional[str], str], None],
) -> bool:
    """Fuehrt alle Liga-spezifischen Standard-Checks durch.

    Gibt True zurueck, wenn die Validierung normal durchlaufen ist,
    False wenn ein harter Skip-Fehler (n<2 oder n_md=0) auftrat.
    """
    lid = ctx.lid
    name = ctx.name_md
    teams = ctx.teams
    n = len(teams)
    n_md = ctx.n_md
    days = set(range(1, n_md + 1))

    # Zu wenige Teams / Spieltage = 0
    if n < 2:
        _err(lid, f'{name}: Mindestens 2 Teams erforderlich (aktuell: {n}).')
        return False
    if n_md == 0:
        _err(lid, f'{name}: Spieltag-Berechnung ergibt 0 – Format oder Team-Anzahl prüfen.')
        return False

    # Distanzmatrix
    mat = ctx.dist
    _mat_bad = (mat is None or (isinstance(mat, np.ndarray)
                and (float(mat.sum()) == 0.0 or _has_nan(mat))))
    if _mat_bad:
        _warn(lid, f'{name}: Distanzmatrix ist leer – Reiseminimierung nicht möglich.')

    # DST-Tage außerhalb gültiger Spieltage
    for d1, d2 in ctx.dst_blocks:
        if d1 not in days or d2 not in days:
            _err(lid, f'{name}: DST-Block ST{d1}+ST{d2} liegt außerhalb des gültigen '
                       f'Bereichs (1–{n_md}).')

    # R8-C-M1.1: DST-Block mit d1 == d2 ist kein DST, sondern Einzeltag
    for d1, d2 in ctx.dst_blocks:
        if d1 == d2:
            _warn(lid, f'{name}: DST-Block ST{d1}+ST{d2} hat identische Tage – '
                        f'das ist kein Doppelspieltag und wird vom Solver als sinnloser '
                        f'Eintrag behandelt.')

    # R8-C-M1.2: Zwei DST-Blöcke mit überlappendem Tag → de-facto 3-Tage-Block
    _dst_day_owner: dict = {}
    for d1, d2 in ctx.dst_blocks:
        for d in (d1, d2):
            if d in _dst_day_owner and _dst_day_owner[d] != (d1, d2):
                _warn(lid, f'{name}: Spieltag ST{d} ist in mehreren DST-Blöcken enthalten '
                            f'({_dst_day_owner[d]} und ({d1}, {d2})). Solver erzwingt dann '
                            f'gleiche Heimrechte über alle beteiligten Tage – das ist '
                            f'wahrscheinlich nicht gewollt.')
            else:
                _dst_day_owner[d] = (d1, d2)

    # Sperrtage
    _teams_set = set(teams)
    for team, bdays in ctx.blocked.items():
        if team not in _teams_set:
            _warn(lid, f'{name}: Sperrtag-Team «{team}» nicht in der Teamliste – wird ignoriert.')
            continue
        blocked_set = set(bdays)
        invalid = blocked_set - days
        if invalid:
            _warn(lid, f'{name} – Team «{team}»: Sperrtag(e) {sorted(invalid)} '
                       f'liegen außerhalb des gültigen Bereichs (1–{n_md}) und werden ignoriert.')
        overlap = blocked_set & days
        if days and days.issubset(blocked_set):
            _err(lid, f'{name} – Team «{team}»: Alle {n_md} Spieltage als '
                       'Heimspiel-Sperrtage eingetragen. Das Team kann keine Heimspiele austragen.')
        elif days and len(overlap) > len(days) * 0.5:
            _warn(lid, f'{name} – Team «{team}»: Mehr als die Hälfte der '
                        f'Spieltage ({len(overlap)} von {n_md}) ist gesperrt. '
                        'Der Solver könnte keine gültige Lösung finden.')

    # Pflichtspiele: Teamnamen, Self-Spiele, ungültige Spieltage
    for pm in ctx.pinned:
        ta, tb = pm.get('teamA'), pm.get('teamB')
        if ta and ta not in _teams_set:
            _err(lid, f'{name}: Pflichtspiel-Team «{ta}» nicht in der Teamliste.')
        if tb and tb not in _teams_set:
            _err(lid, f'{name}: Pflichtspiel-Team «{tb}» nicht in der Teamliste.')
        if ta and tb and ta == tb:
            _err(lid, f'{name}: Pflichtspiel «{ta}» gegen sich selbst – kein gültiges Spiel.')
        pd = pm.get('day')
        if pd is not None:
            try:
                if int(pd) not in days:
                    _err(lid, f'{name}: Pflichtspiel '
                               f'{pm.get("teamA", "?")} – {pm.get("teamB", "?")} '
                               f'auf ST{pd}, der nicht existiert (gültig: 1–{n_md}).')
            except (TypeError, ValueError):
                _err(lid, f'{name}: Pflichtspiel '
                           f'{pm.get("teamA", "?")} – {pm.get("teamB", "?")}: '
                           f'Spieltag «{pd}» ist kein gültiger Wert.')

    # Pflichtspiele: widersprüchliches Heimrecht für dieselbe Paarung + Tag
    pin_key: dict = {}
    for pm in ctx.pinned:
        if not pm.get('home'):
            continue
        try:
            _pin_day = int(pm.get('day', 0))
        except (TypeError, ValueError):
            continue  # ungueltiger day-Wert wurde bereits oben als Fehler erfasst
        key = (frozenset([pm.get('teamA'), pm.get('teamB')]), _pin_day)
        if key in pin_key and pin_key[key] != pm.get('home'):
            _err(lid, f'{name}: Pflichtspiel '
                       f'{pm.get("teamA", "?")} – {pm.get("teamB", "?")} '
                       f'auf ST{pm.get("day")} hat widersprüchliches Heimrecht '
                       f'(einmal «{pin_key[key]}», einmal «{pm.get("home")}»).')
        pin_key[key] = pm.get('home')

    # Einfachrunde: doppelte Pflichtspiel-Paarung → INFEASIBLE
    n_rounds = ctx.n_rounds
    if n_rounds == 1:
        _seen_pairs: set = set()
        for pm in ctx.pinned:
            ta, tb = pm.get('teamA'), pm.get('teamB')
            if not ta or not tb:
                continue
            pair = frozenset([ta, tb])
            if pair in _seen_pairs:
                _err(lid, f'{name}: Einfachrunde – Paarung {ta} – {tb} als Pflichtspiel '
                           'mehrfach eingetragen. Jede Paarung darf nur einmal vorkommen → unlösbar.')
            _seen_pairs.add(pair)

    # n_rounds >= 2: mehrere Pins für dieselbe Paarung im SELBEN Round → INFEASIBLE (B-M2)
    if n_rounds >= 2 and n_md > 0:
        _round_len = max(1, n_md // n_rounds)
        _pair_rounds: dict = {}
        for pm in ctx.pinned:
            ta, tb = pm.get('teamA'), pm.get('teamB')
            if not ta or not tb or pm.get('day') is None:
                continue
            try:
                _d = int(pm['day'])
            except (TypeError, ValueError):
                continue
            pair = frozenset([ta, tb])
            _rnd = min(n_rounds, (_d - 1) // _round_len + 1)
            _pair_rounds.setdefault(pair, []).append(_rnd)
        for pair, rnds in _pair_rounds.items():
            if len(rnds) != len(set(rnds)):
                _err(lid, f'{name}: Paarung {sorted(pair)} ist mehrfach in derselben '
                           f'Runde als Pflichtspiel eingetragen → unlösbar.')

    # Pflichtspiel-Heimrecht widerspricht Sperrtag des Heimteams → INFEASIBLE (B-M1)
    blk = ctx.blocked
    for pm in ctx.pinned:
        _ht_pin = pm.get('home')
        _d_pin = pm.get('day')
        if not _ht_pin or _d_pin is None:
            continue
        try:
            _d_int = int(_d_pin)
        except (TypeError, ValueError):
            continue
        if _ht_pin in blk and _d_int in set(blk.get(_ht_pin, [])):
            _err(lid, f'{name}: Pflichtspiel ST{_d_int} – Team «{_ht_pin}» soll '
                       f'Heimrecht haben, ST{_d_int} ist aber gleichzeitig Sperrtag → unlösbar.')

    # Ungerade Team-Anzahl Hinweis (Spielfrei-Modus)
    if ctx.gpd == 1 and ctx.n_active == 0 and n % 2 == 1:
        _warn(lid, f'{name}: {n} Teams (ungerade Anzahl) – an jedem Spieltag hat '
                    f'ein Team spielfrei. Der Spielplan hat {n} statt {n - 1} Spieltage '
                    f'pro Runde.')

    # Pflichtspiel-Anzahl
    total_games = n * (n - 1) // 2 * n_rounds
    if total_games > 0 and len(ctx.pinned) > total_games:
        _err(lid, f'{name}: {len(ctx.pinned)} Pflichtspiele, aber nur {total_games} Spiele '
                   f'in der Saison – nicht alle Pins koennen stattfinden.')
    elif total_games > 0 and len(ctx.pinned) > total_games * 0.4:
        _warn(lid, f'{name}: {len(ctx.pinned)} von {total_games} Spielen sind Pflichtspiele '
                    '(> 40 %). Der Solver hat wenig Spielraum – Optimierungsqualität '
                    'kann eingeschränkt sein.')

    # Pflichtheim
    # R8-C-M1.3: max-Heimspiele pro Team berechnen (für Anzahl-Check).
    # Bei n_rounds=2 muss jede Paarung 1x Heim + 1x Auswärts pro Team → genau n-1
    # Heimspiele pro Team. Bei n_rounds=1 max. n-1 (alle Heim), aber Solver-Constraints
    # (max 2 konsekutiv) machen das praktisch unmöglich → realistisch ~n/2.
    if n_rounds == 2:
        _max_home_per_team = n - 1
    elif n_rounds == 3:
        _max_home_per_team = 2 * (n - 1)  # jede Paarung 2x Heim + 1x Auswärts (oder umgekehrt)
    else:
        _max_home_per_team = n - 1  # Einfachrunde: max alle Spiele Heim
    for team, fdays in ctx.forced_home.items():
        # B-M3: Pflichtheim-Team gegen Teamliste validieren
        if team not in _teams_set:
            _warn(lid, f'{name}: Pflichtheim-Team «{team}» nicht in der Teamliste – wird ignoriert.')
            continue
        frc_set = set(fdays)
        # R8-C-M1.3: Pflichtheim-Anzahl gegen max-Heimspiele
        if len(frc_set) > _max_home_per_team:
            _err(lid, f'{name} – Team «{team}»: {len(frc_set)} Pflichtheim-Tage eingetragen, '
                       f'aber bei {n_rounds}-Runden-Format kann das Team maximal '
                       f'{_max_home_per_team} Heimspiele haben → unlösbar.')
        blk_set = set(blk.get(team, []))
        conflict = blk_set & frc_set
        if conflict:
            _err(lid, f'{name} – Team «{team}»: '
                       f'Spieltag(e) {sorted(conflict)} sind gleichzeitig Sperrtag '
                       f'und Pflichtheim – das ist ein Widerspruch.')
        invalid = frc_set - days
        if invalid:
            _err(lid, f'{name} – Team «{team}»: '
                       f'Pflichtheim-Spieltag(e) {sorted(invalid)} existieren nicht '
                       f'(gültig: 1–{n_md}).')
        for d1, d2 in ctx.dst_blocks:
            if (d1 in frc_set and d2 in blk_set) or (d2 in frc_set and d1 in blk_set):
                _err(lid, f'{name} – Team «{team}»: '
                           f'DST-Block ST{d1}/ST{d2} – ein Tag ist Pflichtheim, '
                           f'der andere ist Sperrtag. DST erzwingt gleiche Heimrechte '
                           f'an beiden Tagen → unlösbar.')
        for pm in ctx.pinned:
            if not pm.get('home') or not pm.get('day'):
                continue
            try:
                pd_int = int(pm['day'])
            except (TypeError, ValueError):
                continue
            if pd_int not in frc_set:
                continue
            if pm['home'] != team and team in (pm.get('teamA'), pm.get('teamB')):
                _err(lid, f'{name} – Team «{team}»: '
                           f'Spieltag ST{pd_int} ist Pflichtheim, aber Pflichtspiel '
                           f'{pm.get("teamA","?")} – {pm.get("teamB","?")} '
                           f'erzwingt Auswärtsspiel → unlösbar.')

    return True


# ── Public API: UI/Wizard-Variante ───────────────────────────────────────────

def validate(
    league_order:  List[str],
    leagues:       Dict[str, dict],
    dst_per_liga:  Dict[str, list],
    blocked:       Dict[str, dict],
    pinned:        Dict[str, list],
    dist_matrices: Dict[str, Optional[np.ndarray]],
    kw_compat:     Dict[int, dict],
    clubs:         Dict[str, dict],
    calc_n_matchdays,        # callable: (ld: dict) -> int
    get_n_rounds_gpd,        # callable: (ld: dict) -> (int, int)
    routing:       Optional[Dict[str, tuple]] = None,  # {lid: (apply:bool, pct:int)}
    forced_home:   Optional[Dict[str, dict]] = None,   # {lid: {team:[days]}}
) -> List[dict]:
    """Prüft die Konfiguration und gibt eine Liste von Problemen zurück.

    Jeder Eintrag: {'level': 'error'|'warning', 'lid': str|None, 'msg': str}
    Fehler (error) = unlösbare Konfiguration.
    Warnung (warning) = mögliche Einschränkung der Optimierungsqualität.

    UI-spezifische Checks ergänzen den Common-Validator:
      - Kalender-Einträge je Liga
      - DST-Routing-Toleranz (verhindert Routing-Konflikte)
      - Co-Home: Liga ohne Kalender
    """
    issues: List[dict] = []
    _err = lambda lid, msg: issues.append({'level': 'error',   'lid': lid, 'msg': msg})
    _warn = lambda lid, msg: issues.append({'level': 'warning', 'lid': lid, 'msg': msg})

    for lid in league_order:
        ld = leagues.get(lid, {})
        name = ld.get('name', lid)
        teams = [t for t, _ in ld.get('teams', [])]
        n_rounds, gpd = get_n_rounds_gpd(ld)
        ctx = _LeagueValCtx(
            lid=lid,
            name_md=f'**{name}**',
            teams=teams,
            n_md=calc_n_matchdays(ld),
            n_rounds=n_rounds,
            gpd=gpd,
            n_active=int(ld.get('n_active_per_day', 0) or 0),
            dst_blocks=dst_per_liga.get(lid, []),
            blocked=blocked.get(lid, {}),
            forced_home=(forced_home or {}).get(lid, {}),
            pinned=pinned.get(lid, []),
            dist=dist_matrices.get(lid),
        )
        if not _validate_league_common(ctx, _err, _warn):
            continue

        # UI-only: Kalender zu wenige Einträge
        n_md = ctx.n_md
        cal_days: set = set()
        for kw_data in kw_compat.values():
            for l, sts in kw_data.items():
                if l == lid:
                    cal_days.update(sts)
        cal_entries = len(cal_days)
        if kw_compat and cal_entries < n_md:
            _warn(lid, f'**{name}**: Kalender enthält nur {cal_entries} von {n_md} Spieltagen. '
                        'Fehlende Spieltage erhalten kein Datum im Export.')

        # UI-only: DST-Routing + Sperrtage Infeasibility-Check
        if routing:
            apply_r, pct = routing.get(lid, (False, 0))
            mat = ctx.dist
            n = len(teams)
            if (apply_r and pct > 0 and ctx.dst_blocks
                    and mat is not None and isinstance(mat, np.ndarray) and mat.shape[0] == n):
                f_num = 100 + pct
                f_den = 100
                blk = ctx.blocked
                for d1, d2 in ctx.dst_blocks:
                    for ti, ti_name in enumerate(teams):
                        blk_set = set(blk.get(ti_name, []))
                        if d1 not in blk_set and d2 not in blk_set:
                            continue
                        no_escape = []
                        n_candidates = 0
                        for i in range(n):
                            if i == ti or mat[ti, i] <= 0:
                                continue
                            n_candidates += 1
                            rhs = (f_num / f_den) * float(mat[ti, i])
                            can_reach = any(
                                j != ti and j != i
                                and float(mat[i, j]) + float(mat[j, ti]) <= rhs
                                for j in range(n)
                            )
                            if not can_reach:
                                no_escape.append(teams[i])
                        if no_escape and len(no_escape) >= n_candidates:
                            _err(lid,
                                f'**{name}**: DST-Routing-Konflikt (ST{d1}/ST{d2}) – '
                                f'Team «{ti_name}» ist auf ST{d1} oder ST{d2} gesperrt '
                                f'(DST-Constraint erzwingt Auswärts auf beiden Tagen). '
                                f'Für keinen möglichen Gegner ist eine Folgetag-Route '
                                f'innerhalb der Toleranz ({pct} %) erreichbar. '
                                f'→ Routing auf mind. 100 % erhöhen oder deaktivieren.')

    # UI-only: Co-Home-Verein ohne Kalender
    if clubs and kw_compat:
        for club, members in clubs.items():
            for cl in members.keys():
                has_cal = any(cl in kw_data for kw_data in kw_compat.values())
                if not has_cal:
                    name_c = leagues.get(cl, {}).get('name', cl)
                    _warn(None, f'**Co-Home «{club}»**: Liga «{name_c}» hat '
                                 'keinen Kalender – Heimspiel-Koordination ist nicht möglich.')

    return issues


# ── Public API: CLI-Variante (LeagueConfig-Objekte) ──────────────────────────

def validate_cfgs(cfgs: Dict[str, 'LeagueConfig']) -> List[dict]:
    """Validiert fertig gebaute LeagueConfig-Objekte (für CLI-Nutzung via wizard.py).

    Gibt dieselbe Listenstruktur zurück wie `validate()`:
    [{'level': 'error'|'warning', 'lid': str|None, 'msg': str}, ...]
    """
    issues: List[dict] = []
    _err = lambda lid, msg: issues.append({'level': 'error',   'lid': lid, 'msg': msg})
    _warn = lambda lid, msg: issues.append({'level': 'warning', 'lid': lid, 'msg': msg})

    for lid, cfg in cfgs.items():
        ctx = _LeagueValCtx(
            lid=lid,
            name_md=cfg.name,                       # CLI: kein **bold**
            teams=list(cfg.teams),
            n_md=cfg.n_matchdays,
            n_rounds=cfg.n_rounds,
            gpd=cfg.games_per_team_per_day,
            n_active=cfg.n_active_per_day,
            dst_blocks=list(cfg.dst_blocks),
            blocked=dict(cfg.blocked),
            forced_home=dict(cfg.forced_home),
            pinned=list(cfg.pinned),
            dist=cfg.dist,
        )
        _validate_league_common(ctx, _err, _warn)

    return issues
