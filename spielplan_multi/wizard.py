"""CLI-Wizard zur Konfiguration beliebig vieler Ligen.

Schritte:
  0  Ligen definieren (Anzahl, ID, Name, Teams, Standorte, Hierarchiegewicht)
  1  Distanzmatrizen (Google Maps / Datei / manuell)
  2  Kalender laden (optional) + DST-Konfiguration
  3  DST-Routing-Optimierung
  4  Optimierungs-Gewichtungen
  5  Pflichtspiele
  6  Heimspiel-Sperrtage
  7  Co-Home-Konfiguration (nur bei mehreren Ligen)
  8  Solver-Konfiguration
  9  Constraint-Validierung
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .ui import (banner, section, ok, info, warn, err, step,
                  ask_yes_no, ask_int, ask_float, ask_path)
from .config import WEIGHT_SCALES, WEIGHT_LABELS
from .calendar_parser import parse_rahmenterminplan, preview_columns, build_weekends
from .league_types import LeagueConfig
from .distances import (get_api_key, calculate_distance_matrix,
                         load_distances_from_file, enter_distances_manually)


# ── Schritt 0: Ligen definieren ───────────────────────────────────────────────

def _valid_lid(lid: str) -> bool:
    return bool(re.fullmatch(r'[A-Za-z0-9_\-]{1,20}', lid))


def _show_team_table(teams: List[str], locations: List[str], title: str) -> None:
    section(title)
    nw = max(len('Teamname'), max((len(t) for t in teams), default=8))
    lw = max(len('Standort'),  max((len(l) for l in locations), default=8))
    print('  Nr.  ' + 'Teamname'.ljust(nw) + '  ' + 'Standort'.ljust(lw))
    print('  ---  ' + '-' * nw + '  ' + '-' * lw)
    for i, (t, loc) in enumerate(zip(teams, locations), 1):
        print('  ' + str(i).rjust(3) + '  ' + t.ljust(nw) + '  ' + loc.ljust(lw))


def _input_teams() -> Tuple[List[str], List[str]]:
    """Fragt Teams und Standorte ab. Leerzeile beendet die Eingabe."""
    info('Teams eingeben (leere Zeile = fertig, mind. 4 Teams):')
    teams, locations = [], []
    while True:
        name = input(f'  Team {len(teams)+1} Name (leer = fertig): ').strip()
        if not name:
            if len(teams) < 4:
                err('Mindestens 4 Teams erforderlich.')
                continue
            break
        loc = input(f'  Team {len(teams)+1} Standort/Adresse: ').strip()
        if not loc:
            loc = name
        teams.append(name)
        locations.append(loc)
    return teams, locations


def step0_leagues() -> Dict[str, Tuple[List[str], List[str], str, float, int, int, int, int, dict]]:
    """Definiert alle Ligen.

    Gibt zurueck: {lid: (teams, locations, name, hier_weight, gpd, n_rounds, k_group, n_active, tt_settings)}
    k_group: 0 = Stufe 1 (alle Teams), >0 = Stufe 2 (Gruppengroesse)
    n_active: 0 = alle Teams, >0 = Spielfrei-Modus (Anzahl aktiver Teams pro Spieltag)
    tt_settings: Turniertag-Spielreihenfolge-Einstellungen (leer fuer andere Formate)
    """
    section('SCHRITT 0: LIGEN KONFIGURIEREN')
    info('Definiere alle Ligen, die in diesem Durchlauf optimiert werden sollen.')

    n_ligen = ask_int('Anzahl Ligen', 1, 8, default=1)
    result = {}

    for i in range(n_ligen):
        print(f'\n  === Liga {i+1}/{n_ligen} ===')

        # Liga-ID
        while True:
            lid = input('  Liga-ID (kurz, keine Leerzeichen, z.B. LIGA_A): ').strip().upper()
            if not lid:
                err('Liga-ID darf nicht leer sein.')
                continue
            if not _valid_lid(lid):
                err('Nur Buchstaben, Ziffern, _ und - erlaubt (max. 20 Zeichen).')
                continue
            if lid in result:
                err(f'Liga-ID "{lid}" bereits vergeben.')
                continue
            break

        # Liga-Name
        name = input(f'  Liga-Name (z.B. Regionalliga Nord): ').strip()
        if not name:
            name = lid

        # Hierarchiegewicht
        if n_ligen > 1:
            hw = ask_float(f'  Hierarchiegewicht (1.0 = Standard, hoeher = wichtiger)',
                           0.1, 5.0, default=1.0)
        else:
            hw = 1.0

        # Teams und Standorte
        while True:
            teams, locations = _input_teams()
            _show_team_table(teams, locations, f'Liga {lid} – Uebersicht')
            dupes = [t for t, c in Counter(teams).items() if c > 1]
            if dupes:
                err(f'Doppelte Teamnamen: {dupes}. Bitte erneut eingeben.')
                continue
            if ask_yes_no('So uebernehmen?'):
                break

        # Spielformat
        print()
        print('  Spielformat:')
        print('    1 = Einfachrunde    (1 Runde,  1 Spiel/Tag)')
        print('    2 = Hin-/Rueckrunde (2 Runden, 1 Spiel/Tag)  [Standard]')
        print('    3 = Dreifachrunde   (3 Runden, 1 Spiel/Tag)')
        print('    4 = Turniertag      (mehrere Spiele pro Tag, alle Teams vor Ort)')
        while True:
            fmt = input('  Format (1/2/3/4) [Standard: 2]: ').strip()
            if fmt in ('', '1', '2', '3', '4'):
                break
            err('Bitte 1, 2, 3 oder 4 eingeben.')
        fmt = fmt if fmt else '2'

        k_group = 0  # Standard: Stufe 1 (kein Gruppenmodell)
        n_events = 0
        tt_settings: dict = {}

        if fmt == '1':
            n_rounds, gpd = 1, 1
            mode_label = 'Einfachrunde'
        elif fmt == '2':
            n_rounds, gpd = 2, 1
            mode_label = 'Hin-/Rueckrunde'
        elif fmt == '3':
            n_rounds, gpd = 3, 1
            mode_label = 'Dreifachrunde'
        else:  # '4' Turniertag
            # Anzahl Runden
            print('  Turniertag – Runden:')
            print('    1 = Einfachrunde')
            print('    2 = Hin-/Rueckrunde [Standard]')
            print('    3 = Dreifachrunde')
            while True:
                rnd = input('  Runden (1/2/3) [2]: ').strip() or '2'
                if rnd in ('1', '2', '3'):
                    n_rounds = int(rnd)
                    break
                err('Bitte 1, 2 oder 3.')
            # Gueltige gpd-Werte berechnen (alle Teams an einem Ort)
            n_t = len(teams)
            valid_gpd = [g for g in range(2, n_t)
                         if (n_t - 1) % g == 0 and (n_t * g) % 2 == 0]
            if not valid_gpd:
                warn(f'Keine gueltigen Turniertag-Werte fuer {n_t} Teams. '
                     f'Falle zurueck auf Standard (1 Spiel/Tag).')
                gpd = 1
            else:
                info(f'  Gueltige Spiele/Team/Spieltag fuer {n_t} Teams: {valid_gpd}')
                while True:
                    g_str = input(f'  Spiele pro Team pro Spieltag [{valid_gpd[0]}]: ').strip()
                    g_str = g_str or str(valid_gpd[0])
                    try:
                        gpd = int(g_str)
                        if gpd in valid_gpd:
                            break
                        err(f'Muss einer von {valid_gpd} sein.')
                    except ValueError:
                        err('Bitte eine Zahl eingeben.')

            import math as _math
            k_group  = 0  # Stufe 1 default
            n_active = 0  # 0 = alle Teams

            # Wie viele Teams sollen pro Spieltag spielen? (Spielfrei-Modus)
            # Gueltige Werte: a Teams/Tag, so dass Gesamtspiele aufgehen
            total_matches = n_rounds * n_t * (n_t - 1) // 2
            valid_active = [a for a in range(gpd + 1, n_t + 1)
                            if a * gpd % 2 == 0
                            and (total_matches * 2) % (a * gpd) == 0]
            if len(valid_active) > 1:
                print('  Wie viele Teams sollen pro Spieltag spielen?')
                for a in valid_active:
                    bye = n_t - a
                    n_days_a = total_matches * 2 // (a * gpd)
                    if bye == 0:
                        print(f'    {a} = alle Teams (kein Spielfrei, {n_days_a} Spieltage)  [Standard]')
                    else:
                        print(f'    {a} = {a} Teams/Tag ({bye} Teams Spielfrei, {n_days_a} Spieltage)')
                while True:
                    a_str = input(f'  Teams pro Spieltag [{n_t}]: ').strip() or str(n_t)
                    try:
                        a_val = int(a_str)
                        if a_val in valid_active:
                            n_active = 0 if a_val == n_t else a_val
                            break
                        err(f'Muss einer von {valid_active} sein.')
                    except ValueError:
                        err('Bitte eine Zahl eingeben.')

            if n_active > 0:
                # Spielfrei-Modus: 1 Gruppe mit n_active Teams, Rest hat Spielfrei
                k_group = n_active
                n_events = total_matches * 2 // (n_active * gpd)
                mode_label = (f'Turniertag ({gpd} Spiele/Tag, {n_rounds} Runden, '
                              f'{n_active}/{n_t} Teams/Tag, {n_t - n_active} Spielfrei)')
            else:
                # Alle Teams spielen – optionale Gruppen-Konfiguration (Stufe 2)
                valid_k = [K for K in range(2, n_t + 1)
                           if n_t % K == 0 and (n_t - 1) % gpd == 0
                           and K * gpd % 2 == 0 and gpd <= K - 1]
                if valid_k and len(valid_k) > 1:
                    print('  Gruppen-Konfiguration:')
                    print(f'    {n_t} = Alle Teams an einem Ort (Stufe 1)  [Standard]')
                    for K in valid_k:
                        if K < n_t:
                            G = _math.ceil(n_t / K)
                            n_days = _math.ceil(n_t * (n_t - 1) * n_rounds / max(1, G * K * gpd))
                            print(f'    {K} = {K} Teams/Gruppe ({G} Gruppen, {n_days} Spieltage)')
                    while True:
                        k_str = input(f'  Teams pro Gruppe [{n_t}]: ').strip() or str(n_t)
                        try:
                            k_val = int(k_str)
                            if k_val == n_t:
                                k_group = 0
                                break
                            if k_val in valid_k and k_val < n_t:
                                k_group = k_val
                                break
                            err(f'Muss {n_t} oder einer von {[K for K in valid_k if K < n_t]} sein.')
                        except ValueError:
                            err('Bitte eine Zahl eingeben.')

                if k_group > 0:
                    G = _math.ceil(n_t / k_group)
                    n_events = _math.ceil(n_t * (n_t - 1) * n_rounds / max(1, G * k_group * gpd))
                    mode_label = f'Turniertag ({gpd} Spiele/Tag, {n_rounds} Runden, {k_group} Teams/Gruppe)'
                else:
                    n_events = n_rounds * (n_t - 1) // max(1, gpd)
                    mode_label = f'Turniertag ({gpd} Spiele/Tag, {n_rounds} Runden)'

            # ── Spielreihenfolge-Einstellungen (Turniertag) ───────────────────
            _n_games_tt = (n_active if n_active > 0 else n_t) * gpd // 2
            info(f'  Spielreihenfolge: {_n_games_tt} Spiele pro Spieltag.')
            _mg = 0
            _xg = max(1, _n_games_tt)
            if _n_games_tt >= 2:
                _mg = ask_int(
                    '  Min. Pause zw. Spielen eines Teams (0 = kein Mindestabstand)',
                    0, _n_games_tt - 2, default=0)
                _xg = ask_int(
                    f'  Max. Pause zw. Spielen eines Teams '
                    f'(mind. {_mg + 1}, {_n_games_tt} = kein Limit)',
                    _mg + 1, _n_games_tt, default=min(3, _n_games_tt))
            _hs: List[int] = []
            if ask_yes_no('  Ausrichter-Spielpositionen festlegen?'):
                info(f'  Slots 1-{_n_games_tt}. Ausrichter hat {gpd} Spiel(e) pro Spieltag.')
                for _gi in range(gpd):
                    while True:
                        _s_raw = input(
                            f'    Slot fuer Ausrichterspiel {_gi + 1} '
                            f'(1-{_n_games_tt}, 0 = kein): ').strip()
                        try:
                            _s = int(_s_raw)
                            if 0 <= _s <= _n_games_tt:
                                if _s > 0:
                                    _hs.append(_s)
                                break
                            err(f'Bitte 0 bis {_n_games_tt} eingeben.')
                        except ValueError:
                            err('Bitte eine ganze Zahl eingeben.')
            _n_days_tt = (n_events if n_events > 0
                          else n_rounds * (n_t - 1) // max(1, gpd))
            _hc: Dict[str, int] = {}
            if ask_yes_no('  Ausrichter pro Team festlegen?'):
                info(f'  {_n_days_tt} Spieltage. Wie oft soll jedes Team Ausrichter sein?')
                _host_sum = 0
                for _tn in teams:
                    _c = ask_int(f'    {_tn}', 0, _n_days_tt, default=0)
                    if _c > 0:
                        _hc[_tn] = _c
                    _host_sum += _c
                if _host_sum != _n_days_tt:
                    warn(f'Summe Ausrichter ({_host_sum}) != Spieltage ({_n_days_tt}) '
                         f'– wird automatisch aufgefuellt.')
            tt_settings = {
                'min_gap':    _mg,
                'max_gap':    _xg,
                'host_slots': _hs if _hs else None,
                'host_mode':  'per_team',
                'host_counts': _hc,
            }

        n_t = len(teams)
        if gpd == 1 and k_group == 0:
            n_md = n_rounds * (n_t - 1)
            info(f'  {mode_label}: {n_md} Spieltage.')
        else:
            info(f'  {mode_label}: {n_events} Spieltage.')

        result[lid] = (teams, locations, name, hw, gpd, n_rounds, k_group, n_active, tt_settings)
        ok(f'  {lid}: {n_t} Teams, Format: {mode_label}.')

    # Leistungshinweis bei vielen Teams
    total_teams = sum(len(t) for t, *_ in result.values())
    if total_teams > 48:
        warn(f'Hinweis: {total_teams} Teams gesamt – Phase 2 (kombiniertes Modell) '
             f'koennte mehrere Stunden dauern.')
    elif total_teams > 36:
        info(f'{total_teams} Teams gesamt – Phase 2 benoetigt ggf. 60-90 Minuten.')

    return result


# ── Schritt 1: Distanzmatrizen ────────────────────────────────────────────────

def step1_distances(league_defs: Dict[str, Tuple[List[str], List[str], str, float, int, int]],
                    cache_dir: Path) -> Optional[Dict[str, object]]:
    section('SCHRITT 1: DISTANZMATRIZEN')
    info('Fuer jede Liga wird eine NxN-Distanzmatrix (km) benoetigt.')
    print()
    print('  Methoden:')
    print('    1 = Google Maps API  (automatisch, benoetigt API-Key)')
    print('    2 = Datei laden      (CSV oder Excel, siehe Dokumentation)')
    print('    3 = Manuell eingeben (empfohlen fuer kleine Ligen bis 6 Teams)')
    print()

    while True:
        ch = input('  Methode (1/2/3) [Standard: 1]: ').strip()
        if ch in ('', '1', '2', '3'):
            break
        err('Bitte 1, 2 oder 3 eingeben.')
    method = ch if ch else '1'

    api_key = None
    if method == '1':
        api_key = get_api_key()
        if not api_key:
            err('Kein API-Key. Bitte andere Methode waehlen.')
            return None

    dist_per_liga = {}

    for lid, (teams, locations, name, _, _, _, _, *_r) in league_defs.items():
        n = len(teams)
        print(f'\n  {name} ({lid}): {n} Teams')

        if method == '1':
            cache_path = cache_dir / f'dist_{lid}.json'
            dist = calculate_distance_matrix(locations, api_key, cache_path)
            if dist is None:
                err(f'Distanzmatrix fuer {lid} nicht verfuegbar.')
                return None

        elif method == '2':
            while True:
                path = ask_path(f'  Datei fuer {lid} (CSV oder Excel)')
                if not path:
                    err('Kein Pfad angegeben.')
                    continue
                dist = load_distances_from_file(path, teams)
                if dist is not None:
                    break
                if not ask_yes_no('  Erneut versuchen?'):
                    return None

        else:  # method == '3'
            dist = enter_distances_manually(teams)

        dist_per_liga[lid] = dist
        ok(f'  {lid}: {n}x{n} Distanzmatrix bereit.')

    return dist_per_liga


# ── Schritt 2: Kalender und DST ───────────────────────────────────────────────

def step2_calendar_and_dst(
        league_defs: Dict[str, Tuple[List[str], List[str], str, float, int, int]]
) -> Tuple[Dict[str, List[Tuple[int, int]]], Dict[int, Dict[str, List[int]]]]:
    """Gibt (dst_per_liga, kw_compat) zurueck."""
    section('SCHRITT 2: KALENDER & DOPPELSPIELTAGE (DST)')

    dst_result: Dict[str, List[Tuple[int, int]]] = {}
    kw_compat:  Dict[int, Dict[str, List[int]]]  = {}

    use_cal = ask_yes_no('Rahmenterminplan (Excel) laden? '
                          '(Nein = DST manuell eingeben, kein Kalender)')

    if use_cal:
        path = ask_path('Pfad zur Rahmenplan-Excel-Datei')
        if not path:
            warn('Kein Pfad – fahre ohne Kalender fort.')
            use_cal = False

    if use_cal:
        # Spalten-Mapping: Benutzer zeigt auf welche Spalte fuer jede Liga
        preview = preview_columns(path)
        if preview is not None:
            info('Erste Zeilen der Datei (Spalten-Index startet bei 0):')
            for col_idx in range(min(25, len(preview.columns))):
                vals = preview.iloc[:, col_idx].dropna().astype(str).tolist()[:3]
                print(f'    Spalte {col_idx:2d}: {" | ".join(vals)}')

        print()
        info('Weise jeder Liga eine Spalte zu (Spieltag-Nummern stehen dort).')
        col_mapping: Dict[str, int] = {}
        for lid, (_, _, name, _, _, _, _, *_r) in league_defs.items():
            while True:
                raw = input(f'  Spaltenindex fuer {name} ({lid}): ').strip()
                try:
                    col_mapping[lid] = int(raw)
                    break
                except ValueError:
                    err('Bitte eine ganze Zahl eingeben.')

        kw_col      = ask_int('KW-Spaltenindex', 0, 50, default=16)
        date_from   = ask_int('Datum-Von-Spaltenindex', 0, 50, default=17)
        date_to     = ask_int('Datum-Bis-Spaltenindex', 0, 50, default=18)

        cal = parse_rahmenterminplan(path, col_mapping,
                                      kw_col=kw_col,
                                      date_from_col=date_from,
                                      date_to_col=date_to)
        if cal is None:
            warn('Kalender konnte nicht gelesen werden – fahre ohne Kalender fort.')
            use_cal = False
        else:
            kw_compat = cal.get('kw_compat', {})
            cal_dst   = cal.get('dst_blocks', {})

            # DST aus Kalender vorbelegen
            for lid, (teams, _, name, _, gpd, n_rounds_lid, _, *_r) in league_defs.items():
                n_md = n_rounds_lid * (len(teams) - 1)
                if gpd > 1:
                    dst_result[lid] = []  # kompaktes Turniertag-Modell braucht keine DST-Bloecke
                    ok(f'  {lid}: Turniertag ({gpd} Spiele/Tag) – keine DST-Bloecke noetig.')
                    continue
                hint = cal_dst.get(lid, [])
                print(f'\n  {name}:')
                if hint:
                    info(f'  Aus Kalender: {hint}')
                    if ask_yes_no('  DST-Bloecke aus Kalender uebernehmen?'):
                        dst_result[lid] = hint
                        ok(f'  {lid}: {hint}')
                        continue
                dst_result[lid] = _input_dst_manual(lid, name, len(teams), n_md)

    if not use_cal:
        # Manuell DST eingeben, kein Kalender
        for lid, (teams, _, name, _, gpd, n_rounds, _, *_r) in league_defs.items():
            n_md = n_rounds * (len(teams) - 1)
            if gpd > 1:
                dst_result[lid] = []  # kompaktes Turniertag-Modell braucht keine DST-Bloecke
                ok(f'  {lid}: Turniertag ({gpd} Spiele/Tag) – keine DST-Bloecke noetig.')
                continue
            print(f'\n  {name}:')
            dst_result[lid] = _input_dst_manual(lid, name, len(teams), n_md)

    return dst_result, kw_compat


def _input_dst_manual(lid: str, name: str, n_teams: int,
                       n_md: int) -> List[Tuple[int, int]]:
    """Fragt DST-Bloecke manuell ab."""
    num = ask_int(f'  Anzahl DST-Bloecke fuer {name} (0 = keine)', 0, n_teams - 1, default=0)
    if num == 0:
        return []

    blocks, used = [], set()
    for i in range(num):
        while True:
            raw = input(f'    DST {i+1} (d1,d2): ').strip()
            try:
                d1, d2 = [int(x.strip()) for x in raw.split(',')]
            except Exception:
                err('Format: d1,d2'); continue
            if not (1 <= d1 <= n_md and 1 <= d2 <= n_md):
                err(f'Spieltage 1-{n_md}'); continue
            if abs(d2 - d1) != 1:
                err('Aufeinanderfolgende Spieltage erforderlich.'); continue
            if d1 in used or d2 in used:
                err('Spieltag bereits belegt.'); continue
            blk = (min(d1, d2), max(d1, d2))
            blocks.append(blk); used.update(blk)
            ok(f'    DST: ST{blk[0]}+ST{blk[1]}'); break

    ok(f'  {lid}: {blocks}')
    return blocks


# ── Schritt 3: DST-Routing ────────────────────────────────────────────────────

def step3_routing(league_defs: Dict,
                  dst_per_liga: Dict[str, List]) -> Dict[str, Tuple[bool, int, int]]:
    section('SCHRITT 3: DST ROUTING-OPTIMIERUNG')
    result = {}
    for lid, (_, _, name, _, _, _, _, *_r) in league_defs.items():
        if not dst_per_liga.get(lid):
            result[lid] = (False, 125, 100)
            continue
        print(f'\n  {name}:')
        if not ask_yes_no('  Routing-Optimierung aktivieren?'):
            result[lid] = (False, 125, 100)
            continue
        pct = 25
        if ask_yes_no('  Standard 25% Mehrkilometer aendern?'):
            pct = ask_int('  Erlaubte Mehrkilometer (%)', 0, 200, default=25)
        result[lid] = (True, 100 + pct, 100)
        ok(f'  {lid}: Routing aktiv ({100 + pct}%)')
    return result


# ── Schritt 4: Gewichtungen ───────────────────────────────────────────────────

def step4_weights(league_defs: Dict) -> Tuple[Dict[str, Dict], Dict[str, float], float]:
    """Gibt (w_scaled_per_liga, raw_per_liga, w_cohome) zurueck."""
    section('SCHRITT 4: OPTIMIERUNGS-GEWICHTUNGEN')
    info('Gewichte 0-10 pro Liga. Ligahierarchie skaliert Ligen untereinander.')

    lids = list(league_defs.keys())
    use_same = ask_yes_no('Gleiche Gewichte fuer alle Ligen verwenden?')

    if use_same:
        print('  Gewichte fuer alle Ligen:')
        common_raw = {}
        for key, label in WEIGHT_LABELS:
            print(f'  - {label}')
            common_raw[key] = ask_float('    Wichtigkeit (0-10)', 0, 10, default=5)
        raw_per_liga = {lid: common_raw.copy() for lid in lids}
    else:
        raw_per_liga = {}
        for lid, (_, _, name, _, _, _, _, *_r) in league_defs.items():
            print(f'\n  {name}:')
            raw = {}
            for key, label in WEIGHT_LABELS:
                print(f'  - {label}')
                raw[key] = ask_float(f'    Wichtigkeit ({lid})', 0, 10, default=5)
            raw_per_liga[lid] = raw

    w_scaled_per_liga = {
        lid: {k: v * WEIGHT_SCALES[k] for k, v in raw_per_liga[lid].items()}
        for lid in lids
    }
    for lid, (_, _, _, hw, _, _, _, *_r) in league_defs.items():
        w_scaled_per_liga[lid]['hier'] = hw

    # Co-Home-Gewicht (nur bei mehreren Ligen sinnvoll)
    w_cohome = 0.0
    if len(lids) >= 2:
        section('CO-HOME-BONUS-GEWICHT')
        info('Wie wichtig ist es, dass Mehrspartenvereine gemeinsam Heimspiele haben?')
        info('0 = ignorieren, 5 = mittelwichtig, 10 = hohe Prioritaet')
        w_cohome = ask_float('Co-Home-Gewicht (0-10)', 0, 10, default=5)
        ok(f'Co-Home-Gewicht: {w_cohome}')

    return w_scaled_per_liga, raw_per_liga, w_cohome


# ── Schritt 5: Pflichtspiele ──────────────────────────────────────────────────

def step5_pinned(league_defs: Dict) -> Dict[str, List[dict]]:
    section('SCHRITT 5: PFLICHTSPIELE')
    result = {lid: [] for lid in league_defs}

    if not ask_yes_no('Pflichtspiele definieren?'):
        return result

    for lid, (teams, _, name, _, gpd, n_rounds, _, *_r) in league_defs.items():
        n_md = n_rounds * (len(teams) - 1) // max(1, gpd)
        print(f'\n  {name}:')
        if not ask_yes_no(f'  Pflichtspiele fuer {lid} definieren?'):
            continue

        while True:
            while True:
                a = input('    Team A: ').strip()
                if a in teams: break
                err(f"'{a}' nicht gefunden.")
            while True:
                b = input('    Team B: ').strip()
                if b in teams and b != a: break
                err('Team B ungueltig.')
            day = ask_int('    Spieltag', 1, n_md)
            print(f'    Heimteam? 1={a}  2={b}  3=beliebig')
            while True:
                ch = input('    Auswahl (1/2/3): ').strip()
                if ch == '1': home = a; break
                if ch == '2': home = b; break
                if ch == '3': home = None; break
                err('Bitte 1/2/3.')
            result[lid].append({'teamA': a, 'teamB': b, 'day': day, 'home': home})
            ok(f'    Pflichtspiel: {a} vs. {b} ST{day}')
            if not ask_yes_no('    Weiteres Pflichtspiel?'):
                break

    return result


# ── Schritt 6: Sperrtage ──────────────────────────────────────────────────────

def step6_blocked(league_defs: Dict) -> Dict[str, Dict[str, List[int]]]:
    section('SCHRITT 6: HEIMSPIEL-SPERRTAGE')
    result = {lid: {} for lid in league_defs}

    if not ask_yes_no('Heimspiel-Sperrtage definieren?'):
        return result

    for lid, (teams, _, name, _, gpd, n_rounds, _, *_r) in league_defs.items():
        n_md = n_rounds * (len(teams) - 1) // max(1, gpd)
        print(f'\n  {name}:')
        if not ask_yes_no(f'  Sperrtage fuer {lid} definieren?'):
            continue

        while True:
            while True:
                t = input('    Team: ').strip()
                if t in teams: break
                err(f"'{t}' nicht gefunden.")
            while True:
                raw = input(f"    Gesperrte Spieltage fuer '{t}' (kommagetrennt): ").strip()
                try:
                    days = sorted(set(int(x.strip()) for x in raw.split(',') if x.strip()))
                except Exception:
                    err('Format: 3,7,12'); continue
                if not days or not all(1 <= d <= n_md for d in days):
                    err(f'Spieltage 1-{n_md}'); continue
                result[lid].setdefault(t, [])
                result[lid][t] = sorted(set(result[lid][t]).union(days))
                break
            ok(f'    {t}: gesperrt an {result[lid][t]}')
            if not ask_yes_no('    Weiteres Team?'):
                break

    return result


# ── Schritt 7: Co-Home ────────────────────────────────────────────────────────

def step7_cohome(league_defs: Dict) -> Dict[str, Dict[str, str]]:
    """Konfiguriert Mehrsparten-Vereine (nur bei >= 2 Ligen sinnvoll)."""
    section('SCHRITT 7: CO-HOME-VEREINE')

    lids = list(league_defs.keys())
    if len(lids) < 2:
        info('Nur eine Liga – Co-Home nicht relevant.')
        return {}

    # Teams aller Ligen anzeigen
    info('Mehrsparten-Vereine haben Teams in mehreren Ligen.')
    info('Gib an, welche Teams zu demselben Verein gehoeren.')

    if not ask_yes_no('Mehrsparten-Vereine konfigurieren?'):
        return {}

    clubs: Dict[str, Dict[str, str]] = {}

    while True:
        club_name = input('\n  Vereinsname (leer = fertig): ').strip()
        if not club_name:
            break

        liga_map: Dict[str, str] = {}
        for lid, (teams, _, name, _, _, _, _) in league_defs.items():
            team_list = ', '.join(teams)
            raw = input(f'  Teamname in {name} ({lid}) '
                        f'[leer = kein Team]: ').strip()
            if raw and raw in teams:
                liga_map[lid] = raw
            elif raw:
                warn(f"'{raw}' nicht in {lid} – uebersprungen.")

        if len(liga_map) >= 2:
            clubs[club_name] = liga_map
            ok(f'  Verein "{club_name}": {liga_map}')
        else:
            warn('  Weniger als 2 Ligen – Verein nicht gespeichert.')

        if not ask_yes_no('  Weiteren Verein hinzufuegen?'):
            break

    ok(f'{len(clubs)} Mehrsparten-Vereine konfiguriert.')
    return clubs


# ── Schritt 8: Solver-Konfiguration ──────────────────────────────────────────

def step8_solver() -> Tuple[int, int, bool, int, int]:
    """Gibt (phase1_time, phase2_time, night_mode, n_seeds, sa_time) zurueck."""
    section('SCHRITT 8: SOLVER-KONFIGURATION')
    info('Phase 1: Alle Ligen parallel (Warm-Start-Vorbereitung)')
    info('Phase 2: Gemeinsames Modell (Co-Home + Hierarchie)')
    info('Phase 3: SA-Nachbearbeitung (Heimrecht-Optimierung)')

    p1 = ask_int('Phase-1-Zeitlimit pro Liga (Sekunden)', 60, 3600, default=900)
    info(f'Phase 1: {p1}s Wandzeit (alle Ligen laufen parallel)')

    print()
    info('Phase-2-Modi:')
    print('    1 = Standard      (90 min, Gap-Limit 2%)')
    print('    2 = Intensiv      (3 h,    Gap-Limit 1%)')
    print('    3 = Nachtlauf     (8 h,    kein Gap-Limit)')
    while True:
        ch = input('  Modus (1/2/3) [Standard: 1]: ').strip()
        if ch in ('', '1'):
            p2, nm = 5400, False; break
        if ch == '2':
            p2, nm = 10800, False; break
        if ch == '3':
            p2, nm = 28800, True; break
        err('Bitte 1, 2 oder 3 eingeben.')

    print()
    n_seeds = ask_int('Seeds pro Liga in Phase 1 (mehr = bessere Startloesungen)', 1, 4, default=2)
    info(f'Phase 1: {n_seeds} Seeds pro Liga – beste Loesung gewinnt.')

    print()
    sa_time = ask_int('SA-Nachbearbeitung pro Liga (Sekunden, 0 = deaktiviert)', 0, 600, default=120)
    if sa_time > 0:
        info(f'Phase 3: {sa_time}s SA pro Liga.')
    else:
        info('Phase 3: deaktiviert.')

    return p1, p2, nm, n_seeds, sa_time


# ── Schritt 9: Validierung ────────────────────────────────────────────────────

def step9_validate(cfgs: Dict) -> bool:
    """Schritt 9: Constraint-Prüfung auf Basis fertiger LeagueConfig-Objekte."""
    from .config_validator import validate_cfgs
    section('SCHRITT 9: CONSTRAINT-VALIDIERUNG')

    issues = validate_cfgs(cfgs)
    errors   = [i for i in issues if i['level'] == 'error']
    warnings = [i for i in issues if i['level'] == 'warning']

    for i in warnings:
        lid_lbl = f'[{i["lid"]}] ' if i.get('lid') else ''
        warn(f'{lid_lbl}{i["msg"]}')
    for i in errors:
        lid_lbl = f'[{i["lid"]}] ' if i.get('lid') else ''
        err(f'{lid_lbl}{i["msg"]}')

    if not issues:
        ok('Keine Konflikte gefunden.')

    return len(errors) == 0


# ── Konfigurationsobjekte aufbauen ────────────────────────────────────────────

def build_configs(league_defs: Dict,
                  dist_per_liga: Dict,
                  dst_per_liga: Dict,
                  routing_per_liga: Dict,
                  w_scaled_per_liga: Dict,
                  raw_per_liga: Dict,
                  pinned_per_liga: Dict,
                  blocked_per_liga: Dict,
                  kw_compat: Dict) -> Dict[str, LeagueConfig]:
    """Erstellt LeagueConfig-Objekte fuer alle Ligen."""
    from .calendar_parser import build_weekends

    # Kalender-Spieltage ableiten aus kw_compat
    spieltage_per_liga: Dict[str, Dict] = {}
    for kw, kw_data in kw_compat.items():
        for lid, sts in kw_data.items():
            spieltage_per_liga.setdefault(lid, {})
            for st in sts:
                spieltage_per_liga[lid][st] = {'kw': kw}

    import math as _math
    cfgs = {}
    for lid, league_def in league_defs.items():
        # Tuple kann 7 (legacy), 8 oder 9 Elemente haben
        if len(league_def) >= 9:
            teams, locations, name, hw, gpd, n_rounds, k_group, n_active, tt_settings = league_def[:9]
        elif len(league_def) == 8:
            teams, locations, name, hw, gpd, n_rounds, k_group, n_active = league_def
            tt_settings = {}
        else:
            teams, locations, name, hw, gpd, n_rounds, k_group = league_def
            n_active = 0
            tt_settings = {}
        dst   = dst_per_liga.get(lid, [])
        n = len(teams)
        K = k_group if k_group > 0 and k_group < n else 0
        # n_matchdays: gleiche Formel wie LeagueConfig.n_matchdays
        if K > 0:
            na = n_active if n_active > 0 else n
            G = max(1, na // K)
            total_matches = n_rounds * n * (n - 1) // 2
            games_per_day = G * K * gpd // 2
            n_md = total_matches // games_per_day if games_per_day > 0 else n_rounds * (n - 1) // max(1, gpd)
        else:
            n_md = n_rounds * (n - 1) // max(1, gpd)
        days  = list(range(1, n_md + 1))
        cal   = spieltage_per_liga.get(lid, {})

        apply_r, f_num, f_den = routing_per_liga.get(lid, (False, 125, 100))
        raw    = raw_per_liga.get(lid, {k: 5.0 for k in WEIGHT_SCALES})
        scaled = {k: v * WEIGHT_SCALES[k] for k, v in raw.items()}

        cfgs[lid] = LeagueConfig(
            league_id=lid,
            name=name,
            teams=teams,
            locations=locations,
            dist=dist_per_liga[lid],
            dst_blocks=dst,
            weekends=build_weekends(days, dst),
            apply_routing=apply_r,
            f_num=f_num,
            f_den=f_den,
            w_scaled=scaled,
            raw_weights=raw,
            pinned=pinned_per_liga.get(lid, []),
            blocked=blocked_per_liga.get(lid, {}),
            calendar=cal,
            hier_weight=hw,
            games_per_team_per_day=gpd,
            n_rounds=n_rounds,
            n_teams_per_group=K,
            n_active_per_day=n_active,
            tt_settings=tt_settings,
        )
    return cfgs


# ── Vollstaendiger Wizard ─────────────────────────────────────────────────────

def run_wizard(cache_dir: Path) -> Optional[dict]:
    """Fuehrt alle Schritte durch. Gibt Config-Dict zurueck oder None bei Abbruch."""
    banner('SPIELPLAN-OPTIMIERER | Multi-Liga-Scheduler')

    # Schritt 0: Ligen definieren
    league_defs = step0_leagues()
    if not league_defs:
        err('Keine Ligen konfiguriert.')
        return None

    # Schritt 1: Distanzen
    dist_per_liga = step1_distances(league_defs, cache_dir)
    if dist_per_liga is None:
        return None

    # Schritt 2: Kalender + DST
    dst_per_liga, kw_compat = step2_calendar_and_dst(league_defs)

    # Schritt 3: Routing
    routing_per_liga = step3_routing(league_defs, dst_per_liga)

    # Schritt 4: Gewichtungen
    w_scaled_per_liga, raw_per_liga, w_cohome = step4_weights(league_defs)

    # Schritt 5: Pflichtspiele
    pinned_per_liga = step5_pinned(league_defs)

    # Schritt 6: Sperrtage
    blocked_per_liga = step6_blocked(league_defs)

    # Schritt 7: Co-Home
    active_clubs = step7_cohome(league_defs)

    # Schritt 8: Solver
    phase1_time, phase2_time, night_mode, n_seeds, sa_time = step8_solver()

    # Konfigurationsobjekte bauen (werden für Schritt 9 benötigt)
    cfgs = build_configs(league_defs, dist_per_liga, dst_per_liga,
                         routing_per_liga, w_scaled_per_liga, raw_per_liga,
                         pinned_per_liga, blocked_per_liga, kw_compat)

    # Schritt 9: Validierung
    valid = step9_validate(cfgs)
    if not valid:
        if not ask_yes_no('Trotz Konflikten fortfahren?'):
            return None

    return {
        'cfgs':        cfgs,
        'clubs':       active_clubs,
        'kw_compat':   kw_compat,
        'w_cohome':    w_cohome,
        'phase1_time': phase1_time,
        'phase2_time': phase2_time,
        'night_mode':  night_mode,
        'n_seeds':     n_seeds,
        'sa_time':     sa_time,
    }
