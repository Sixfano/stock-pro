"""AKShare provider.

The provider stays strategy-agnostic. New methods expose evidence used by the
daily limit-up report. They do not change the four base relay-strategy weights.
"""
import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None


class AKShareProvider:
    def _require(self):
        if ak is None:
            raise RuntimeError("Install AKShare first: pip install akshare")

    def stock_daily(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        self._require()
        return ak.stock_zh_a_hist(
            symbol=symbol, period="daily",
            start_date=start_date, end_date=end_date, adjust=""
        )

    def limit_up_pool(self, date: str) -> pd.DataFrame:
        self._require()
        return ak.stock_zt_pool_em(date=date)

    def limit_up_pool_previous(self, date: str) -> pd.DataFrame:
        self._require()
        return ak.stock_zt_pool_previous_em(date=date)

    def strong_pool(self, date: str) -> pd.DataFrame:
        self._require()
        return ak.stock_zt_pool_strong_em(date=date)

    def broken_board_pool(self, date: str) -> pd.DataFrame:
        self._require()
        return ak.stock_zt_pool_zbgc_em(date=date)

    def limit_down_pool(self, date: str) -> pd.DataFrame:
        self._require()
        return ak.stock_zt_pool_dtgc_em(date=date)

    def individual_fund_flow(self, stock: str, market: str) -> pd.DataFrame:
        self._require()
        return ak.stock_individual_fund_flow(stock=stock, market=market)

    def market_fund_flow(self, period: str = "即时") -> pd.DataFrame:
        self._require()
        return ak.stock_fund_flow_individual(symbol=period)

    def sector_fund_flow(
        self, indicator: str = "今日", sector_type: str = "概念资金流"
    ) -> pd.DataFrame:
        self._require()
        return ak.stock_sector_fund_flow_rank(
            indicator=indicator, sector_type=sector_type
        )

    def dragon_tiger(self, start_date: str, end_date: str) -> pd.DataFrame:
        self._require()
        return ak.stock_lhb_detail_em(
            start_date=start_date, end_date=end_date
        )

    def cyq(self, symbol: str, adjust: str = "") -> pd.DataFrame:
        """Eastmoney CYQ: recent profit ratio/cost bands/concentration."""
        self._require()
        return ak.stock_cyq_em(symbol=symbol, adjust=adjust)

    def concept_constituents(self, symbol: str) -> pd.DataFrame:
        self._require()
        return ak.stock_board_concept_cons_em(symbol=symbol)

    def concept_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "",
    ) -> pd.DataFrame:
        self._require()
        return ak.stock_board_concept_hist_em(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

    def industry_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "日k",
        adjust: str = "",
    ) -> pd.DataFrame:
        self._require()
        return ak.stock_board_industry_hist_em(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            period=period,
            adjust=adjust,
        )


def market_for_code(code: str) -> str:
    code = str(code).zfill(6)
    if code.startswith(("4", "8", "92")):
        return "bj"
    if code.startswith(("5", "6", "9")):
        return "sh"
    return "sz"
