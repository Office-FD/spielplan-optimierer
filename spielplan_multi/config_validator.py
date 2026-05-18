"""Constraint-Vorab-Prüfung vor dem Solver-Start.

Prüft die Liga-Konfiguration auf häufige Probleme und gibt verständliche
Fehlermeldungen und Hinweise zurück – ohne Streamlit-Abhängigkeit.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional
import numpy as np

if TYPE_CHECKING:
    from .league_types import LeagueConfig


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
    """
    issues: List[dict] = []

    def err(lid, msg):  issues.append({'level': 'error',   'lid': lid, 'msg': msg})
    def warn(lid, msg): issues.append({'level': 'warning', 'lid': lid, 'msg': msg})

    for lid in league_order:
        ld   = leagues.get(lid, {})
        name = ld.get('name', lid)
        teams = [t for t, _ in ld.get('teams', [])]
        n     = len(teams)
        n_md  = calc_n_matchdays(ld)
        days  = set(range(1, n_md + 1))
        dst   = dst_per_liga.get(lid, [])
        blk   = blocked.get(lid, {})
        pins  = pinned.get(lid, [])

        # Zu wenige Teams
        if n < 2:
            err(lid, f'**{name}**: Mindestens 2 Teams erforderlich (aktuell: {n}).')
            continue

        # Spieltage = 0
        if n_md == 0:
            err(lid, f'**{name}**: Spieltag-Berechnung ergibt 0 – Format oder Team-Anzahl prüfen.')
            continue

        # Distanzmatrix fehlt oder ist leer
        mat = dist_matrices.get(lid)
        _mat_bad = (mat is None or (isinstance(mat, np.ndarray)
                    and (float(mat.sum()) == 0.0 or bool(np.isnan(mat).any()))))
        if _mat_bad:
            warn(lid, f'**{name}**: Distanzmatrix ist leer – Reiseminimierung nicht möglich. '
                       'Entfernungen im Schritt "Distanzen" eingeben.')

        # DST-Tage außerhalb gültiger Spieltage
        for d1, d2 in dst:
            if d1 not in days or d2 not in days:
                err(lid, f'**{name}**: DST-Block ST{d1}+ST{d2} liegt außerhalb des gültigen '
                          f'Bereichs (1–{n_md}). DST-Blöcke im Kalender-Schritt korrigieren.')

        # Sperrtage: Team mit allen oder mehr als der Hälfte der Tage gesperrt
        for team, bdays in blk.items():
            blocked_set = set(bdays)
            overlap = blocked_set & days
            if days and days.issubset(blocked_set):
                err(lid, f'**{name}** – Team «{team}»: Alle {n_md} Spieltage als '
                          'Heimspiel-Sperrtage eingetragen. Das Team kann keine Heimspiele austragen.')
            elif days and len(overlap) > len(days) * 0.5:
                warn(lid, f'**{name}** – Team «{team}»: Mehr als die Hälfte der '
                           f'Spieltage ({len(overlap)} von {n_md}) ist gesperrt. '
                           'Der Solver könnte keine gültige Lösung finden.')

        # Pflichtspiele außerhalb gültiger Spieltage
        for pm in pins:
            pd = pm.get('day')
            if pd is not None:
                try:
                    if int(pd) not in days:
                        err(lid, f'**{name}**: Pflichtspiel '
                                  f'{pm.get("teamA", "?")} – {pm.get("teamB", "?")} '
                                  f'auf ST{pd}, der nicht existiert (gültig: 1–{n_md}).')
                except (TypeError, ValueError):
                    err(lid, f'**{name}**: Pflichtspiel '
                              f'{pm.get("teamA", "?")} – {pm.get("teamB", "?")}: '
                              f'Spieltag «{pd}» ist kein gültiger Wert.')

        # Pflichtspiele: widersprüchliches Heimrecht für dieselbe Paarung + Tag
        pin_key: dict = {}
        for pm in pins:
            if not pm.get('home'):
                continue
            key = (frozenset([pm.get('teamA'), pm.get('teamB')]), int(pm.get('day', 0)))
            if key in pin_key and pin_key[key] != pm.get('home'):
                err(lid, f'**{name}**: Pflichtspiel '
                          f'{pm.get("teamA", "?")} – {pm.get("teamB", "?")} '
                          f'auf ST{pm.get("day")} hat widersprüchliches Heimrecht '
                          f'(einmal «{pin_key[key]}», '
                          f'einmal «{pm.get("home")}»).')
            pin_key[key] = pm.get('home')

        # Viele Pflichtspiele
        n_rounds, gpd = get_n_rounds_gpd(ld)
        total_games = n * (n - 1) // 2 * n_rounds

        # Ungerade Team-Anzahl → automatisch ein Spielfrei-Tag pro Runde (kein Fehler, nur Hinweis)
        n_active = ld.get('n_active_per_day', 0)
        if gpd == 1 and n_active == 0 and n % 2 == 1:
            warn(lid, f'**{name}**: {n} Teams (ungerade Anzahl) – an jedem Spieltag hat '
                       f'ein Team spielfrei. Der Spielplan hat {n} statt {n - 1} Spieltage '
                       f'pro Runde.')

        if total_games > 0 and len(pins) > total_games * 0.4:
            warn(lid, f'**{name}**: {len(pins)} von {total_games} Spielen sind Pflichtspiele '
                       '(> 40 %). Der Solver hat wenig Spielraum – Optimierungsqualität '
                       'kann eingeschränkt sein.')

        # Kalender: zu wenige Einträge für diese Liga (set vermeidet Doppelzählung)
        cal_days: set = set()
        for kw_data in kw_compat.values():
            for l, sts in kw_data.items():
                if l == lid:
                    cal_days.update(sts)
        cal_entries = len(cal_days)
        if kw_compat and cal_entries < n_md:
            warn(lid, f'**{name}**: Kalender enthält nur {cal_entries} von {n_md} Spieltagen. '
                       'Fehlende Spieltage erhalten kein Datum im Export.')

        # Pflichtheim: Konflikte prüfen
        if forced_home:
            frc = forced_home.get(lid, {})
            for team, fdays in frc.items():
                blk_set = set(blk.get(team, []))
                frc_set = set(fdays)
                # Konflikt: selber Tag ist Sperrtag UND Pflichttag
                conflict = blk_set & frc_set
                if conflict:
                    err(lid, f'**{name}** – Team «{team}»: '
                             f'Spieltag(e) {sorted(conflict)} sind gleichzeitig Sperrtag '
                             f'und Pflichtheim – das ist ein Widerspruch.')
                # Konflikt: Pflichttag liegt außerhalb gültiger Spieltage
                invalid = frc_set - days
                if invalid:
                    err(lid, f'**{name}** – Team «{team}»: '
                             f'Pflichtheim-Spieltag(e) {sorted(invalid)} existieren nicht '
                             f'(gültig: 1–{n_md}).')
                # Konflikt: DST-Block – ein Tag Pflichttag, anderer Tag Sperrtag
                for d1, d2 in dst:
                    if (d1 in frc_set and d2 in blk_set) or (d2 in frc_set and d1 in blk_set):
                        err(lid, f'**{name}** – Team «{team}»: '
                                 f'DST-Block ST{d1}/ST{d2} – ein Tag ist Pflichtheim, '
                                 f'der andere ist Sperrtag. DST erzwingt gleiche Heimrechte '
                                 f'an beiden Tagen → unlösbar.')
                # Konflikt: Pflichtspiel erzwingt Auswärtsspiel an Pflichtheim-Tag
                for pm in pins:
                    if not pm.get('home') or not pm.get('day'):
                        continue
                    try:
                        pd_int = int(pm['day'])
                    except (TypeError, ValueError):
                        continue
                    if pd_int not in frc_set:
                        continue
                    if pm['home'] != team and team in (pm.get('teamA'), pm.get('teamB')):
                        err(lid, f'**{name}** – Team «{team}»: '
                                  f'Spieltag ST{pd_int} ist Pflichtheim, aber Pflichtspiel '
                                  f'{pm.get("teamA","?")} – {pm.get("teamB","?")} '
                                  f'erzwingt Auswärtsspiel → unlösbar.')

        # DST-Routing + Sperrtage: Infeasibility-Risiko prüfen
        if routing:
            apply_r, pct = routing.get(lid, (False, 0))
            if apply_r and pct > 0 and dst and mat is not None and isinstance(mat, np.ndarray) and mat.shape[0] == n:
                f_num = 100 + pct
                f_den = 100
                for d1, d2 in dst:
                    for ti, ti_name in enumerate(teams):
                        blk_set = set(blk.get(ti_name, []))
                        if d1 not in blk_set and d2 not in blk_set:
                            continue
                        # DST-Constraint zwingt ti auf beiden Tagen zu Auswärts.
                        # Fehler nur wenn ALLE möglichen d1-Gegner keine erreichbaren
                        # d2-Gegner haben (partielle Fälle kann der Solver umgehen).
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
                            err(lid,
                                f'**{name}**: DST-Routing-Konflikt (ST{d1}/ST{d2}) – '
                                f'Team «{ti_name}» ist auf ST{d1} oder ST{d2} gesperrt '
                                f'(DST-Constraint erzwingt Auswärts auf beiden Tagen). '
                                f'Für keinen möglichen Gegner ist eine Folgetag-Route '
                                f'innerhalb der Toleranz ({pct} %) erreichbar. '
                                f'→ Routing auf mind. 100 % erhöhen oder deaktivieren.')

    # Co-Home: Liga ohne Kalender
    if clubs and kw_compat:
        for club, members in clubs.items():
            for cl in members.keys():
                has_cal = any(cl in kw_data for kw_data in kw_compat.values())
                if not has_cal:
                    name_c = leagues.get(cl, {}).get('name', cl)
                    warn(None, f'**Co-Home «{club}»**: Liga «{name_c}» hat '
                                'keinen Kalender – Heimspiel-Koordination ist nicht möglich.')

    return issues


def validate_cfgs(cfgs: Dict[str, 'LeagueConfig']) -> List[dict]:
    """Validiert fertig gebaute LeagueConfig-Objekte (für CLI-Nutzung via wizard.py).

    Gibt dieselbe Listenstruktur zurück wie `validate()`:
    [{'level': 'error'|'warning', 'lid': str|None, 'msg': str}, ...]
    """
    issues: List[dict] = []

    def err(lid, msg):  issues.append({'level': 'error',   'lid': lid, 'msg': msg})
    def warn(lid, msg): issues.append({'level': 'warning', 'lid': lid, 'msg': msg})

    for lid, cfg in cfgs.items():
        name  = cfg.name
        n     = cfg.n_teams
        n_md  = cfg.n_matchdays
        days  = set(cfg.days)

        if n < 2:
            err(lid, f'{name}: Mindestens 2 Teams erforderlich (aktuell: {n}).')
            continue

        if n_md == 0:
            err(lid, f'{name}: Spieltag-Berechnung ergibt 0 – Format oder Team-Anzahl prüfen.')
            continue

        if cfg.dist is None or float(cfg.dist.sum()) == 0.0 or bool(np.isnan(cfg.dist).any()):
            warn(lid, f'{name}: Distanzmatrix ist leer – Reiseminimierung nicht möglich.')

        for d1, d2 in cfg.dst_blocks:
            if d1 not in days or d2 not in days:
                err(lid, f'{name}: DST-Block ST{d1}+ST{d2} liegt außerhalb des gültigen '
                          f'Bereichs (1–{n_md}).')

        for team, bdays in cfg.blocked.items():
            blocked_set = set(bdays)
            overlap = blocked_set & days
            if days and days.issubset(blocked_set):
                err(lid, f'{name} – Team «{team}»: Alle {n_md} Spieltage gesperrt.')
            elif days and len(overlap) > len(days) * 0.5:
                warn(lid, f'{name} – Team «{team}»: Mehr als die Hälfte der Spieltage '
                           f'({len(overlap)} von {n_md}) ist gesperrt.')

        for pm in cfg.pinned:
            pd = pm.get('day')
            if pd is not None:
                try:
                    if int(pd) not in days:
                        err(lid, f'{name}: Pflichtspiel {pm.get("teamA","?")} – {pm.get("teamB","?")} '
                                  f'auf ST{pd}, der nicht existiert (gültig: 1–{n_md}).')
                except (TypeError, ValueError):
                    err(lid, f'{name}: Pflichtspiel {pm.get("teamA","?")} – {pm.get("teamB","?")}: '
                              f'Spieltag «{pd}» ist kein gültiger Wert.')

        pin_key: dict = {}
        for pm in cfg.pinned:
            if not pm.get('home'):
                continue
            key = (frozenset([pm.get('teamA'), pm.get('teamB')]), int(pm.get('day', 0)))
            if key in pin_key and pin_key[key] != pm.get('home'):
                err(lid, f'{name}: Pflichtspiel {pm.get("teamA","?")} – {pm.get("teamB","?")} '
                          f'auf ST{pm.get("day")} hat widersprüchliches Heimrecht.')
            pin_key[key] = pm.get('home')

        # Pflichtheim-Validierung
        for team, fdays in cfg.forced_home.items():
            frc_set = set(fdays)
            blk_set = set(cfg.blocked.get(team, []))
            conflict = blk_set & frc_set
            if conflict:
                err(lid, f'{name} – Team «{team}»: '
                         f'Spieltag(e) {sorted(conflict)} sind gleichzeitig Sperrtag '
                         f'und Pflichtheim – das ist ein Widerspruch.')
            invalid = frc_set - days
            if invalid:
                err(lid, f'{name} – Team «{team}»: '
                         f'Pflichtheim-Spieltag(e) {sorted(invalid)} existieren nicht '
                         f'(gültig: 1–{n_md}).')
            for d1, d2 in cfg.dst_blocks:
                if (d1 in frc_set and d2 in blk_set) or (d2 in frc_set and d1 in blk_set):
                    err(lid, f'{name} – Team «{team}»: '
                             f'DST-Block ST{d1}/ST{d2} – ein Tag ist Pflichtheim, '
                             f'der andere ist Sperrtag → unlösbar.')
            for pm in cfg.pinned:
                if not pm.get('home') or not pm.get('day'):
                    continue
                try:
                    pd_int = int(pm['day'])
                except (TypeError, ValueError):
                    continue
                if pd_int not in frc_set:
                    continue
                if pm['home'] != team and team in (pm.get('teamA'), pm.get('teamB')):
                    err(lid, f'{name} – Team «{team}»: '
                              f'Spieltag ST{pd_int} ist Pflichtheim, aber Pflichtspiel '
                              f'{pm.get("teamA","?")} – {pm.get("teamB","?")} '
                              f'erzwingt Auswärtsspiel → unlösbar.')

        total_games = n * (n - 1) // 2 * cfg.n_rounds

        # Ungerade Team-Anzahl → automatisch ein Spielfrei-Tag pro Runde
        if cfg.games_per_team_per_day == 1 and cfg.n_active_per_day == 0 and n % 2 == 1:
            warn(lid, f'{name}: {n} Teams (ungerade Anzahl) – je Spieltag hat ein Team spielfrei. '
                       f'Spielplan hat {n} statt {n - 1} Spieltage pro Runde.')

        if total_games > 0 and len(cfg.pinned) > total_games * 0.4:
            warn(lid, f'{name}: {len(cfg.pinned)} von {total_games} Spielen sind Pflichtspiele '
                       '(> 40 %). Optimierungsqualität kann eingeschränkt sein.')

    return issues
