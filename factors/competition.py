"""Same-height carding/competition evidence.

This does not replace a stage score. It compares candidates already admitted
to the same relay stage and helps avoid holding multiple equivalent names from
the same theme.
"""
from __future__ import annotations

from dataclasses import dataclass
from factors.evidence import EvidenceItem


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


@dataclass(frozen=True)
class SameHeightCandidate:
    name: str
    height: int
    sector: str | None
    auction_score: float | None = None
    turnover_quality: float | None = None
    limitup_quality: float | None = None
    sector_strength: float | None = None
    leader_identity: float | None = None
    tradability: float | None = None


def same_height_raw_score(c: SameHeightCandidate) -> float:
    parts = [
        (c.auction_score, 0.24),
        (c.turnover_quality, 0.18),
        (c.limitup_quality, 0.18),
        (c.sector_strength, 0.16),
        (c.leader_identity, 0.14),
        (c.tradability, 0.10),
    ]
    present = [(v, w) for v, w in parts if v is not None]
    if not present:
        return 50.0
    denom = sum(w for _, w in present)
    return round(
        sum(_clamp(v) * w for v, w in present) / denom, 2
    )


def same_height_competition(
    target: SameHeightCandidate,
    peers: list[SameHeightCandidate],
) -> EvidenceItem:
    group = [p for p in peers if p.height == target.height]
    if not group:
        return EvidenceItem(
            50.0, "同身位卡位", "缺少同身位对手", available=False
        )

    if all(p.name != target.name for p in group):
        group.append(target)

    ranked = sorted(group, key=same_height_raw_score, reverse=True)
    target_pos = next(i for i, p in enumerate(ranked) if p.name == target.name)
    n = len(ranked)
    percentile = 100.0 if n == 1 else 100.0 * (n - 1 - target_pos) / (n - 1)

    same_sector = [
        p for p in ranked
        if p.name != target.name
        and p.sector
        and target.sector
        and p.sector == target.sector
    ]
    strongest_same_sector = (
        max((same_height_raw_score(p) for p in same_sector), default=None)
    )
    raw = same_height_raw_score(target)

    if strongest_same_sector is not None and raw < strongest_same_sector:
        card_score = percentile * 0.65 + raw * 0.35 - 10.0
        duplicate_note = "同板块存在更强同身位，默认只保留更主动的一只"
    else:
        card_score = percentile * 0.65 + raw * 0.35
        duplicate_note = "同板块未发现更强同身位压制"

    card_score = round(_clamp(card_score), 2)
    top = "、".join(
        f"{p.name}:{same_height_raw_score(p):.0f}" for p in ranked[:3]
    )

    if card_score >= 72:
        detail = f"同身位竞争占优；{duplicate_note}；前列={top}"
    elif card_score <= 38:
        detail = f"同身位卡位偏弱；{duplicate_note}；前列={top}"
    else:
        detail = f"同身位竞争中性；{duplicate_note}；前列={top}"
    return EvidenceItem(card_score, "同身位卡位", detail)
