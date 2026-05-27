"""Karten-Visualisierung der Reiserouten (A1, v1.9.0).

Baut eine Folium-Karte mit:
  - Marker pro Team-Standort (Liga-spezifische Farbe)
  - Polylinien zwischen Heim- und Gastteam fuer jedes Spiel
  - Liga-LayerGroups (umschaltbar)
  - Tooltip: Spieltag, Heim, Gast, km

Verwendung:
    from spielplan_multi.map_output import build_route_map
    m = build_route_map(results, geocodes)
    # m ist ein folium.Map, in Streamlit via st_folium(m, ...) anzeigbar
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional, Tuple

import folium

from .league_types import LeagueResult
from .config import get_team_color


def _esc(s: str) -> str:
    """HTML-escape fuer Tooltip-Strings (B7-L5)."""
    return _html.escape(str(s), quote=True)


# Deutschland-geografisches Zentrum (etwa Niederdorla, Thueringen)
_DE_CENTER = (51.16, 10.45)


def _hex_to_color(hex_color: str) -> str:
    """Hex-Code (ohne #) zu folium-kompatiblem '#RRGGBB'."""
    h = hex_color.lstrip('#')
    return f'#{h}'


def build_route_map(
    results: Dict[str, Optional[LeagueResult]],
    geocodes: Dict[str, Optional[Tuple[float, float]]],
    *,
    dist_matrices: Optional[Dict[str, object]] = None,
    zoom_start: int = 6,
) -> folium.Map:
    """Erstellt eine Folium-Karte mit allen Reiserouten.

    Args:
        results:      {lid: LeagueResult|None}
        geocodes:     {adresse: (lat, lon)|None}
        dist_matrices: Optional {lid: np.ndarray} – fuer km-Anzeige im Tooltip
        zoom_start:   Initialer Zoom-Level (6 = Deutschland)

    Returns:
        folium.Map mit LayerControl, Markern und Polylinien
    """
    m = folium.Map(location=_DE_CENTER, zoom_start=zoom_start,
                   tiles='OpenStreetMap', control_scale=True)

    # Sammle alle gueltigen Koordinaten fuer Auto-Center
    all_coords: List[Tuple[float, float]] = []

    valid_results = [(lid, res) for lid, res in results.items()
                     if res is not None and res.cfg and res.schedule]

    if not valid_results:
        # Leere Karte ist ok
        return m

    for lid, res in valid_results:
        cfg = res.cfg
        liga_group = folium.FeatureGroup(name=f'Liga {lid}', show=True)

        # Mapping: team_name -> (lat, lon) ueber locations
        team_coords: Dict[str, Optional[Tuple[float, float]]] = {}
        for ti, team in enumerate(cfg.teams):
            loc = cfg.locations[ti] if ti < len(cfg.locations) else team
            coord = geocodes.get(loc)
            team_coords[team] = coord
            if coord:
                all_coords.append(coord)

        # Marker pro Team-Standort
        for ti, team in enumerate(cfg.teams):
            coord = team_coords.get(team)
            if not coord:
                continue
            color = _hex_to_color(get_team_color(ti))
            folium.CircleMarker(
                location=coord,
                radius=8,
                color='#333',
                weight=1.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                tooltip=f'<b>{_esc(team)}</b><br>{_esc(cfg.locations[ti])}<br>Liga {_esc(lid)}',
            ).add_to(liga_group)

        # Distanz-Matrix fuer km-Anzeige
        dist = None
        if dist_matrices and lid in dist_matrices:
            dist = dist_matrices[lid]
        elif cfg.dist is not None:
            dist = cfg.dist
        t_idx = {t: i for i, t in enumerate(cfg.teams)}

        # Eindeutige Paare zaehlen (gleiche Paarung erscheint mehrfach
        # bei n_rounds >= 2 -> Linie wird einmal mit allen Daten gezeichnet)
        edge_data: Dict[Tuple[str, str], List[Tuple[int, str, str]]] = {}
        for day, games in res.schedule.items():
            for ht, at in games:
                # Sortiere die beiden Teams, sodass (A,B) und (B,A) zusammen sind
                pair = tuple(sorted([ht, at]))
                edge_data.setdefault(pair, []).append((day, ht, at))

        # Polylinien pro Paarung
        for (ta, tb), occurrences in edge_data.items():
            ca = team_coords.get(ta)
            cb = team_coords.get(tb)
            if not ca or not cb:
                continue

            # km zwischen den Standorten
            km_str = ''
            if dist is not None:
                try:
                    ia, ib = t_idx[ta], t_idx[tb]
                    km = int(dist[ia, ib])
                    km_str = f'<br>{km} km'
                except (KeyError, IndexError, ValueError):
                    pass

            # Tooltip: alle Begegnungen dieser Paarung (B7-L5: HTML-escaped)
            tooltip_lines = [f'<b>{_esc(ta)} ↔ {_esc(tb)}</b>{km_str}']
            for day, ht, at in sorted(occurrences):
                tooltip_lines.append(f'ST {day}: {_esc(ht)} (H) – {_esc(at)}')
            tooltip = '<br>'.join(tooltip_lines)

            # Liniendicke = Anzahl Begegnungen
            weight = 2 + min(3, len(occurrences) - 1)

            folium.PolyLine(
                locations=[ca, cb],
                color='#555',
                weight=weight,
                opacity=0.55,
                tooltip=tooltip,
            ).add_to(liga_group)

        liga_group.add_to(m)

    # LayerControl (umschaltbar wenn mehrere Ligen)
    if len(valid_results) > 1:
        folium.LayerControl(collapsed=False).add_to(m)

    # Auto-Fit auf alle Koordinaten
    if all_coords:
        lat_min = min(c[0] for c in all_coords)
        lat_max = max(c[0] for c in all_coords)
        lon_min = min(c[1] for c in all_coords)
        lon_max = max(c[1] for c in all_coords)
        m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]],
                     padding=(20, 20))

    return m
