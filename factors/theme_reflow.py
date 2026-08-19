"""Theme reflow-likelihood evidence.

The 0-100 value is a heuristic likelihood score, NOT a calibrated statistical
probability.  It should only influence narrative and review priority until a
historical calibration study proves otherwise.
"""
from __future__ import annotations

from factors.evidence import EvidenceItem


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def theme_reflow_evidence(
    *,
    prior_heat: float,
    divergence_depth: float,
    sector_flow_score: float,
    leader_feedback_score: float,
    ladder_completeness: float,
    breadth_recovery: float,
    auction_core_strength: float | None = None,
) -> EvidenceItem:
    """Estimate whether a recently strong theme has conditions for a return.

    Inputs are all 0-100.
    - prior_heat: theme had identity before the pullback
    - divergence_depth: enough divergence/washout to create re-entry room
    - sector_flow_score: capital returning to the theme
    - leader_feedback_score: old leaders are not producing destructive feedback
    - ladder_completeness: 1/2/3/high positions still have continuity
    - breadth_recovery: members recovering together rather than one isolated name
    - auction_core_strength: optional next-day auction confirmation
    """
    inputs = {
        "prior_heat": prior_heat,
        "divergence_depth": divergence_depth,
        "sector_flow_score": sector_flow_score,
        "leader_feedback_score": leader_feedback_score,
        "ladder_completeness": ladder_completeness,
        "breadth_recovery": breadth_recovery,
    }
    if any(v is None for v in inputs.values()):
        return EvidenceItem(
            50.0, "题材回流", "题材回流关键数据不足", available=False
        )

    base = (
        _clamp(prior_heat) * 0.16
        + _clamp(divergence_depth) * 0.14
        + _clamp(sector_flow_score) * 0.20
        + _clamp(leader_feedback_score) * 0.18
        + _clamp(ladder_completeness) * 0.16
        + _clamp(breadth_recovery) * 0.16
    )

    if auction_core_strength is not None:
        base = base * 0.85 + _clamp(auction_core_strength) * 0.15

    # Reflow requires both prior identity and a real divergence. A never-hot
    # theme or one that never released disagreement should not score as "reflow".
    if prior_heat < 45:
        base -= 12
    if divergence_depth < 30:
        base -= 8
    if leader_feedback_score < 30:
        base -= 12

    score = round(_clamp(base), 2)

    if score >= 72:
        detail = "具备较强回流条件：旧主线辨识度、资金回流、梯队和高标反馈形成共振"
    elif score >= 58:
        detail = "存在修复/回流预期，但需竞价核心与板块广度进一步确认"
    elif score <= 38:
        detail = "回流条件弱，更多视为局部反抽或单票行为"
    else:
        detail = "回流倾向中性，保持观察而非提前押注"

    return EvidenceItem(
        score,
        "题材回流",
        detail + "；该分值为启发式倾向分，未经历史校准不得当作真实概率",
    )
