"""Hilfsfunktionen fuer nachtraegliche Spielplan-Bearbeitung und -Export.

Koennen unabhaengig von Streamlit importiert und getestet werden.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .league_types import LeagueConfig, LeagueResult


def assign_game_times(result, time_slots: list) -> None:
    """Weist Spielzeiten zu: time_slots[i] = Uhrzeit fuer das i-te Spiel des Tages.

    Leere Strings werden fuer Spiele ohne Slot gesetzt.
    Ergebnis wird direkt in result.game_times geschrieben.
    """
    game_times = {}
    for d, games in result.schedule.items():
        game_times[d] = [
            time_slots[i] if i < len(time_slots) else ''
            for i in range(len(games))
        ]
    result.game_times = game_times


def recompute_result_stats(result, cfg) -> tuple:
    """Berechnet travels, sw_counts, sw_rates aus dem aktuellen Schedule neu.

    Reisekilometer nach Transitions-Modell (identisch mit Solver/SA):
    summiert dist[loc[d], loc[d+1]] fuer aufeinanderfolgende Spieltage,
    wobei Heimteam am eigenen Standort, Gastteam am Standort des Heimteams.
    """
    n     = cfg.n_teams
    t_idx = {t: i for i, t in enumerate(cfg.teams)}
    dist  = cfg.dist
    days  = sorted(cfg.days)

    # loc[ti][pos] = Venue-Index fuer Team ti an Position pos in days
    # Default = eigener Standort (ti), wird durch Spieldaten ueberschrieben
    loc   = [[ti] * len(days) for ti in range(n)]
    d_pos = {d: i for i, d in enumerate(days)}

    for d, games in result.schedule.items():
        pos = d_pos.get(d)
        if pos is None:
            continue
        for ht, at in games:
            hi = t_idx.get(ht, -1)
            ai = t_idx.get(at, -1)
            if hi >= 0:
                loc[hi][pos] = hi
            if ai >= 0 and hi >= 0:
                loc[ai][pos] = hi

    travels = [0] * n
    for ti in range(n):
        for pos in range(len(days) - 1):
            travels[ti] += int(dist[loc[ti][pos], loc[ti][pos + 1]])

    weekends   = cfg.weekends
    sw_counts  = [0] * n
    for ti in range(n):
        prev = None
        for wknd in weekends:
            if not wknd:
                continue
            cur = result.home_vals.get((ti, wknd[0]))
            if cur is None:
                prev = None
                continue
            if prev is not None and cur != prev:
                sw_counts[ti] += 1
            prev = cur

    # Denominator: n_matchdays - 1 (Spieltag-Transitions), konsistent zum Solver.
    # cfg.n_transitions liefert genau diesen Wert.
    n_tr     = max(1, cfg.n_transitions)
    sw_rates = [round(100.0 * sw / n_tr, 1) for sw in sw_counts]
    return travels, sw_counts, sw_rates


def swap_home_away(result, cfg, day: int, match_idx: int) -> None:
    """Tauscht Heim- und Auswaertsteam fuer ein Spiel.

    Wirft KEINE Exception bei verbotenen Tagen, sondern returnt ohne Aenderung.
    Die UI sollte den Swap-Button bei DST-Tagen deaktivieren und einen Hinweis zeigen.
    """
    if cfg.games_per_team_per_day > 1:
        return  # Turniertag: home_vals sind Zaehler, kein einfacher Swap
    if day in cfg.dst_days:
        # DST-Partner-Tag hat andere Paarungen; ein Swap nur auf einem Tag wuerde
        # die DST-Invariante (gleiches Heimrecht beider Tage) brechen. Die alte
        # Logik versuchte den Partner mitzuziehen, hat dabei aber home_vals und
        # schedule fuer Teams gesetzt, die auf dem Partner-Tag andere Gegner haben.
        return
    t_idx = {t: i for i, t in enumerate(cfg.teams)}

    games = list(result.schedule.get(day, []))
    if match_idx >= len(games):
        return
    ht, at = games[match_idx]
    games[match_idx] = (at, ht)
    result.schedule[day] = games

    hi = t_idx.get(ht, -1)
    ai = t_idx.get(at, -1)

    # home_vals aktualisieren (nur fuer den Tag, da DST-Tage oben ausgeschlossen sind)
    if hi >= 0:
        result.home_vals[(hi, day)] = 0
    if ai >= 0:
        result.home_vals[(ai, day)] = 1

    travels, sw_counts, sw_rates = recompute_result_stats(result, cfg)
    result.travels   = travels
    result.sw_counts = sw_counts
    result.sw_rates  = sw_rates


def find_schedule_warnings(result, cfg) -> list:
    """Prueft den Spielplan auf unausgewogene Konstellationen.

    Gibt eine Liste von Dicts zurueck:
      {'team': str, 'text': str, 'severity': 'warn' | 'info'}
    """
    warnings = []
    n    = cfg.n_teams
    days = cfg.days

    for ti, team in enumerate(cfg.teams):
        cur_home = cur_away = max_home = max_away = 0
        for d in days:
            hv = result.home_vals.get((ti, d))
            if hv is None:
                cur_home = cur_away = 0
                continue
            if hv >= 1:
                cur_home += 1; cur_away = 0
            else:
                cur_away += 1; cur_home = 0
            max_home = max(max_home, cur_home)
            max_away = max(max_away, cur_away)

        if max_away >= 4:
            warnings.append({'team': team,
                              'text': f'{max_away}× Auswärts in Folge',
                              'severity': 'warn'})
        elif max_away == 3:
            warnings.append({'team': team,
                              'text': '3× Auswärts in Folge',
                              'severity': 'info'})
        if max_home >= 4:
            warnings.append({'team': team,
                              'text': f'{max_home}× Heim in Folge',
                              'severity': 'warn'})

    if result.travels and n > 1:
        avg_km = sum(result.travels) / n
        if avg_km > 0:
            for ti, team in enumerate(cfg.teams):
                km_ti = result.travels[ti] if ti < len(result.travels) else 0
                pct = (km_ti - avg_km) / avg_km * 100
                if pct > 35:
                    warnings.append({'team': team,
                                     'text': (f'+{pct:.0f}% über Ø-Reisekilometer '
                                              f'({km_ti:,} km)'),
                                     'severity': 'warn'})

    return warnings


def move_game(result, cfg, old_day: int, match_idx: int, new_day: int) -> str:
    """Verschiebt ein Spiel von old_day auf new_day.

    Gibt '' bei Erfolg zurueck, sonst eine Fehlermeldung.
    """
    if cfg.games_per_team_per_day > 1:
        return 'Verschieben bei Turniertag nicht unterstützt.'
    if new_day not in cfg.days:
        return f'Spieltag {new_day} existiert nicht im Spielplan.'
    t_idx     = {t: i for i, t in enumerate(cfg.teams)}
    games_old = list(result.schedule.get(old_day, []))
    if match_idx >= len(games_old):
        return 'Spiel nicht gefunden.'
    ht, at = games_old[match_idx]
    hi = t_idx.get(ht, -1)
    ai = t_idx.get(at, -1)

    teams_on_new = {t for pair in result.schedule.get(new_day, []) for t in pair}
    if ht in teams_on_new:
        return f'{ht} hat an Spieltag {new_day} bereits ein Spiel.'
    if at in teams_on_new:
        return f'{at} hat an Spieltag {new_day} bereits ein Spiel.'

    games_old.pop(match_idx)
    result.schedule[old_day] = games_old

    teams_still_old = {t for pair in games_old for t in pair}
    if hi >= 0 and ht not in teams_still_old:
        result.home_vals.pop((hi, old_day), None)
    if ai >= 0 and at not in teams_still_old:
        result.home_vals.pop((ai, old_day), None)

    result.schedule.setdefault(new_day, []).append((ht, at))
    if hi >= 0:
        result.home_vals[(hi, new_day)] = 1
    if ai >= 0:
        result.home_vals[(ai, new_day)] = 0

    travels, sw_counts, sw_rates = recompute_result_stats(result, cfg)
    result.travels   = travels
    result.sw_counts = sw_counts
    result.sw_rates  = sw_rates
    return ''


def cancel_game(result, cfg, day: int, match_idx: int):
    """Entfernt ein Spiel. Gibt (ht, at) zurueck oder (None, None) bei Fehler."""
    if cfg.games_per_team_per_day > 1:
        return None, None  # Turniertag: home_vals sind Zaehler, recompute liefert falsche travels
    t_idx = {t: i for i, t in enumerate(cfg.teams)}
    games = list(result.schedule.get(day, []))
    if match_idx >= len(games):
        return None, None
    ht, at = games.pop(match_idx)
    result.schedule[day] = games
    hi = t_idx.get(ht, -1)
    ai = t_idx.get(at, -1)

    teams_still = {t for pair in games for t in pair}
    if hi >= 0 and ht not in teams_still:
        result.home_vals.pop((hi, day), None)
    if ai >= 0 and at not in teams_still:
        result.home_vals.pop((ai, day), None)

    travels, sw_counts, sw_rates = recompute_result_stats(result, cfg)
    result.travels   = travels
    result.sw_counts = sw_counts
    result.sw_rates  = sw_rates
    return ht, at


def reschedule_game(result, cfg, day: int, home_team: str, away_team: str) -> str:
    """Fuegt ein Spiel (home_team vs away_team) an day ein.

    Gibt '' bei Erfolg zurueck, sonst eine Fehlermeldung.
    """
    if cfg.games_per_team_per_day > 1:
        return 'Nachholspiele bei Turniertag nicht unterstützt.'
    if home_team not in cfg.teams:
        return f'Team "{home_team}" nicht in der Liga.'
    if away_team not in cfg.teams:
        return f'Team "{away_team}" nicht in der Liga.'
    t_idx        = {t: i for i, t in enumerate(cfg.teams)}
    teams_on_day = {t for pair in result.schedule.get(day, []) for t in pair}
    if home_team in teams_on_day:
        return f'{home_team} hat an Spieltag {day} bereits ein Spiel.'
    if away_team in teams_on_day:
        return f'{away_team} hat an Spieltag {day} bereits ein Spiel.'

    result.schedule.setdefault(day, []).append((home_team, away_team))
    hi = t_idx.get(home_team, -1)
    ai = t_idx.get(away_team, -1)
    if hi >= 0:
        result.home_vals[(hi, day)] = 1
    if ai >= 0:
        result.home_vals[(ai, day)] = 0

    travels, sw_counts, sw_rates = recompute_result_stats(result, cfg)
    result.travels   = travels
    result.sw_counts = sw_counts
    result.sw_rates  = sw_rates
    return ''


def find_free_days(result, cfg, team_a: str, team_b: str) -> list:
    """Spieltage in cfg.days, an denen weder team_a noch team_b ein Spiel haben."""
    busy: dict = {d: {t for pair in games for t in pair}
                  for d, games in result.schedule.items()}
    return [d for d in cfg.days
            if team_a not in busy.get(d, set()) and team_b not in busy.get(d, set())]


def build_ics_bytes(result, season_year: int) -> bytes:
    """Erzeugt eine .ics-Datei mit allen Spielen der Liga."""
    import datetime as _dt
    cfg        = result.cfg
    t_idx      = {t: i for i, t in enumerate(cfg.teams)}
    dst_d2     = {d2 for _, d2 in cfg.dst_blocks}
    round_len  = cfg.n_matchdays // max(1, cfg.n_rounds)
    _phase_lbl = {1: 'Hinrunde', 2: 'Rueckrunde', 3: 'Dritte Runde'}
    is_tt      = cfg.games_per_team_per_day > 1

    def _date_for(d):
        kw = cfg.calendar.get(d, {}).get('kw')
        if not kw:
            return None
        try:
            yr  = season_year + 1 if int(kw) <= 26 else season_year
            sat = _dt.date.fromisocalendar(yr, int(kw), 6)
            return sat + _dt.timedelta(days=1) if d in dst_d2 else sat
        except (ValueError, TypeError):
            return None

    def _ical_escape(s: str) -> str:
        s = s.replace('\\', '\\\\')
        s = s.replace(';', '\\;')
        s = s.replace(',', '\\,')
        s = s.replace('\n', '\\n')
        return s

    def _ical_fold(line: str) -> str:
        encoded = line.encode('utf-8')
        if len(encoded) <= 75:
            return line
        chunks = []
        start = 0
        first = True
        while start < len(encoded):
            limit = 75 if first else 74
            first = False
            end = start + limit
            if end >= len(encoded):
                chunks.append(encoded[start:].decode('utf-8'))
                break
            while end > start and (encoded[end] & 0xC0) == 0x80:
                end -= 1
            chunks.append(encoded[start:end].decode('utf-8'))
            start = end
        return '\r\n '.join(chunks)

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Spielplan-Optimierer//FD//DE',
        'CALSCALE:GREGORIAN',
        f'X-WR-CALNAME:{_ical_escape(cfg.name)}',
    ]

    dtstamp = _dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    uid_n = 0
    for d in cfg.days:
        date  = _date_for(d)
        rnd   = min(cfg.n_rounds, (d - 1) // round_len + 1)
        phase = _phase_lbl.get(rnd, f'Runde {rnd}')
        for ht, at in result.schedule.get(d, []):
            hi  = t_idx.get(ht, -1)
            loc = cfg.locations[hi] if 0 <= hi < len(cfg.locations) else ht
            uid_n += 1
            uid   = f'{cfg.league_id}-ST{d:03d}-{uid_n}@flvd.de'
            host  = f' · Ausrichter: {result.hosts[d]}' if is_tt and d in result.hosts else ''
            desc  = f'Spieltag {d} · {phase}{host} · {cfg.name}'
            if not date:
                continue  # Kein Datum verfuegbar – Spiel aus iCal ausschliessen
            dt_str   = date.strftime('%Y%m%d')
            dt_end   = (date + _dt.timedelta(days=1)).strftime('%Y%m%d')
            dt_lines = [f'DTSTART;VALUE=DATE:{dt_str}', f'DTEND;VALUE=DATE:{dt_end}']
            lines += ['BEGIN:VEVENT', f'UID:{uid}', f'DTSTAMP:{dtstamp}'] + dt_lines + [
                f'SUMMARY:{_ical_escape(f"{ht} vs. {at}")}',
                f'LOCATION:{_ical_escape(loc)}',
                f'DESCRIPTION:{_ical_escape(desc)}',
                'END:VEVENT',
            ]

    lines.append('END:VCALENDAR')
    return '\r\n'.join(_ical_fold(ln) for ln in lines).encode('utf-8')


# ── Druckbarer Spielplan (HTML) ───────────────────────────────────────────────

def build_print_html(result, season_year: int = 0) -> str:
    """Erzeugt einen druckbaren HTML-Spielplan (oeffnen im Browser, dann Drucken/PDF)."""
    import html as _html
    from .config import get_team_color

    cfg       = result.cfg
    teams     = cfg.teams
    n         = cfg.n_teams
    t_idx     = {t: i for i, t in enumerate(teams)}
    dst_days  = cfg.dst_days
    dst_d2    = {d2 for _, d2 in cfg.dst_blocks}
    round_len = cfg.n_matchdays // max(1, cfg.n_rounds)
    is_tt     = cfg.games_per_team_per_day > 1
    _ph       = {1: 'Hinrunde', 2: 'Rückrunde', 3: 'Dritte Runde'}

    def _esc(s):  return _html.escape(str(s))
    def _tc(idx): return '#' + get_team_color(idx)

    def _kw_label(d):
        kw = cfg.calendar.get(d, {}).get('kw', '')
        return f'KW {kw}' if kw else ''

    def _date_str(d):
        if not season_year:
            return ''
        import datetime as _dt
        kw = cfg.calendar.get(d, {}).get('kw')
        if not kw:
            return ''
        try:
            yr  = season_year + 1 if int(kw) <= 26 else season_year
            sat = _dt.date.fromisocalendar(yr, int(kw), 6)
            day = sat + _dt.timedelta(days=1) if d in dst_d2 else sat
            return day.strftime('%d.%m.%Y')
        except (ValueError, TypeError):
            return ''

    # CSS
    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, Helvetica, sans-serif; font-size: 11px;
           color: #222; background: #fff; padding: 16px; }
    h1 { font-size: 17px; margin-bottom: 2px; color: #1F3864; }
    .meta { font-size: 10px; color: #666; margin-bottom: 14px; }
    h2 { font-size: 13px; margin: 18px 0 5px; color: #1F3864;
         border-bottom: 2px solid #4472C4; padding-bottom: 3px; }
    h3 { font-size: 11px; margin: 12px 0 3px; color: #4472C4; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 8px; }
    th { background: #4472C4; color: #fff; padding: 4px 7px;
         text-align: center; font-size: 10px; white-space: nowrap; }
    td { padding: 3px 6px; border: 1px solid #ddd; vertical-align: middle; }
    tr:nth-child(even) td { background: #f7f8fa; }
    .dst-row td { background: #FFF2CC !important; }
    .phase-sep td { background: #D9E1F2; font-weight: bold;
                    text-align: center; font-size: 10px; }
    .team-name { font-weight: bold; padding: 2px 6px; border-radius: 3px;
                 display: inline-block; }
    .heim-tag { background: #C6EFCE; color: #006100; padding: 1px 5px;
                border-radius: 3px; font-weight: bold; font-size: 9px; }
    .ausw-tag { background: #FFE0E0; color: #9C0006; padding: 1px 5px;
                border-radius: 3px; font-weight: bold; font-size: 9px; }
    .dst-tag  { background: #FFF2CC; color: #9C6500; padding: 1px 5px;
                border-radius: 3px; font-size: 9px; }
    .print-btn { margin-bottom: 14px; }
    .print-btn button { background: #4472C4; color: white; border: none;
                        padding: 7px 18px; font-size: 12px; border-radius: 4px;
                        cursor: pointer; }
    .print-btn button:hover { background: #2b57a0; }
    .stats-grid { display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 14px; }
    .stat-box { border: 1px solid #ddd; border-radius: 4px; padding: 6px 12px;
                background: #f7f8fa; min-width: 120px; }
    .stat-label { font-size: 9px; color: #888; }
    .stat-val   { font-size: 14px; font-weight: bold; color: #1F3864; }
    @media print {
      @page { size: A4 landscape; margin: 1.2cm; }
      body { padding: 0; font-size: 10px; }
      .print-btn { display: none; }
      h2 { margin-top: 14px; }
      .team-section { page-break-inside: avoid; }
    }
    """

    # Statistik-Boxen
    avg_km   = sum(result.travels) / n if n else 0
    avg_sw   = sum(result.sw_rates) / n if n else 0
    total_km = sum(result.travels)
    stat_html = '<div class="stats-grid">'
    stat_html += f'<div class="stat-box"><div class="stat-label">Gesamt-km</div><div class="stat-val">{total_km:,}</div></div>'
    stat_html += f'<div class="stat-box"><div class="stat-label">&#216; km/Team</div><div class="stat-val">{avg_km:.0f}</div></div>'
    stat_html += f'<div class="stat-box"><div class="stat-label">&#216; Wechselquote</div><div class="stat-val">{avg_sw:.0f}%</div></div>'
    stat_html += f'<div class="stat-box"><div class="stat-label">Spieltage</div><div class="stat-val">{cfg.n_matchdays}</div></div>'
    stat_html += f'<div class="stat-box"><div class="stat-label">Teams</div><div class="stat-val">{n}</div></div>'
    stat_html += '</div>'

    has_times = bool(result.game_times)

    # Haupt-Spielplan
    def _main_table():
        rows = ['<table><thead><tr>',
                '<th>ST</th><th>KW</th>']
        if season_year:
            rows.append('<th>Datum</th>')
        rows += ['<th>Phase</th>',
                 '<th>DST</th>' if cfg.dst_blocks else '']
        if has_times:
            rows.append('<th>Uhrzeit</th>')
        rows += ['<th>Heimteam</th><th>Gastteam</th>']
        if is_tt:
            rows.append('<th>Ausrichter</th>')
        rows.append('</tr></thead><tbody>')

        prev_rnd = 0
        for d in cfg.days:
            rnd      = min(cfg.n_rounds, (d - 1) // round_len + 1)
            phase    = _ph.get(rnd, f'Runde {rnd}')
            day_times = result.game_times.get(d, [])
            if rnd != prev_rnd:
                ncols = (5 + bool(season_year) + bool(cfg.dst_blocks)
                         + bool(is_tt) + bool(has_times))
                rows.append(f'<tr class="phase-sep"><td colspan="{ncols}">{_esc(phase)}</td></tr>')
                prev_rnd = rnd

            is_dst   = d in dst_days
            day_type = '<span class="dst-tag">DST</span>' if is_dst else ''

            for game_n, (ht, at) in enumerate(result.schedule.get(d, [])):
                hi       = t_idx.get(ht, -1)
                ai       = t_idx.get(at, -1)
                hc       = _tc(hi) if hi >= 0 else '#eee'
                ac       = _tc(ai) if ai >= 0 else '#eee'
                host_lbl = _esc(result.hosts.get(d, '')) if is_tt else ''
                row_cls  = ' class="dst-row"' if is_dst else ''
                rows.append(f'<tr{row_cls}>')
                if game_n == 0:
                    ng = len(result.schedule.get(d, []))
                    rows.append(f'<td rowspan="{ng}" style="text-align:center;font-weight:bold">{d}</td>')
                    rows.append(f'<td rowspan="{ng}" style="text-align:center;color:#666">{_kw_label(d)}</td>')
                    if season_year:
                        rows.append(f'<td rowspan="{ng}" style="text-align:center;color:#666">{_date_str(d)}</td>')
                    rows.append(f'<td rowspan="{ng}" style="color:#666">{_esc(phase)}</td>')
                    if cfg.dst_blocks:
                        rows.append(f'<td rowspan="{ng}" style="text-align:center">{day_type}</td>')
                if has_times:
                    t_str = day_times[game_n] if game_n < len(day_times) else ''
                    rows.append(f'<td style="text-align:center;font-weight:bold;color:#1F3864">'
                                 f'{_esc(t_str)}</td>')
                rows.append(
                    f'<td><span class="team-name" style="background:{hc}">{_esc(ht)}</span></td>'
                    f'<td><span class="team-name" style="background:{ac}">{_esc(at)}</span></td>'
                )
                if is_tt:
                    rows.append(f'<td style="text-align:center;color:#666">{host_lbl}</td>')
                rows.append('</tr>')
        rows.append('</tbody></table>')
        return ''.join(rows)

    # Team-Einzelansichten
    def _team_tables():
        parts = []
        for ti, t in enumerate(teams):
            tc = _tc(ti)
            parts.append(
                f'<div class="team-section">'
                f'<h3><span class="team-name" style="background:{tc}">{_esc(t)}</span>'
                f'  &nbsp; {result.travels[ti] if ti < len(result.travels) else 0:,} km &nbsp; '
                f'Wechselquote: {result.sw_rates[ti] if ti < len(result.sw_rates) else 0:.0f}%</h3>'
                '<table><thead><tr>'
                + ('<th>ST</th><th>KW</th><th>Phase</th><th>Uhrzeit</th><th>Heimrecht</th><th>Gegner</th><th>km</th>'
                   if has_times else
                   '<th>ST</th><th>KW</th><th>Phase</th><th>Heimrecht</th><th>Gegner</th><th>km</th>')
                + '</tr></thead><tbody>'
            )
            for d in cfg.days:
                rnd   = min(cfg.n_rounds, (d - 1) // round_len + 1)
                phase = _ph.get(rnd, f'Runde {rnd}')
                is_dst = d in dst_days
                row_cls = ' class="dst-row"' if is_dst else ''
                found      = False
                day_times  = result.game_times.get(d, [])
                for g_idx, (ht, at) in enumerate(result.schedule.get(d, [])):
                    if ht != t and at != t:
                        continue
                    found   = True
                    is_home = (ht == t)
                    opp     = at if is_home else ht
                    oi      = t_idx.get(opp, -1)
                    km_val  = int(cfg.dist[ti, oi]) if not is_home and 0 <= oi < n else 0
                    hr_tag  = '<span class="heim-tag">Heim</span>' if is_home else '<span class="ausw-tag">Ausw.</span>'
                    km_str  = str(km_val) if km_val else '—'
                    occ     = _tc(oi) if oi >= 0 else '#eee'
                    t_cell  = (f'<td style="text-align:center;font-weight:bold;color:#1F3864">'
                               f'{_esc(day_times[g_idx])}</td>'
                               if has_times and g_idx < len(day_times)
                               else ('<td></td>' if has_times else ''))
                    parts.append(
                        f'<tr{row_cls}>'
                        f'<td style="text-align:center">{d}</td>'
                        f'<td style="text-align:center;color:#666">{_kw_label(d)}</td>'
                        f'<td style="color:#666">{_esc(phase)}</td>'
                        + t_cell +
                        f'<td style="text-align:center">{hr_tag}</td>'
                        f'<td><span class="team-name" style="background:{occ}">{_esc(opp)}</span></td>'
                        f'<td style="text-align:center">{km_str}</td>'
                        f'</tr>'
                    )
                ncols_sf = 6 + bool(has_times)
                if not found:
                    parts.append(f'<tr{row_cls}><td style="text-align:center">{d}</td>'
                                 f'<td colspan="{ncols_sf}" style="color:#aaa;text-align:center">spielfrei</td></tr>')
            parts.append('</tbody></table></div>')
        return ''.join(parts)

    import datetime as _dt2
    gen_date = _dt2.date.today().strftime('%d.%m.%Y')
    title    = _esc(cfg.name)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spielplan – {title}</title>
<style>{css}</style>
</head>
<body>
<div class="print-btn"><button onclick="window.print()">&#128438; Drucken / Als PDF speichern</button></div>
<h1>Spielplan &#8211; {title}</h1>
<p class="meta">Erstellt am {gen_date} &#8226; {n} Teams &#8226; {cfg.n_matchdays} Spieltage</p>
{stat_html}
<h2>Alle Spiele</h2>
{_main_table()}
<h2>Spielplan je Team</h2>
{_team_tables()}
</body>
</html>"""
