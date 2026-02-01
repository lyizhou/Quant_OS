"""Stock Daily Data Cache Service - 个股每日数据缓存服务."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.common.logging import logger
from app.common.time import format_date, get_last_market_day
from app.data.db import get_db
from app.drivers.cn_market_driver.driver import CNMarketDriver


class StockDataCacheService:
    """个股每日数据缓存服务."""

    def __init__(self, tushare_token: str = None):
        """初始化缓存服务.

        Args:
            tushare_token: Tushare API token
        """
        self.db = get_db()
        self.market_driver = CNMarketDriver(tushare_token)

    def save_stock_data(self, stock_data, trade_date: datetime) -> None:
        """保存单个股票的行情数据到缓存.

        Args:
            stock_data: CNStockData对象
            trade_date: 交易日期
        """
        conn = self.db.get_connection()

        # 检查是否已存在
        existing = conn.execute(
            """
            SELECT id FROM stock_daily_data
            WHERE symbol = ? AND trade_date = ?
            """,
            [stock_data.symbol, trade_date.date()],
        ).fetchone()

        if existing:
            # 更新现有记录
            conn.execute(
                """
                UPDATE stock_daily_data
                SET stock_name = ?,
                    open = ?, high = ?, low = ?, close = ?, pre_close = ?,
                    change_amount = ?, change_pct = ?,
                    volume = ?, amount = ?,
                    turnover_rate = ?, volume_ratio = ?,
                    net_money_flow = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [
                    stock_data.name,
                    float(stock_data.open),
                    float(stock_data.high),
                    float(stock_data.low),
                    float(stock_data.close),
                    float(stock_data.prev_close) if stock_data.prev_close else None,
                    float(stock_data.close - stock_data.prev_close)
                    if stock_data.prev_close
                    else None,
                    float(stock_data.change_pct) if stock_data.change_pct else None,
                    stock_data.volume,
                    float(stock_data.amount),
                    float(stock_data.turnover_rate) if stock_data.turnover_rate else None,
                    float(stock_data.volume_ratio) if stock_data.volume_ratio else None,
                    float(stock_data.net_money_flow) if stock_data.net_money_flow else None,
                    existing[0],
                ],
            )
        else:
            # 插入新记录
            conn.execute(
                """
                INSERT INTO stock_daily_data (
                    symbol, stock_name, trade_date,
                    open, high, low, close, pre_close,
                    change_amount, change_pct,
                    volume, amount,
                    turnover_rate, volume_ratio,
                    net_money_flow
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    stock_data.symbol,
                    stock_data.name,
                    trade_date.date(),
                    float(stock_data.open),
                    float(stock_data.high),
                    float(stock_data.low),
                    float(stock_data.close),
                    float(stock_data.prev_close) if stock_data.prev_close else None,
                    float(stock_data.close - stock_data.prev_close)
                    if stock_data.prev_close
                    else None,
                    float(stock_data.change_pct) if stock_data.change_pct else None,
                    stock_data.volume,
                    float(stock_data.amount),
                    float(stock_data.turnover_rate) if stock_data.turnover_rate else None,
                    float(stock_data.volume_ratio) if stock_data.volume_ratio else None,
                    float(stock_data.net_money_flow) if stock_data.net_money_flow else None,
                ],
            )

    def batch_save_stock_data(self, stock_data_list: list, trade_date: datetime) -> dict:
        """批量保存股票行情数据.

        Args:
            stock_data_list: CNStockData对象列表
            trade_date: 交易日期

        Returns:
            保存结果统计
        """
        success_count = 0
        error_count = 0
        errors = []

        for stock_data in stock_data_list:
            try:
                self.save_stock_data(stock_data, trade_date)
                success_count += 1
            except Exception as e:
                error_count += 1
                error_msg = f"{stock_data.symbol}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Failed to save stock data for {stock_data.symbol}: {e}")

        return {
            "total": len(stock_data_list),
            "success": success_count,
            "error": error_count,
            "errors": errors,
        }

    def get_cached_stock_data(self, symbol: str, trade_date: datetime = None) -> dict | None:
        """从缓存获取股票数据.

        Args:
            symbol: 股票代码
            trade_date: 交易日期（默认为最近交易日）

        Returns:
            股票数据字典，不存在返回None
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN")

        conn = self.db.get_connection()
        result = conn.execute(
            """
            SELECT symbol, stock_name, trade_date,
                   open, high, low, close, pre_close,
                   change_amount, change_pct,
                   volume, amount,
                   turnover_rate, volume_ratio,
                   net_money_flow
            FROM stock_daily_data
            WHERE symbol = ? AND trade_date = ?
            """,
            [symbol, trade_date.date()],
        ).fetchone()

        if not result:
            return None

        return {
            "symbol": result[0],
            "stock_name": result[1],
            "trade_date": result[2],
            "open": result[3],
            "high": result[4],
            "low": result[5],
            "close": result[6],
            "pre_close": result[7],
            "change_amount": result[8],
            "change_pct": result[9],
            "volume": result[10],
            "amount": result[11],
            "turnover_rate": result[12],
            "volume_ratio": result[13],
            "net_money_flow": result[14],
        }

    def get_or_fetch_stock_data(self, symbol: str, trade_date: datetime = None) -> dict | None:
        """获取股票数据，优先从缓存读取，缓存不存在则从API获取.

        Args:
            symbol: 股票代码
            trade_date: 交易日期（默认为最近交易日）

        Returns:
            股票数据字典
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN")

        # 先尝试从缓存获取
        cached_data = self.get_cached_stock_data(symbol, trade_date)
        if cached_data:
            logger.debug(f"Cache hit for {symbol} on {format_date(trade_date)}")
            return cached_data

        # 缓存不存在，从API获取
        logger.debug(f"Cache miss for {symbol}, fetching from API...")
        try:
            stock_data_list = self.market_driver.fetch_stock_data([symbol], trade_date)
            if stock_data_list:
                stock_data = stock_data_list[0]
                # 保存到缓存
                self.save_stock_data(stock_data, trade_date)
                # 返回数据
                return self.get_cached_stock_data(symbol, trade_date)
        except Exception as e:
            logger.error(f"Failed to fetch stock data for {symbol}: {e}")

        return None

    def batch_get_or_fetch_stock_data(
        self, symbols: list[str], trade_date: datetime = None
    ) -> dict[str, dict]:
        """批量获取股票数据，优先从缓存读取.

        Args:
            symbols: 股票代码列表
            trade_date: 交易日期（默认为最近交易日）

        Returns:
            股票代码到数据的映射字典
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN")

        result = {}
        missing_symbols = []

        # 先从缓存批量读取
        conn = self.db.get_connection()
        placeholders = ",".join(["?"] * len(symbols))
        cached_results = conn.execute(
            f"""
            SELECT symbol, stock_name, trade_date,
                   open, high, low, close, pre_close,
                   change_amount, change_pct,
                   volume, amount,
                   turnover_rate, volume_ratio,
                   net_money_flow
            FROM stock_daily_data
            WHERE symbol IN ({placeholders}) AND trade_date = ?
            """,
            symbols + [trade_date.date()],
        ).fetchall()

        # 构建结果字典
        for row in cached_results:
            result[row[0]] = {
                "symbol": row[0],
                "stock_name": row[1],
                "trade_date": row[2],
                "open": row[3],
                "high": row[4],
                "low": row[5],
                "close": row[6],
                "pre_close": row[7],
                "change_amount": row[8],
                "change_pct": row[9],
                "volume": row[10],
                "amount": row[11],
                "turnover_rate": row[12],
                "volume_ratio": row[13],
                "net_money_flow": row[14],
            }

        # 找出缓存中不存在的股票
        missing_symbols = [s for s in symbols if s not in result]

        if missing_symbols:
            logger.info(
                f"Cache miss for {len(missing_symbols)} stocks, fetching from API..."
            )
            try:
                # 从API批量获取
                stock_data_list = self.market_driver.fetch_stock_data(
                    missing_symbols, trade_date
                )

                # 保存到缓存并添加到结果
                for stock_data in stock_data_list:
                    self.save_stock_data(stock_data, trade_date)
                    cached = self.get_cached_stock_data(stock_data.symbol, trade_date)
                    if cached:
                        result[stock_data.symbol] = cached

            except Exception as e:
                logger.error(f"Failed to fetch missing stock data: {e}")

        logger.info(
            f"Batch get stock data: {len(result)}/{len(symbols)} stocks retrieved"
        )
        return result

    def clean_old_cache(self, days_to_keep: int = 90) -> int:
        """清理旧的缓存数据.

        Args:
            days_to_keep: 保留最近多少天的数据（默认90天）

        Returns:
            删除的记录数
        """
        conn = self.db.get_connection()
        result = conn.execute(
            """
            DELETE FROM stock_daily_data
            WHERE trade_date < date('now', '-' || ? || ' days')
            """,
            [days_to_keep],
        )

        deleted_count = result.rowcount
        logger.info(f"Cleaned {deleted_count} old cache records (kept last {days_to_keep} days)")
        return deleted_count

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息.

        Returns:
            缓存统计字典
        """
        conn = self.db.get_connection()

        # 总记录数
        total_records = conn.execute(
            "SELECT COUNT(*) FROM stock_daily_data"
        ).fetchone()[0]

        # 不同股票数
        unique_stocks = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM stock_daily_data"
        ).fetchone()[0]

        # 不同日期数
        unique_dates = conn.execute(
            "SELECT COUNT(DISTINCT trade_date) FROM stock_daily_data"
        ).fetchone()[0]

        # 最早和最新日期
        date_range = conn.execute(
            """
            SELECT MIN(trade_date), MAX(trade_date)
            FROM stock_daily_data
            """
        ).fetchone()

        # 今日缓存数
        today_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM stock_daily_data
            WHERE trade_date = date('now')
            """
        ).fetchone()[0]

        return {
            "total_records": total_records,
            "unique_stocks": unique_stocks,
            "unique_dates": unique_dates,
            "earliest_date": date_range[0],
            "latest_date": date_range[1],
            "today_count": today_count,
        }
