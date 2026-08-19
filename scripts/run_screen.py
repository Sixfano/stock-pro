"""Daily limit-up evidence snapshot.

This is a research snapshot, not an auto-trading command. It enriches the
existing relay workflow with evidence and does not replace the four base scores.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from data.providers.akshare_provider import AKShareProvider, market_for_code
from factors.cyq import CYQSnapshot, cyq_structure_evidence


def _scalar(row, column, default=None):
    if row is None or column not in row:
        return default
    value = row[column]
    if pd.isna(value):
        return default
    return value


def _latest_individual_flow(provider, code: str):
    try:
        flow = provider.individual_fund_flow(code, market_for_code(code))
    except Exception:
        return {}
    if flow is None or flow.empty:
        return {}
    row = flow.iloc[-1]
    return {
        "主力净流入占比": _scalar(row, "主力净流入-净占比"),
        "超大单净流入占比": _scalar(row, "超大单净流入-净占比"),
        "大单净流入占比": _scalar(row, "大单净流入-净占比"),
    }


def _latest_cyq(provider, code: str, close: float | None):
    if close is None or close <= 0:
        return {}
    try:
        df = provider.cyq(code)
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    row = df.iloc[-1]
    snap = CYQSnapshot(
        close=float(close),
        winner_ratio=_scalar(row, "获利比例"),
        avg_cost=_scalar(row, "平均成本"),
        cost90_low=_scalar(row, "90成本-低"),
        cost90_high=_scalar(row, "90成本-高"),
        concentration90=_scalar(row, "90集中度"),
        cost70_low=_scalar(row, "70成本-低"),
        cost70_high=_scalar(row, "70成本-高"),
        concentration70=_scalar(row, "70集中度"),
    )
    evidence = cyq_structure_evidence(snap)
    return {
        "CYQ获利比例": snap.winner_ratio,
        "CYQ平均成本": snap.avg_cost,
        "CYQ90成本低": snap.cost90_low,
        "CYQ90成本高": snap.cost90_high,
        "CYQ90集中度": snap.concentration90,
        "CYQ70成本低": snap.cost70_low,
        "CYQ70成本高": snap.cost70_high,
        "CYQ70集中度": snap.concentration70,
        "CYQ影子分": evidence.score,
        "CYQ论据": evidence.detail,
    }


def build_snapshot(
    date: str,
    enrich_top: int = 80,
    cyq_top: int = 30,
) -> pd.DataFrame:
    provider = AKShareProvider()
    pool = provider.limit_up_pool(date).copy()
    if pool.empty:
        return pool

    pool["代码"] = pool["代码"].astype(str).str.zfill(6)

    try:
        strong = provider.strong_pool(date).copy()
        if not strong.empty:
            strong["代码"] = strong["代码"].astype(str).str.zfill(6)
            keep = [
                c for c in ["代码", "入选理由", "是否新高", "量比"]
                if c in strong.columns
            ]
            pool = pool.merge(
                strong[keep].drop_duplicates("代码"),
                on="代码", how="left",
            )
    except Exception:
        pass

    try:
        lhb = provider.dragon_tiger(date, date).copy()
        if not lhb.empty:
            lhb["代码"] = lhb["代码"].astype(str).str.zfill(6)
            keep = [
                c for c in [
                    "代码", "龙虎榜净买额",
                    "净买额占总成交比", "上榜原因",
                ] if c in lhb.columns
            ]
            lhb = (
                lhb[keep].sort_values("代码")
                .drop_duplicates("代码", keep="last")
            )
            pool = pool.merge(lhb, on="代码", how="left")
    except Exception:
        pass

    sort_cols = [
        c for c in ["连板数", "封板资金", "成交额"] if c in pool.columns
    ]
    ranked = (
        pool.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        if sort_cols else pool
    )

    flow_rows = {}
    for code in ranked.head(max(0, enrich_top))["代码"].tolist():
        flow_rows[code] = _latest_individual_flow(provider, code)
    flow_df = pd.DataFrame.from_dict(flow_rows, orient="index")
    if not flow_df.empty:
        flow_df.index.name = "代码"
        pool = pool.merge(flow_df.reset_index(), on="代码", how="left")

    # True CYQ evidence replaces the old lightweight proxy for top candidates.
    cyq_rows = {}
    close_col = "最新价" if "最新价" in pool.columns else None
    ranked_now = pool.set_index("代码", drop=False)
    for code in ranked.head(max(0, cyq_top))["代码"].tolist():
        close = (
            _scalar(ranked_now.loc[code], close_col)
            if close_col and code in ranked_now.index else None
        )
        cyq_rows[code] = _latest_cyq(provider, code, close)
    cyq_df = pd.DataFrame.from_dict(cyq_rows, orient="index")
    if not cyq_df.empty:
        cyq_df.index.name = "代码"
        pool = pool.merge(cyq_df.reset_index(), on="代码", how="left")

    if "连板数" in pool.columns:
        pool["接力模式"] = pool["连板数"].map(
            lambda h: (
                "一进二观察" if h == 1 else
                "二进三观察" if h == 2 else
                "三进四观察" if h == 3 else
                "高标接力观察"
            )
        )

    def rationale(row):
        parts = []
        reason = _scalar(row, "入选理由")
        if reason:
            parts.append(f"强势池:{reason}")
        main_flow = _scalar(row, "主力净流入占比")
        if main_flow is not None:
            parts.append(f"主力净流入占比:{float(main_flow):.2f}%")
        lhb_ratio = _scalar(row, "净买额占总成交比")
        if lhb_ratio is not None:
            parts.append(f"龙虎榜净买占比:{float(lhb_ratio):.2f}%")
        turnover = _scalar(row, "换手率")
        if turnover is not None:
            parts.append(f"换手:{float(turnover):.2f}%")
        boards = _scalar(row, "炸板次数")
        if boards is not None:
            parts.append(f"炸板:{int(boards)}次")
        cyq = _scalar(row, "CYQ论据")
        if cyq:
            parts.append(str(cyq))
        return "；".join(parts) if parts else "维持原连板因子判断"

    pool["新增论据"] = pool.apply(rationale, axis=1)
    return pool


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True, help="YYYYMMDD")
    p.add_argument("--enrich-top", type=int, default=80)
    p.add_argument("--cyq-top", type=int, default=30)
    p.add_argument("--output", default=None)
    args = p.parse_args()

    df = build_snapshot(args.date, args.enrich_top, args.cyq_top)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(out)
    else:
        preferred = [
            c for c in [
                "代码", "名称", "连板数", "接力模式",
                "最新价", "换手率", "封板资金",
                "首次封板时间", "最后封板时间", "炸板次数",
                "所属行业", "入选理由", "主力净流入占比",
                "净买额占总成交比", "CYQ影子分",
                "CYQ论据", "新增论据",
            ] if c in df.columns
        ]
        print(df[preferred].to_string(index=False))


if __name__ == "__main__":
    main()
