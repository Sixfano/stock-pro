"""Daily evidence narrative helpers."""
from __future__ import annotations

from factors.evidence import EvidenceBundle


def relay_evidence_narrative(
    *,
    stock_name: str,
    height: int,
    base_strategy: str,
    bundle: EvidenceBundle,
) -> str:
    """Human-readable paragraph used in daily screening output."""
    args = bundle.arguments()
    body = "；".join(args) if args else "暂无新增证据，维持原策略判断"
    return (
        f"{stock_name}（{height}板，{base_strategy}）"
        f"影子证据分 {bundle.shadow_score:.2f}。"
        f"{body}。"
        "注意：影子证据不覆盖原策略分数，只用于解释、排序复核和风险提示。"
    )
