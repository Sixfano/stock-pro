"""High-level leader feedback matrix for sector/theme context."""
from __future__ import annotations

from dataclasses import dataclass
from factors.evidence import EvidenceItem


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


@dataclass(frozen=True)
class LeaderObservation:
    name: str
    height: int
    pct_chg: float
    auction_gap: float | None = None
    final_sealed: bool = False
    limit_down: bool = False
    above_vwap_ratio: float | None = None
    is_sector_core: bool = True


def leader_stock_feedback(obs: LeaderObservation) -> float:
    """Score today's feedback from a previously high-position/core stock."""
    score = 50.0
    score += min(max(obs.pct_chg, -10.0), 10.0) * 3.0

    if obs.final_sealed:
        score += 20.0
    if obs.limit_down or obs.pct_chg <= -9.0:
        score -= 30.0

    if obs.auction_gap is not None:
        score += max(-12.0, min(12.0, obs.auction_gap * 2.0))

    if obs.above_vwap_ratio is not None:
        score += (max(0.0, min(1.0, obs.above_vwap_ratio)) - 0.5) * 20.0

    if obs.is_sector_core:
        score += 4.0

    return round(_clamp(score), 2)


def sector_high_level_feedback(
    observations: list[LeaderObservation],
) -> EvidenceItem:
    if not observations:
        return EvidenceItem(
            50.0, "高标反馈", "缺少板块高标反馈样本", available=False
        )

    weighted_sum = 0.0
    total_weight = 0.0
    worst_core = 100.0

    for obs in observations:
        weight = max(1.0, float(obs.height))
        if obs.is_sector_core:
            weight *= 1.35
        value = leader_stock_feedback(obs)
        weighted_sum += value * weight
        total_weight += weight
        if obs.is_sector_core:
            worst_core = min(worst_core, value)

    score = weighted_sum / total_weight if total_weight else 50.0

    # A collapsing core leader has asymmetric negative influence on lower relays.
    if worst_core < 25:
        score -= 15
    elif worst_core < 40:
        score -= 8

    score = round(_clamp(score), 2)
    ranked = sorted(
        ((o.name, leader_stock_feedback(o), o.height) for o in observations),
        key=lambda x: x[1],
        reverse=True,
    )
    brief = "；".join(f"{n}({h}板):{s:.0f}" for n, s, h in ranked[:4])

    if score >= 70:
        detail = f"高位核心反馈正向，利于低位/中位梯队延续；{brief}"
    elif score <= 38:
        detail = f"高位核心负反馈明显，降低同题材接力容错；{brief}"
    else:
        detail = f"高标反馈分化，优先选择主动性与换手更好的个股；{brief}"

    return EvidenceItem(score, "高标反馈", detail)
