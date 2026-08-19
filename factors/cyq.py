"""Real CYQ / position-cost-distribution evidence for relay screening.

The goal is not to turn CYQ into an entry trigger.  It answers:
- Has turnover produced a healthier cost structure?
- Is overhead pressure still material?
- Is the relay sitting too far above the average cost with crowded profits?
"""
from __future__ import annotations

from dataclasses import dataclass

from factors.evidence import EvidenceItem


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def _pct(v: float | None) -> float | None:
    """Normalize a ratio that may be returned as 0-1 or 0-100."""
    if v is None:
        return None
    v = float(v)
    return v * 100.0 if abs(v) <= 1.0 else v


@dataclass(frozen=True)
class CYQSnapshot:
    close: float
    winner_ratio: float | None
    avg_cost: float | None
    cost90_low: float | None
    cost90_high: float | None
    concentration90: float | None
    cost70_low: float | None
    cost70_high: float | None
    concentration70: float | None


def cyq_structure_evidence(s: CYQSnapshot) -> EvidenceItem:
    if s.close <= 0 or (
        s.winner_ratio is None
        and s.avg_cost is None
        and s.concentration70 is None
        and s.concentration90 is None
    ):
        return EvidenceItem(
            50.0, "CYQ筹码", "缺少可用CYQ成本分布", available=False
        )

    winner = _pct(s.winner_ratio)
    c70 = _pct(s.concentration70)
    c90 = _pct(s.concentration90)

    # Profit ratio: relay wants enough profitable chips to reduce overhead,
    # but an almost fully profitable book can increase synchronized profit-taking.
    if winner is None:
        winner_score = 50.0
    elif 55 <= winner <= 90:
        winner_score = 90.0
    elif 35 <= winner < 55 or 90 < winner <= 97:
        winner_score = 72.0
    elif winner > 97:
        winner_score = 58.0
    else:
        winner_score = 40.0

    # Distance to average cost. Too far above cost is a profit-crowding warning.
    if s.avg_cost is None or s.avg_cost <= 0:
        cost_distance_score = 50.0
        cost_distance_pct = None
    else:
        cost_distance_pct = (s.close / s.avg_cost - 1.0) * 100.0
        if 3 <= cost_distance_pct <= 18:
            cost_distance_score = 92.0
        elif -2 <= cost_distance_pct < 3 or 18 < cost_distance_pct <= 28:
            cost_distance_score = 72.0
        elif 28 < cost_distance_pct <= 38:
            cost_distance_score = 48.0
        else:
            cost_distance_score = 30.0

    # Lower concentration values mean a narrower cost band. For relay trading,
    # moderate concentration is preferred over both extreme crowding and chaos.
    def concentration_score(v):
        if v is None:
            return 50.0
        if 5 <= v <= 16:
            return 88.0
        if 2 <= v < 5 or 16 < v <= 24:
            return 70.0
        if 24 < v <= 35:
            return 48.0
        return 42.0

    conc_score = (
        concentration_score(c70) * 0.60
        + concentration_score(c90) * 0.40
    )

    # Overhead pressure: being near/above the 90% high-cost boundary lowers
    # trapped-supply pressure. This is evidence, not a chase signal.
    if s.cost90_high is None or s.cost90_high <= 0:
        overhead_score = 50.0
        overhead_desc = "套牢压力未知"
    else:
        ratio = s.close / s.cost90_high
        if ratio >= 1.02:
            overhead_score = 88.0
            overhead_desc = "价格已有效越过90%高成本区，历史套牢压力较轻"
        elif ratio >= 0.97:
            overhead_score = 72.0
            overhead_desc = "接近90%高成本区上沿，仍需换手消化"
        elif ratio >= 0.90:
            overhead_score = 52.0
            overhead_desc = "上方仍存在一定成本密集区"
        else:
            overhead_score = 32.0
            overhead_desc = "上方90%成本区压力较明显"

    score = (
        winner_score * 0.28
        + cost_distance_score * 0.28
        + conc_score * 0.22
        + overhead_score * 0.22
    )
    score = round(_clamp(score), 2)

    details = [overhead_desc]
    if winner is not None:
        details.append(f"获利盘约{winner:.1f}%")
    if cost_distance_pct is not None:
        details.append(f"现价较平均成本{cost_distance_pct:+.1f}%")
    if c70 is not None:
        details.append(f"70%集中度{c70:.1f}%")
    if c90 is not None:
        details.append(f"90%集中度{c90:.1f}%")

    if score >= 72:
        prefix = "筹码结构对换手接力形成正向确认"
    elif score <= 42:
        prefix = "筹码结构存在明显兑现/套牢风险"
    else:
        prefix = "筹码结构中性，需结合分时承接与板块地位"

    return EvidenceItem(score, "CYQ筹码", prefix + "；" + "；".join(details))
