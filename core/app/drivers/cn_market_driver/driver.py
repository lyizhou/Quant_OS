"""CN Market Driver - fetch China A-share market data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import tushare as ts

from app.common.config import get_config
from app.common.errors import CNMarketDriverError
from app.common.logging import logger
from app.common.time import format_date, get_last_market_day, now


@dataclass
class CNStockData:
    """CN stock data point."""

    symbol: str  # e.g., "000001" or "000001.SZ"
    name: str  # Chinese name
    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int  # 成交量（手）
    amount: Decimal  # 成交额（元）
    change_pct: Decimal | None = None  # 涨跌幅 %
    turnover_rate: Decimal | None = None  # 换手率 %
    volume_ratio: Decimal | None = None  # 量比
    prev_close: Decimal | None = None
    net_money_flow: Decimal | None = None  # 主力净流入（万元）


@dataclass
class CNMarketSummary:
    """CN market summary."""

    date: datetime
    stocks: list[CNStockData]
    top_gainers: list[CNStockData]
    top_losers: list[CNStockData]
    high_volume: list[CNStockData]


class CNMarketDriver:
    """Driver for fetching CN A-share market data using Tushare."""

    def __init__(self, token: str | None = None):
        """Initialize CN market driver.

        Args:
            token: Tushare API token (default: from config)

        Raises:
            CNMarketDriverError: If token is missing
        """
        self.token = token or get_config().api.tushare_token
        if not self.token:
            raise CNMarketDriverError("Tushare token is required. Set TUSHARE_TOKEN in .env")

        # Initialize Tushare
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        logger.info("CNMarketDriver initialized with Tushare")

    def fetch_stock_data(
        self, symbols: list[str], date: datetime | None = None
    ) -> list[CNStockData]:
        """Fetch stock data for given symbols.

        Args:
            symbols: List of stock codes (e.g., ["000001", "600000"])
            date: Target date (default: last market day, None for realtime)

        Returns:
            List of stock data

        Raises:
            CNMarketDriverError: If fetch fails
        """
        # 如果没有指定日期，尝试获取实时行情
        if date is None:
            try:
                return self._fetch_realtime_quotes(symbols)
            except Exception as e:
                logger.warning(f"Failed to fetch realtime quotes: {e}, falling back to daily data")
                date = get_last_market_day(market="CN")

        # Try to fetch data for the requested date, with fallback to previous trading days
        max_retries = 5
        current_date = date

        for attempt in range(max_retries):
            date_str = format_date(current_date).replace("-", "")  # YYYYMMDD format

            if attempt > 0:
                logger.info(f"Retrying with previous trading day: {date_str} (attempt {attempt + 1}/{max_retries})")
            else:
                logger.info(f"Fetching CN market data for {len(symbols)} symbols on {date_str}")

            results = []
            failed_symbols = []

            for symbol in symbols:
                try:
                    # Normalize symbol (add exchange suffix if missing)
                    ts_code = self._normalize_symbol(symbol)

                    # Fetch daily data with basic factors (包含换手率)
                    try:
                        df = self.pro.daily(ts_code=ts_code, trade_date=date_str)
                    except Exception as e:
                        logger.debug(f"Failed to fetch daily data for {symbol}: {e}")
                        failed_symbols.append(symbol)
                        continue

                    try:
                        df_basic = self.pro.daily_basic(
                            ts_code=ts_code,
                            trade_date=date_str,
                            fields="ts_code,trade_date,turnover_rate,volume_ratio,amount",
                        )
                    except Exception as e:
                        logger.debug(f"Failed to fetch daily_basic for {symbol}: {e}")
                        df_basic = pd.DataFrame()  # 使用空DataFrame

                    # Fetch money flow data (主力净流入)
                    net_money_flow = None
                    try:
                        df_money_flow = self.pro.moneyflow(
                            ts_code=ts_code,
                            trade_date=date_str,
                            fields="ts_code,trade_date,buy_sell_elg_vol,xg_elg_amount",
                        )
                        if not df_money_flow.empty:
                            # 计算主力净流入 = 买入卖出精英量（手） * 当日收盘价 / 10000（万元）
                            # 或者使用 xg_elg_amount (超大单净金额，单位：元)
                            flow_row = df_money_flow.iloc[0]
                            if pd.notna(flow_row.get("xg_elg_amount")):
                                # 超大单净金额（元转万元）
                                net_money_flow = Decimal(str(flow_row["xg_elg_amount"])) / Decimal(
                                    "10000"
                                )
                            elif pd.notna(flow_row.get("buy_sell_elg_vol")):
                                # 买卖精英量净额（手转万元，需要价格信息）
                                net_money_flow = Decimal(str(flow_row["buy_sell_elg_vol"]))
                    except Exception as e:
                        logger.debug(f"Failed to fetch money flow for {symbol}: {e}")

                    if df.empty:
                        if attempt == 0:  # Only log warning on first attempt
                            logger.debug(f"No data for {symbol} on {date_str}")
                        failed_symbols.append(symbol)
                        continue

                    # Get stock basic info for name
                    try:
                        stock_info = self.pro.stock_basic(ts_code=ts_code, fields="ts_code,name,industry")
                        name = stock_info.iloc[0]["name"] if not stock_info.empty else symbol
                        industry = stock_info.iloc[0]["industry"] if not stock_info.empty else None
                    except Exception as e:
                        logger.debug(f"Failed to fetch stock_basic for {symbol}: {e}")
                        name = symbol
                        industry = None

                    row = df.iloc[0]

                    # 获取换手率和量比
                    turnover_rate = None
                    volume_ratio = None
                    if not df_basic.empty:
                        basic_row = df_basic.iloc[0]
                        turnover_rate = (
                            Decimal(str(basic_row["turnover_rate"]))
                            if pd.notna(basic_row["turnover_rate"])
                            else None
                        )
                        volume_ratio = (
                            Decimal(str(basic_row["volume_ratio"]))
                            if pd.notna(basic_row["volume_ratio"])
                            else None
                        )

                    data = CNStockData(
                        symbol=symbol,
                        name=name,
                        date=datetime.strptime(row["trade_date"], "%Y%m%d"),
                        open=Decimal(str(row["open"])),
                        high=Decimal(str(row["high"])),
                        low=Decimal(str(row["low"])),
                        close=Decimal(str(row["close"])),
                        volume=int(row["vol"] * 100),  # Convert to shares (手 -> 股)
                        amount=Decimal(str(row["amount"] * 1000)),  # Convert to yuan (千元 -> 元)
                        change_pct=Decimal(str(row["pct_chg"])) if row["pct_chg"] else None,
                        prev_close=Decimal(str(row["pre_close"])) if row["pre_close"] else None,
                        turnover_rate=turnover_rate,
                        volume_ratio=volume_ratio,
                        net_money_flow=net_money_flow,
                    )
                    results.append(data)

                except Exception as e:
                    logger.error(f"Failed to fetch {symbol}: {e}")
                    failed_symbols.append(symbol)

            # If we got results, return them
            if results:
                if failed_symbols and attempt == 0:
                    logger.warning(f"Failed to fetch {len(failed_symbols)} symbols on {date_str}: {failed_symbols[:10]}")
                logger.info(f"Successfully fetched {len(results)} symbols on {date_str}")
                return results

            # No results, try previous trading day
            logger.warning(f"No data available for any symbol on {date_str}, trying previous trading day")
            current_date = get_last_market_day(reference_date=current_date - timedelta(days=1), market="CN")

        # All retries exhausted
        raise CNMarketDriverError(f"No data fetched for any symbol after {max_retries} attempts")

    def fetch_historical_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """获取股票历史数据.

        Args:
            symbol: 股票代码 (e.g., "000001")
            days: 获取天数 (默认60天)

        Returns:
            pandas DataFrame 包含历史数据
            Columns: trade_date, open, high, low, close, vol, amount, pct_chg, pre_close

        Raises:
            CNMarketDriverError: 获取失败
        """
        ts_code = self._normalize_symbol(symbol)
        # 使用最后一个交易日作为结束日期，确保数据可用
        end_date = get_last_market_day(market="CN")
        start_date = end_date - timedelta(days=days + 30)  # 多取一些以防节假日

        logger.info(f"Fetching {days} days historical data for {symbol} (end_date: {format_date(end_date)})")

        try:
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )

            if df.empty:
                raise CNMarketDriverError(f"No historical data for {symbol}")

            # 按日期升序排列
            df = df.sort_values("trade_date").tail(days)

            logger.info(f"Fetched {len(df)} days of historical data for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            raise CNMarketDriverError(f"Failed to fetch historical data: {e}")

    def get_market_summary(
        self, symbols: list[str], date: datetime | None = None, top_n: int = 5
    ) -> CNMarketSummary:
        """Get market summary for given symbols.

        Args:
            symbols: List of stock codes to analyze
            date: Target date (default: last market day)
            top_n: Number of top movers to return

        Returns:
            Market summary

        Raises:
            CNMarketDriverError: If fetch fails
        """
        if date is None:
            date = get_last_market_day(market="CN")

        logger.info(f"Generating CN market summary for {len(symbols)} symbols")

        # Fetch all data
        stocks = self.fetch_stock_data(symbols, date)

        # Filter stocks with valid change_pct
        valid_stocks = [s for s in stocks if s.change_pct is not None]

        # Sort by different metrics
        by_change = sorted(valid_stocks, key=lambda x: x.change_pct or Decimal(0), reverse=True)
        by_volume = sorted(valid_stocks, key=lambda x: x.volume, reverse=True)

        top_gainers = by_change[:top_n]
        top_losers = by_change[-top_n:][::-1]
        high_volume = by_volume[:top_n]

        summary = CNMarketSummary(
            date=date,
            stocks=stocks,
            top_gainers=top_gainers,
            top_losers=top_losers,
            high_volume=high_volume,
        )

        logger.info(
            f"CN market summary: {len(stocks)} stocks, {len(top_gainers)} gainers, {len(top_losers)} losers"
        )
        return summary

    def format_summary(self, summary: CNMarketSummary) -> str:
        """Format market summary as readable text.

        Args:
            summary: Market summary

        Returns:
            Formatted text
        """
        lines = [
            f"📊 A股市场概览 - {format_date(summary.date)}",
            f"总计: {len(summary.stocks)} 只股票",
            "",
            "🚀 涨幅榜:",
        ]

        for i, stock in enumerate(summary.top_gainers, 1):
            lines.append(
                f"  {i}. {stock.name}({stock.symbol}): ¥{stock.close:.2f} ({stock.change_pct:+.2f}%)"
            )

        lines.extend(["", "📉 跌幅榜:"])
        for i, stock in enumerate(summary.top_losers, 1):
            lines.append(
                f"  {i}. {stock.name}({stock.symbol}): ¥{stock.close:.2f} ({stock.change_pct:+.2f}%)"
            )

        lines.extend(["", "💰 成交量榜:"])
        for i, stock in enumerate(summary.high_volume, 1):
            vol_str = f"{stock.volume / 10000:.2f}万手"
            lines.append(f"  {i}. {stock.name}({stock.symbol}): {vol_str}")

        return "\n".join(lines)

    def _fetch_realtime_quotes(self, symbols: list[str]) -> list[CNStockData]:
        """获取实时行情数据.

        Args:
            symbols: 股票代码列表

        Returns:
            实时行情数据列表

        Raises:
            CNMarketDriverError: 获取失败
        """
        logger.info(f"Fetching realtime quotes for {len(symbols)} symbols")

        results = []
        failed_symbols = []

        for symbol in symbols:
            try:
                # Normalize symbol
                ts_code = self._normalize_symbol(symbol)

                # 获取实时行情（使用最新日线数据作为实时价格）
                # Tushare免费版没有真正的实时行情接口，使用最新交易日数据
                df = self.pro.daily(
                    ts_code=ts_code,
                    start_date=(now().strftime("%Y%m%d")),
                    end_date=(now().strftime("%Y%m%d")),
                )

                # 如果今天没有数据，获取最近一个交易日
                if df.empty:
                    df = self.pro.daily(ts_code=ts_code)
                    if not df.empty:
                        df = df.head(1)  # 取最新一条

                if df.empty:
                    logger.warning(f"No realtime data for {symbol}")
                    failed_symbols.append(symbol)
                    continue

                # 获取股票基本信息
                stock_info = self.pro.stock_basic(ts_code=ts_code, fields="ts_code,name,industry")
                name = stock_info.iloc[0]["name"] if not stock_info.empty else symbol

                # 获取当日的基本因子数据
                trade_date = df.iloc[0]["trade_date"]
                df_basic = self.pro.daily_basic(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    fields="ts_code,trade_date,turnover_rate,volume_ratio",
                )

                # 获取换手率和量比
                turnover_rate = None
                volume_ratio = None
                if not df_basic.empty:
                    basic_row = df_basic.iloc[0]
                    turnover_rate = (
                        Decimal(str(basic_row["turnover_rate"]))
                        if pd.notna(basic_row["turnover_rate"])
                        else None
                    )
                    volume_ratio = (
                        Decimal(str(basic_row["volume_ratio"]))
                        if pd.notna(basic_row["volume_ratio"])
                        else None
                    )

                # 获取资金流向数据
                net_money_flow = None
                try:
                    df_money_flow = self.pro.moneyflow(
                        ts_code=ts_code,
                        trade_date=trade_date,
                        fields="ts_code,trade_date,buy_sell_elg_vol,xg_elg_amount",
                    )
                    if not df_money_flow.empty:
                        flow_row = df_money_flow.iloc[0]
                        if pd.notna(flow_row.get("xg_elg_amount")):
                            # 超大单净金额（元转万元）
                            net_money_flow = Decimal(str(flow_row["xg_elg_amount"])) / Decimal(
                                "10000"
                            )
                        elif pd.notna(flow_row.get("buy_sell_elg_vol")):
                            # 买卖精英量净额（手转万元）
                            net_money_flow = Decimal(str(flow_row["buy_sell_elg_vol"]))
                except Exception as e:
                    logger.debug(f"Failed to fetch money flow for {symbol}: {e}")

                row = df.iloc[0]
                data = CNStockData(
                    symbol=symbol,
                    name=name,
                    date=datetime.strptime(row["trade_date"], "%Y%m%d"),
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),  # 使用收盘价作为当前价
                    volume=int(row["vol"] * 100),
                    amount=Decimal(str(row["amount"] * 1000)),
                    change_pct=Decimal(str(row["pct_chg"])) if row["pct_chg"] else None,
                    prev_close=Decimal(str(row["pre_close"])) if row["pre_close"] else None,
                    turnover_rate=turnover_rate,
                    volume_ratio=volume_ratio,
                    net_money_flow=net_money_flow,
                )
                results.append(data)
                logger.debug(f"Fetched realtime quote for {symbol}: ¥{data.close}")

            except Exception as e:
                logger.error(f"Failed to fetch realtime quote for {symbol}: {e}")
                failed_symbols.append(symbol)

        if failed_symbols:
            logger.warning(f"Failed to fetch {len(failed_symbols)} symbols: {failed_symbols}")

        if not results:
            raise CNMarketDriverError("No realtime data fetched for any symbol")

        logger.info(f"Successfully fetched {len(results)} realtime quotes")
        return results

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize stock symbol to Tushare format.

        Args:
            symbol: Stock code (e.g., "000001" or "000001.SZ")

        Returns:
            Tushare format symbol (e.g., "000001.SZ")
        """
        if "." in symbol:
            return symbol

        # Infer exchange from symbol
        if symbol.startswith("6"):
            return f"{symbol}.SH"  # Shanghai
        elif symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"  # Shenzhen
        elif symbol.startswith("4") or symbol.startswith("8"):
            return f"{symbol}.BJ"  # Beijing
        else:
            # Default to Shenzhen
            return f"{symbol}.SZ"


# Convenience function
def get_cn_market_summary(symbols: list[str], date: datetime | None = None) -> CNMarketSummary:
    """Get CN market summary (convenience function).

    Args:
        symbols: List of stock codes
        date: Target date (default: last market day)

    Returns:
        Market summary
    """
    driver = CNMarketDriver()
    return driver.get_market_summary(symbols, date)


if __name__ == "__main__":
    # Test the driver
    from app.common.logging import setup_logging

    setup_logging(level="INFO")

    # Test with some sample symbols
    test_symbols = ["000001", "600000", "300750", "002230"]

    driver = CNMarketDriver()
    summary = driver.get_market_summary(test_symbols)
    print(driver.format_summary(summary))
