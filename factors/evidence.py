"""Supplemental evidence for daily A-share limit-up relay screening.

This module is deliberately NOT a fifth strategy. It enriches the argument
behind the four existing relay strategies with money-flow, Dragon-Tiger,
limit-up-reason and market-structure context.

The default output is a shadow score plus human-readable evidence. Callers
should not replace a base strategy score with it unless a later backtest
explicitly promotes a factor into the core model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _centered_pct_score(value: float | None, scale: float = 4.0) -> float:
    """Map a signed percentage-like input around 50 without hard gating."""
    if value is None:
        return 50.0
    return _clamp(50.0 + value * scale)


@dataclass
class EvidenceItem:
    score: float
    label: str
    detail: str
    available: bool = True


@dataclass
class EvidenceBundle:
    items: dict[str, EvidenceItem] = field(default_factory=dict)

    @property
    def shadow_score(self) -> float:
        """Diagnostic score only; does not modify strategy base weights."""
        weights = {
            "money_flow": 0.10,
            "sector_flow": 0.10,
            "dragon_tiger": 0.07,
            "limitup_reason": 0.07,
            "technical_structure": 0.07,
            "chip_proxy": 0.04,
            "cyq": 0.16,
            "leader_feedback": 0.14,
            "same_height_competition": 0.10,
            "theme_reflow": 0.15,
        }
        # Full CYQ supersedes the lightweight chip proxy to avoid double-counting.
        if (
            "cyq" in self.items
            and self.items["cyq"].available
            and "chip_proxy" in weights
        ):
            weights["chip_proxy"] = 0.0
        present = [
            (key, item)
            for key, item in self.items.items()
            if item.available and key in weights
        ]
        if not present:
            return 50.0
        total_weight = sum(weights[key] for key, _ in present)
        return round(
            sum(item.score * weights[key] for key, item in present) / total_weight,
            2,
        )

    def arguments(self) -> list[str]:
        return [
            f"{item.label}: {item.detail}"
            for item in self.items.values()
            if item.available
        ]


def money_flow_evidence(
    *,
    main_net_pct: float | None,
    super_large_net_pct: float | None = None,
    net_amount_ratio: float | None = None,
) -> EvidenceItem:
    """Capital-flow context; negative flow is never a hard rejection."""
    if (
        main_net_pct is None
        and super_large_net_pct is None
        and net_amount_ratio is None
    ):
        return EvidenceItem(
            50.0, "资金流", "缺少个股资金流数据", available=False
        )

    main = _centered_pct_score(main_net_pct, 3.0)
    super_large = _centered_pct_score(super_large_net_pct, 2.5)
    ratio = _centered_pct_score((net_amount_ratio or 0.0) * 100.0, 2.0)
    score = _clamp(main * 0.50 + super_large * 0.30 + ratio * 0.20)

    if score >= 68:
        detail = "主力/大单资金对涨停结构形成确认，作为正向论据"
    elif score <= 35:
        detail = "资金净流出明显，需结合高换手承接判断是否为健康分歧"
    else:
        detail = "资金流中性，不单独改变连板预期"
    return EvidenceItem(round(score, 2), "资金流", detail)


def sector_flow_evidence(
    *,
    sector_main_net_pct: float | None,
    sector_rank_percentile: float | None = None,
) -> EvidenceItem:
    if sector_main_net_pct is None and sector_rank_percentile is None:
        return EvidenceItem(
            50.0, "板块资金", "缺少板块资金流数据", available=False
        )

    pct_score = _centered_pct_score(sector_main_net_pct, 3.0)
    rank_score = (
        50.0
        if sector_rank_percentile is None
        else _clamp(sector_rank_percentile * 100.0)
    )
    score = pct_score * 0.65 + rank_score * 0.35
    if score >= 68:
        detail = "板块资金有共振，个股并非孤立涨停"
    elif score <= 35:
        detail = "板块资金偏弱，警惕个股单打独斗或兑现"
    else:
        detail = "板块资金一般，仍以梯队完整度和高标反馈为主"
    return EvidenceItem(round(score, 2), "板块资金", detail)


def dragon_tiger_evidence(
    *,
    net_buy_ratio: float | None,
    turnover: float | None = None,
    reason: str | None = None,
) -> EvidenceItem:
    if net_buy_ratio is None and turnover is None and not reason:
        return EvidenceItem(
            50.0, "龙虎榜", "当日无可用龙虎榜证据", available=False
        )

    net_score = _centered_pct_score(net_buy_ratio, 2.5)
    if turnover is None:
        turnover_score = 50.0
    elif 5 <= turnover <= 25:
        turnover_score = 80.0
    elif 2 <= turnover < 5 or 25 < turnover <= 35:
        turnover_score = 60.0
    else:
        turnover_score = 35.0

    score = net_score * 0.70 + turnover_score * 0.30
    reason_text = f"；上榜原因: {reason}" if reason else ""
    if score >= 68:
        detail = f"龙虎榜净买结构偏正，席位资金提供确认{reason_text}"
    elif score <= 35:
        detail = f"龙虎榜卖压偏大，次日接力需提高承接要求{reason_text}"
    else:
        detail = f"龙虎榜结构中性，不作为单独买卖依据{reason_text}"
    return EvidenceItem(round(score, 2), "龙虎榜", detail)


def limitup_reason_evidence(
    *,
    theme_match: bool | None,
    reason_text: str | None,
    strong_pool_reason: str | None = None,
) -> EvidenceItem:
    """Narrative consistency, not a standalone theme-selection strategy."""
    if theme_match is None and not reason_text and not strong_pool_reason:
        return EvidenceItem(
            50.0, "涨停逻辑", "缺少涨停原因/强势池入选理由", available=False
        )

    score = 50.0
    if theme_match is True:
        score += 25.0
    elif theme_match is False:
        score -= 20.0
    if strong_pool_reason:
        score += 10.0
    score = _clamp(score)

    pieces = [x for x in [reason_text, strong_pool_reason] if x]
    joined = "；".join(pieces) if pieces else "未提供文本"
    if score >= 70:
        detail = f"涨停原因与主线/板块定位一致：{joined}"
    elif score <= 40:
        detail = f"涨停逻辑与当前主线匹配度不足：{joined}"
    else:
        detail = f"涨停逻辑待板块梯队进一步确认：{joined}"
    return EvidenceItem(round(score, 2), "涨停逻辑", detail)


def technical_structure_evidence(
    *,
    close_above_vwap_ratio: float | None,
    volume_ratio: float | None,
    close_location: float | None,
    atr_pct: float | None = None,
) -> EvidenceItem:
    """Price/volume context; never a MACD-style strategy switch."""
    if (
        close_above_vwap_ratio is None
        and volume_ratio is None
        and close_location is None
    ):
        return EvidenceItem(
            50.0, "量价结构", "缺少分时/量价结构数据", available=False
        )

    vwap_score = _clamp(
        (close_above_vwap_ratio if close_above_vwap_ratio is not None else 0.5)
        * 100.0
    )

    if volume_ratio is None:
        volume_score = 50.0
    elif 1.2 <= volume_ratio <= 3.5:
        volume_score = 85.0
    elif 0.8 <= volume_ratio < 1.2 or 3.5 < volume_ratio <= 5.0:
        volume_score = 60.0
    else:
        volume_score = 35.0

    location_score = _clamp(
        (close_location if close_location is not None else 0.5) * 100.0
    )
    volatility_score = (
        60.0
        if atr_pct is None
        else _clamp(80.0 - max(0.0, atr_pct - 4.0) * 6.0)
    )
    score = (
        vwap_score * 0.35
        + volume_score * 0.30
        + location_score * 0.25
        + volatility_score * 0.10
    )

    if score >= 68:
        detail = "量价承接较健康，可强化换手接力论据"
    elif score <= 38:
        detail = "量价结构偏弱，需观察均价线承接与回封"
    else:
        detail = "量价结构中性，以涨停质量和板块地位为主"
    return EvidenceItem(round(_clamp(score), 2), "量价结构", detail)


def chip_proxy_evidence(
    *,
    turnover: float | None,
    amount_vs_5d: float | None,
    upper_shadow_pct: float | None,
    close_location: float | None,
) -> EvidenceItem:
    """Lightweight proxy until full CYQ cost distribution is available.

    Rewards sufficient exchange without blindly favoring extreme turnover.
    """
    if turnover is None and amount_vs_5d is None and upper_shadow_pct is None:
        return EvidenceItem(
            50.0,
            "筹码代理",
            "缺少筹码/CYQ数据，当前仅能使用换手代理",
            available=False,
        )

    if turnover is None:
        turnover_score = 50.0
    elif 5 <= turnover <= 15:
        turnover_score = 95.0
    elif 2 <= turnover < 5 or 15 < turnover <= 22:
        turnover_score = 75.0
    elif 22 < turnover <= 30:
        turnover_score = 50.0
    else:
        turnover_score = 30.0

    if amount_vs_5d is None:
        amount_score = 50.0
    elif 1.1 <= amount_vs_5d <= 2.8:
        amount_score = 85.0
    elif 0.8 <= amount_vs_5d < 1.1 or 2.8 < amount_vs_5d <= 4.0:
        amount_score = 60.0
    else:
        amount_score = 35.0

    shadow_penalty = _clamp(
        (upper_shadow_pct or 0.0) * 8.0, 0.0, 35.0
    )
    location_score = _clamp(
        (close_location if close_location is not None else 0.5) * 100.0
    )
    score = (
        turnover_score * 0.45
        + amount_score * 0.25
        + location_score * 0.30
        - shadow_penalty
    )
    score = _clamp(score)

    if score >= 68:
        detail = "换手与成交扩张较均衡，筹码交换充分但未明显失控"
    elif score <= 38:
        detail = "筹码代理偏差，警惕缩量一致或高换手兑现；等待CYQ进一步确认"
    else:
        detail = "筹码代理中性，不能替代真实CYQ成本分布"
    return EvidenceItem(round(score, 2), "筹码代理", detail)


def build_evidence_bundle(
    items: Mapping[str, EvidenceItem],
) -> EvidenceBundle:
    return EvidenceBundle(items=dict(items))
