"""Datenklassen fuer Liga-Konfiguration, Solver-Variablen und Ergebnisse."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np


@dataclass
class LeagueConfig:
    """Vollstaendige Konfiguration fuer eine einzelne Liga."""
    league_id:      str
    name:           str
    teams:          List[str]
    locations:      List[str]
    dist:           np.ndarray        # n x n km-Matrix
    dst_blocks:     List[Tuple[int, int]]  # [(d1,d2), ...]
    weekends:       List[List[int]]   # [[d] oder [d1,d2]]
    apply_routing:  bool
    f_num:          int               # Routing-Faktor Zaehler
    f_den:          int               # Routing-Faktor Nenner
    w_scaled:       Dict[str, float]  # gewichtete Faktoren fuer Solver
    raw_weights:    Dict[str, float]  # Rohgewichte (0-10) fuer Ausgabe
    pinned:         List[dict]        # Pflichtspiele
    blocked:        Dict[str, List[int]]  # Heimspiel-Sperrtage
    # Kalender: spieltag_nr -> {kw, week_start, week_end}
    calendar:       Dict[int, dict] = field(default_factory=dict)
    forced_home:    Dict[str, List[int]] = field(default_factory=dict)  # Heimspiel-Pflichttage
    hier_weight:    float = 1.0       # Hierarchiegewicht im kombinierten Modell
    games_per_team_per_day: int = 1   # 1 = Standard, 2+ = Turniertag (Stufe 1)
    n_rounds:       int = 2           # 1=Einfachrunde, 2=Hin-/Rueckrunde, 3=Dreifachrunde
    n_teams_per_group: int = 0        # 0 = Stufe 1 (alle Teams), >0 = Stufe 2 (Gruppen)
    n_active_per_day: int = 0         # 0 = alle Teams, >0 = Spielfrei-Modus (< n Teams)
    tt_settings:    Dict = field(default_factory=dict)  # Turniertag-Spielreihenfolge

    @property
    def n_teams(self):        return len(self.teams)

    @property
    def n_groups_per_day(self) -> int:
        K = self.n_teams_per_group
        if K <= 0:
            return 1
        n_active = self.n_active_per_day if self.n_active_per_day > 0 else len(self.teams)
        return max(1, n_active // K)

    @property
    def n_matchdays(self):
        gpd = max(1, self.games_per_team_per_day)
        n = len(self.teams)
        K = self.n_teams_per_group
        if K > 0:
            # Stufe 2 (Gruppen): allgemeine Formel, funktioniert auch mit Spielfrei
            n_active = self.n_active_per_day if self.n_active_per_day > 0 else n
            G = max(1, n_active // K)
            total_matches = self.n_rounds * n * (n - 1) // 2
            games_per_day = max(1, G * K * gpd // 2)
            return total_matches // games_per_day
        # Stufe 1 oder Standard – allgemeine Formel, funktioniert auch bei ungerader Teamzahl
        n_active = self.n_active_per_day if self.n_active_per_day > 0 else n
        games_per_day = max(1, n_active * gpd // 2)
        return self.n_rounds * n * (n - 1) // 2 // games_per_day

    @property
    def hinrunde_end(self):
        return self.n_matchdays // max(1, self.n_rounds)

    @property
    def n_games_per_day(self):
        # Bei n_active_per_day > 0 (Spielfrei-Modus) spielen weniger Teams pro Tag,
        # daher entsprechend weniger Spiele pro Tag.
        n_active = self.n_active_per_day if self.n_active_per_day > 0 else len(self.teams)
        return n_active * max(1, self.games_per_team_per_day) // 2

    @property
    def days(self):           return list(range(1, self.n_matchdays + 1))

    @property
    def n_transitions(self):  return self.n_matchdays - 1

    @property
    def dst_days(self):       return {d for blk in self.dst_blocks for d in blk}


@dataclass
class LeagueVars:
    """CP-SAT-Variablen einer Liga im gemeinsamen Modell (Phase 2)."""
    x:         Dict   # (match_idx, day) -> BoolVar
    h:         Dict   # match_idx -> BoolVar  (1 = B ist Heimteam)
    home:      Dict   # (team_idx, day) -> BoolVar
    switch:    Dict   # (team_idx, day) -> BoolVar  (day in 1..N-1)
    sw_count:  Dict   # team_idx -> IntVar
    travel:    Dict   # team_idx -> IntVar
    max_sw:    Any    # IntVar
    min_sw:    Any    # IntVar
    max_travel: Any   # IntVar
    min_travel: Any   # IntVar
    team_idx:  Dict   # team_name -> int
    matches:   List   # [{'A':..., 'B':..., 'phase':...}]
    days:      List[int]
    dst_eff_total: Any = None  # IntVar; nur gesetzt wenn dst_eff-Gewicht > 0 und DST-Blöcke vorhanden
    round_balance_penalty: Any = None  # IntVar; sum(sq_dev[ti,r]) für Heim-Balance pro Runde


@dataclass
class LeagueResult:
    """Ergebnis nach Solver-Lauf fuer eine Liga."""
    league_id:  str
    status:     int        # cp_model.OPTIMAL / FEASIBLE / etc.
    objective:  float
    schedule:   Dict[int, List[Tuple[str, str]]]  # day -> [(ht, at)]
    sw_counts:  List[int]
    sw_rates:   List[float]
    travels:    List[int]
    mins:       int
    secs:       int
    # Rohwerte fuer Phase-2-Hints
    home_vals:  Dict       # (ti, d) -> 0/1
    h_vals:     Dict       # m -> 0/1
    x_vals:     Dict       # (m, d) -> 0/1
    # Referenz auf Konfiguration (fuer Excel-Export)
    cfg:        Optional[LeagueConfig] = None
    # Gruppen-Zuweisung (nur Stufe 2): day -> [[team, ...], ...]
    groups:     Dict = field(default_factory=dict)
    # Ausrichter pro Spieltag (nur Turniertag): day -> team_name
    hosts:      Dict = field(default_factory=dict)
    # Spielzeiten: day -> [uhrzeit_str, ...] (ein Eintrag je Spiel des Tages)
    game_times: Dict = field(default_factory=dict)
    # Gap-Monitoring (B1, v1.11.0): Solver-Telemetrie
    #   gap_history: Liste (elapsed_sec, obj) bei jedem [BEST]-Callback
    #   best_bound:  finaler LP/CP-Bound nach Solver.Solve()
    #   final_gap:   (best_bound - phase2_objective) / best_bound
    #   phase2_objective (A7-M3, v1.13.0): CP-SAT-objective VOR SA-Refine.
    #     SA aktualisiert nur `objective` (km-Reduktion); fuer Gap-Berechnung
    #     muss aber der Pre-SA-Wert gegen den Phase-2-bound verglichen werden.
    gap_history:      List[Tuple[float, float]] = field(default_factory=list)
    best_bound:       Optional[float]           = None
    final_gap:        Optional[float]           = None
    phase2_objective: Optional[float]           = None
    # R7-A7-M2 (v1.14.0): seed_histories sammelt die gap_history aller Phase-1-Seeds
    # vor der Best-Auswahl. Schluessel = Seed-Int, Wert = Liste (elapsed_sec, obj).
    # Erlaubt Vergleichs-Analysen welcher Seed schneller konvergierte.
    seed_histories:   Dict[int, List[Tuple[float, float]]] = field(default_factory=dict)
