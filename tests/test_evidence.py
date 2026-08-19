from factors.evidence import (
    build_evidence_bundle,
    chip_proxy_evidence,
    dragon_tiger_evidence,
    money_flow_evidence,
    sector_flow_evidence,
)


def test_shadow_score_does_not_require_all_items():
    bundle = build_evidence_bundle({
        "money_flow": money_flow_evidence(
            main_net_pct=6,
            super_large_net_pct=3,
            net_amount_ratio=0.02,
        ),
        "sector_flow": sector_flow_evidence(
            sector_main_net_pct=4,
            sector_rank_percentile=0.85,
        ),
    })
    assert 50 < bundle.shadow_score <= 100


def test_negative_money_flow_is_evidence_not_hard_zero():
    item = money_flow_evidence(
        main_net_pct=-12,
        super_large_net_pct=-8,
        net_amount_ratio=-0.05,
    )
    assert item.available
    assert 0 <= item.score <= 100
    assert item.score != 0


def test_turnover_prefers_exchange_not_extreme_turnover():
    healthy = chip_proxy_evidence(
        turnover=10,
        amount_vs_5d=1.8,
        upper_shadow_pct=0.5,
        close_location=0.9,
    )
    extreme = chip_proxy_evidence(
        turnover=38,
        amount_vs_5d=5.0,
        upper_shadow_pct=3.0,
        close_location=0.5,
    )
    assert healthy.score > extreme.score


def test_dragon_tiger_can_be_unavailable():
    item = dragon_tiger_evidence(
        net_buy_ratio=None,
        turnover=None,
        reason=None,
    )
    assert item.available is False
