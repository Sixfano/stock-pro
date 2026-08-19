from factors.cyq import CYQSnapshot, cyq_structure_evidence
from factors.leader_feedback import (
    LeaderObservation,
    leader_stock_feedback,
    sector_high_level_feedback,
)
from factors.competition import (
    SameHeightCandidate,
    same_height_competition,
)
from factors.theme_reflow import theme_reflow_evidence


def test_cyq_rewards_healthy_cost_structure():
    healthy = cyq_structure_evidence(CYQSnapshot(
        close=12.0,
        winner_ratio=0.82,
        avg_cost=10.8,
        cost90_low=9.9,
        cost90_high=11.6,
        concentration90=0.18,
        cost70_low=10.2,
        cost70_high=11.3,
        concentration70=0.10,
    ))
    stretched = cyq_structure_evidence(CYQSnapshot(
        close=16.0,
        winner_ratio=0.995,
        avg_cost=10.0,
        cost90_low=8.8,
        cost90_high=10.5,
        concentration90=0.40,
        cost70_low=9.2,
        cost70_high=10.2,
        concentration70=0.35,
    ))
    assert healthy.score > stretched.score


def test_collapsing_core_leader_penalizes_sector():
    good = LeaderObservation(
        name="A", height=5, pct_chg=6, final_sealed=False,
        auction_gap=3, above_vwap_ratio=0.8, is_sector_core=True,
    )
    bad = LeaderObservation(
        name="B", height=4, pct_chg=-10, final_sealed=False,
        auction_gap=-5, above_vwap_ratio=0.1, is_sector_core=True,
        limit_down=True,
    )
    mixed = sector_high_level_feedback([good, bad])
    only_good = sector_high_level_feedback([good])
    assert only_good.score > mixed.score


def test_same_height_prefers_stronger_same_sector_name():
    a = SameHeightCandidate(
        name="A", height=2, sector="医药", auction_score=90,
        turnover_quality=85, limitup_quality=90,
        sector_strength=80, leader_identity=85, tradability=80,
    )
    b = SameHeightCandidate(
        name="B", height=2, sector="医药", auction_score=55,
        turnover_quality=65, limitup_quality=70,
        sector_strength=80, leader_identity=55, tradability=70,
    )
    ea = same_height_competition(a, [a, b])
    eb = same_height_competition(b, [a, b])
    assert ea.score > eb.score


def test_theme_reflow_requires_identity_and_divergence():
    strong = theme_reflow_evidence(
        prior_heat=85,
        divergence_depth=65,
        sector_flow_score=80,
        leader_feedback_score=75,
        ladder_completeness=80,
        breadth_recovery=78,
        auction_core_strength=82,
    )
    fake = theme_reflow_evidence(
        prior_heat=25,
        divergence_depth=15,
        sector_flow_score=80,
        leader_feedback_score=75,
        ladder_completeness=80,
        breadth_recovery=78,
        auction_core_strength=82,
    )
    assert strong.score > fake.score
