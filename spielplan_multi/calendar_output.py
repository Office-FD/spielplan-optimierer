"""Interaktive Kalenderansicht der Spielpläne (A2, v1.10.0).

Erstellt Event-Listen für streamlit-calendar (FullCalendar-Wrapper).

Verwendung:
    from spielplan_multi.calendar_output import build_calendar_events
    events = build_calendar_events(results)
    # In app.py: calendar(events, options=..., key='spielplan_calendar')
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional

from .league_types import LeagueResult
from .config import get_team_color


def _parse_date(s) -> Optional[_dt.date]:
    """Parst Datumsstring 'YYYY-MM-DD' oder 'DD.MM.YYYY'. None bei Fehler."""
    if not s or str(s).strip() in ('', 'nan'):
        return None
    s = str(s).strip()
    try:
        if '-' in s:
            return _dt.date.fromisoformat(s[:10])
        parts = s.split('.')
        if len(parts) >= 3:
            return _dt.date(int(parts[2][:4]), int(parts[1]), int(parts[0]))
    except (ValueError, TypeError, IndexError):
        pass
    return None


def _hex_color(idx: int) -> str:
    return f'#{get_team_color(idx)}'


def _date_from_kw(year: int, kw: int) -> Optional[_dt.date]:
    """ISO-Wochennummer + Jahr -> Samstag der Woche (typischer Spieltag)."""
    try:
        return _dt.date.fromisocalendar(int(year), int(kw), 6)
    except (ValueError, TypeError):
        return None


def _guess_season_year(results: Dict[str, Optional[LeagueResult]]) -> int:
    """Heuristik: Saison-Startjahr aus erstem gueltigen week_start ableiten."""
    for res in results.values():
        if res is None or not res.cfg:
            continue
        for entry in (res.cfg.calendar or {}).values():
            d = _parse_date(entry.get('week_start') or entry.get('week_end') or '')
            if d:
                # Wenn KW <= 26 (1. Halbjahr): Saison startete im Vorjahr
                kw = entry.get('kw')
                if kw and int(kw) <= 26:
                    return d.year - 1
                return d.year
    return _dt.date.today().year


def build_calendar_events(
    results: Dict[str, Optional[LeagueResult]],
    *,
    include_uhrzeit: bool = True,
    season_year: Optional[int] = None,
) -> List[dict]:
    """Erstellt Event-Liste fuer streamlit-calendar (FullCalendar-Format).

    Args:
        results: {lid: LeagueResult|None}
        include_uhrzeit: Wenn True, baue start/end mit Uhrzeit aus game_times
        season_year: Saison-Startjahr fuer KW→Datum-Berechnung wenn week_start
                     fehlt. Default: aus den vorhandenen Daten geschaetzt.

    Returns:
        Liste von Events. Jedes Event:
        {
            'title': 'Heim vs Gast',
            'start': 'YYYY-MM-DD' (oder 'YYYY-MM-DDTHH:MM:SS'),
            'allDay': True/False,
            'backgroundColor': '#RRGGBB',  # Team-Farbe (Heimteam)
            'borderColor': '#333',
            'textColor': '#000',
            'extendedProps': {'liga': lid, 'st': day, 'km': ..., ...}
        }
    """
    events: List[dict] = []

    if season_year is None:
        season_year = _guess_season_year(results)

    for lid, res in results.items():
        if res is None or not res.cfg or not res.schedule:
            continue
        cfg = res.cfg
        t_idx = {t: i for i, t in enumerate(cfg.teams)}
        cal = cfg.calendar or {}
        game_times = res.game_times or {}

        for day in sorted(res.schedule.keys()):
            games = res.schedule[day]
            cal_entry = cal.get(day, {})
            date_str = (cal_entry.get('week_start') or
                        cal_entry.get('week_end') or '')
            game_date = _parse_date(date_str)

            # Fallback: aus KW + Saison-Jahr berechnen
            if game_date is None:
                kw = cal_entry.get('kw')
                if kw:
                    yr = season_year + 1 if int(kw) <= 26 else season_year
                    game_date = _date_from_kw(yr, kw)

            # Wenn weiterhin kein Datum bekannt: Event ueberspringen
            if game_date is None:
                continue

            day_times = game_times.get(day, [])

            for slot_idx, (ht, at) in enumerate(games):
                hi = t_idx.get(ht, -1)
                bg_color = _hex_color(hi) if hi >= 0 else '#CCCCCC'

                # Uhrzeit aus game_times[day][slot_idx] (Format 'HH:MM')
                uhrzeit = ''
                if include_uhrzeit and slot_idx < len(day_times):
                    uhrzeit = str(day_times[slot_idx]).strip()

                if uhrzeit and ':' in uhrzeit:
                    try:
                        hh, mm = uhrzeit.split(':')[:2]
                        start_dt = _dt.datetime.combine(
                            game_date,
                            _dt.time(int(hh), int(mm))
                        )
                        end_dt = start_dt + _dt.timedelta(hours=2)
                        event = {
                            'title': f'{ht} – {at}',
                            'start': start_dt.isoformat(),
                            'end':   end_dt.isoformat(),
                            'allDay': False,
                            'backgroundColor': bg_color,
                            'borderColor': '#333',
                            'textColor': '#000',
                            'extendedProps': {
                                'liga': lid,
                                'st': day,
                                'heim': ht,
                                'gast': at,
                            },
                        }
                    except (ValueError, IndexError):
                        event = _allday_event(game_date, ht, at,
                                              bg_color, lid, day)
                else:
                    event = _allday_event(game_date, ht, at,
                                          bg_color, lid, day)
                events.append(event)

    return events


def _allday_event(game_date: _dt.date, ht: str, at: str,
                   bg_color: str, lid: str, day: int) -> dict:
    return {
        'title': f'{ht} – {at}',
        'start': game_date.isoformat(),
        'allDay': True,
        'backgroundColor': bg_color,
        'borderColor': '#333',
        'textColor': '#000',
        'extendedProps': {
            'liga': lid,
            'st': day,
            'heim': ht,
            'gast': at,
        },
    }


def default_calendar_options() -> dict:
    """Vernuenftige Default-Optionen fuer streamlit-calendar (FullCalendar)."""
    return {
        'initialView': 'dayGridMonth',
        'editable': False,
        'selectable': False,
        'navLinks': True,
        'weekNumbers': True,
        'firstDay': 1,  # Montag
        'locale': 'de',
        'headerToolbar': {
            'left':   'prev,next today',
            'center': 'title',
            'right':  'dayGridMonth,timeGridWeek,listMonth',
        },
        'buttonText': {
            'today':   'Heute',
            'month':   'Monat',
            'week':    'Woche',
            'list':    'Liste',
        },
        'height': 700,
    }
