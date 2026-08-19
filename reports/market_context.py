"""Market-context report builders for daily relay screening."""
from __future__ import annotations

from dataclasses import dataclass
from factors.leader_feedback import (
    LeaderObservation,
    sector_high_level_feedback,
)
from factors.theme_reflow import theme_reflow_evidence


@dataclass
class ThemeContext:
    name: str
    prior_heat: float
    divergence_depth: float
    sector_flow_score: float
    ladder_completeness: float
    breadth_recovery: float
    leaders: list[LeaderObservation]
    auction_core_strength: float | None = None


def build_theme_context(theme: ThemeContext) -> dict:
    leader_item = sector_high_level_feedback(theme.leaders)
    reflow_item = theme_reflow_evidence(
        prior_heat=theme.prior_heat,
        divergence_depth=theme.divergence_depth,
        sector_flow_score=theme.sector_flow_score,
        leader_feedback_score=leader_item.score,
        ladder_completeness=theme.ladder_completeness,
        breadth_recovery=theme.breadth_recovery,
        auction_core_strength=theme.auction_core_strength,
    )
    return {
        "theme": theme.name,
        "leader_feedback": leader_item,
        "reflow": reflow_item,
    }
