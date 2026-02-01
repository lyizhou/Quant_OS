"""涨停板数据收集服务

从Tushare获取每日涨停股票数据，并计算连板数
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from app.common.logging import logger
from app.common.time import get_last_market_day
from app.data.db import get_db
from app.data.repositories.sector_repo import SectorRepository
from app.drivers.cn_market_driver.driver import CNMarketDriver


@dataclass
class LimitUpStock:
    """涨停股票数据"""

    symbol: str
    stock_name: str
    trade_date: date
    close_price: float
    change_pct: float
    board_count: int  # 连板数
    is_limit_up: bool
    limit_up_time: str | None = None
    open_count: int = 0
    turnover_rate: float | None = None
    volume: int | None = None
    amount: float | None = None
    volume_ratio: float | None = None
    net_money_flow: float | None = None
    main_net_inflow: float | None = None
    limit_up_reason: str | None = None


class LimitUpDataService:
    """涨停板数据收集服务"""

    def __init__(self, tushare_token: str):
        """初始化服务

        Args:
            tushare_token: Tushare API token
        """
        self.market_driver = CNMarketDriver(tushare_token)
        self.sector_repo = SectorRepository()
        self.db = get_db()
        self.pro = self.market_driver.pro

    def fetch_limit_up_stocks(self, trade_date: date | None = None) -> list[LimitUpStock]:
        """获取指定日期的涨停股票

        Args:
            trade_date: 交易日期，None表示最近交易日

        Returns:
            涨停股票列表
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN").date()

        logger.info(f"Fetching limit-up stocks for {trade_date}")

        try:
            date_str = trade_date.strftime("%Y%m%d")

            # 方法1: 尝试使用新接口 limit_list_d (需要5000+积分)
            try:
                df = self.pro.limit_list_d(
                    trade_date=date_str,
                    limit_type='U',  # U=涨停
                    fields='ts_code,name,close,pct_chg,amount,turnover_ratio,fd_amount,first_time,last_time,open_times,up_stat,limit_times'
                )

                if df is not None and not df.empty:
                    logger.info(f"Found {len(df)} limit-up stocks using limit_list_d API")
                    return self._parse_limit_list_d_data(df, trade_date)
                else:
                    logger.warning("limit_list_d returned empty data, trying fallback method")
            except Exception as e:
                logger.warning(f"limit_list_d API failed: {e}, trying fallback method")

            # 方法2: 降级方案 - 使用daily接口筛选涨停股票
            logger.info("Using fallback method: filtering from daily data")
            df = self.pro.daily(trade_date=date_str)

            if df is None or df.empty:
                logger.warning(f"No daily data found for {trade_date}")
                return []

            # 筛选涨停股票 (涨跌幅 >= 9.9%)
            # 注意：主板/中小板/创业板涨停为10%，科创板/创业板注册制为20%，ST股票为5%
            limit_up_df = df[df['pct_chg'] >= 9.9].copy()

            if limit_up_df.empty:
                logger.warning(f"No limit-up stocks found for {trade_date}")
                return []

            logger.info(f"Found {len(limit_up_df)} limit-up stocks on {trade_date} (filtered from daily data)")

            # 转换为LimitUpStock对象（降级方案）
            limit_up_stocks = []

            for _, row in limit_up_df.iterrows():
                ts_code = row['ts_code']
                symbol = ts_code.split('.')[0]

                # 计算连板数
                board_count = self._calculate_board_count(symbol, trade_date)

                # 从daily数据创建LimitUpStock（字段较少）
                stock = LimitUpStock(
                    symbol=symbol,
                    stock_name=None,  # daily接口没有name字段，需要后续补充
                    trade_date=trade_date,
                    close_price=float(row['close']) if pd.notna(row['close']) else 0.0,
                    change_pct=float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0,
                    board_count=board_count,
                    is_limit_up=True,
                    limit_up_time=None,  # daily接口没有涨停时间
                    open_count=0,
                    turnover_rate=float(row['turnover_rate']) if pd.notna(row.get('turnover_rate')) else None,
                    volume=int(row['vol']) if pd.notna(row.get('vol')) else None,
                    amount=float(row['amount']) if pd.notna(row['amount']) else None,
                    volume_ratio=None,  # daily接口没有量比
                    net_money_flow=None,
                    main_net_inflow=None,
                    limit_up_reason=None
                )

                limit_up_stocks.append(stock)

            # 补充股票名称
            self._fill_stock_names(limit_up_stocks)

            return limit_up_stocks

        except Exception as e:
            logger.error(f"Failed to fetch limit-up stocks: {e}", exc_info=True)
            return []

    def _parse_limit_list_d_data(self, df: pd.DataFrame, trade_date: date) -> list[LimitUpStock]:
        """解析limit_list_d接口返回的数据

        Args:
            df: Tushare返回的DataFrame
            trade_date: 交易日期

        Returns:
            涨停股票列表
        """
        limit_up_stocks = []

        for _, row in df.iterrows():
            ts_code = row['ts_code']
            symbol = ts_code.split('.')[0]

            # 计算连板数
            board_count = self._calculate_board_count(symbol, trade_date)

            stock = LimitUpStock(
                symbol=symbol,
                stock_name=row['name'],
                trade_date=trade_date,
                close_price=float(row['close']) if pd.notna(row['close']) else 0.0,
                change_pct=float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0,
                board_count=board_count,
                is_limit_up=True,
                limit_up_time=row.get('first_time'),
                open_count=int(row['open_times']) if pd.notna(row.get('open_times')) else 0,
                turnover_rate=float(row['turnover_ratio']) if pd.notna(row.get('turnover_ratio')) else None,
                volume=None,
                amount=float(row['amount']) if pd.notna(row['amount']) else None,
                volume_ratio=None,
                net_money_flow=None,
                main_net_inflow=float(row['fd_amount']) if pd.notna(row.get('fd_amount')) else None,
                limit_up_reason=None
            )

            limit_up_stocks.append(stock)

        return limit_up_stocks

    def _fill_stock_names(self, stocks: list[LimitUpStock]):
        """补充股票名称（从stock_basic接口获取）

        Args:
            stocks: 涨停股票列表
        """
        try:
            # 获取所有A股基本信息
            stock_basic = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')

            if stock_basic is None or stock_basic.empty:
                logger.warning("Failed to fetch stock basic info")
                return

            # 创建代码到名称的映射
            name_map = {}
            for _, row in stock_basic.iterrows():
                symbol = row['ts_code'].split('.')[0]
                name_map[symbol] = row['name']

            # 补充名称
            for stock in stocks:
                if stock.stock_name is None:
                    stock.stock_name = name_map.get(stock.symbol, stock.symbol)

        except Exception as e:
            logger.warning(f"Failed to fill stock names: {e}")
            # 如果失败，使用股票代码作为名称
            for stock in stocks:
                if stock.stock_name is None:
                    stock.stock_name = stock.symbol

    def _calculate_board_count(self, symbol: str, current_date: date) -> int:
        """计算连板数

        Args:
            symbol: 股票代码
            current_date: 当前日期

        Returns:
            连板数（1=首板，2=二板...）
        """
        try:
            conn = self.db.get_connection()

            # 查询前一个交易日是否涨停
            result = conn.execute(
                """
                SELECT board_count
                FROM limit_up_stocks
                WHERE symbol = ?
                  AND trade_date < ?
                  AND is_limit_up = TRUE
                ORDER BY trade_date DESC
                LIMIT 1
                """,
                [symbol, current_date]
            ).fetchone()

            if result:
                # 检查是否连续涨停（前一个交易日）
                prev_board_count = result[0]
                prev_date_result = conn.execute(
                    """
                    SELECT trade_date
                    FROM limit_up_stocks
                    WHERE symbol = ?
                      AND trade_date < ?
                    ORDER BY trade_date DESC
                    LIMIT 1
                    """,
                    [symbol, current_date]
                ).fetchone()

                if prev_date_result:
                    prev_date = prev_date_result[0]
                    if isinstance(prev_date, str):
                        prev_date = datetime.strptime(prev_date, "%Y-%m-%d").date()

                    # 检查是否是连续交易日（简化版，不考虑节假日）
                    days_diff = (current_date - prev_date).days
                    if days_diff <= 3:  # 允许周末间隔
                        return prev_board_count + 1

            # 首板
            return 1

        except Exception as e:
            logger.error(f"Failed to calculate board count for {symbol}: {e}")
            return 1

    def save_limit_up_stocks(self, stocks: list[LimitUpStock]) -> int:
        """保存涨停股票数据到数据库

        Args:
            stocks: 涨停股票列表

        Returns:
            保存的记录数
        """
        if not stocks:
            return 0

        try:
            conn = self.db.get_connection()
            saved_count = 0

            for stock in stocks:
                try:
                    # 检查是否已存在
                    existing = conn.execute(
                        """
                        SELECT id FROM limit_up_stocks
                        WHERE symbol = ? AND trade_date = ?
                        """,
                        [stock.symbol, stock.trade_date]
                    ).fetchone()

                    if existing:
                        # 更新
                        conn.execute(
                            """
                            UPDATE limit_up_stocks
                            SET stock_name = ?,
                                close_price = ?,
                                change_pct = ?,
                                board_count = ?,
                                is_limit_up = ?,
                                limit_up_time = ?,
                                open_count = ?,
                                turnover_rate = ?,
                                volume = ?,
                                amount = ?,
                                volume_ratio = ?,
                                net_money_flow = ?,
                                main_net_inflow = ?,
                                limit_up_reason = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE symbol = ? AND trade_date = ?
                            """,
                            [
                                stock.stock_name,
                                stock.close_price,
                                stock.change_pct,
                                stock.board_count,
                                stock.is_limit_up,
                                stock.limit_up_time,
                                stock.open_count,
                                stock.turnover_rate,
                                stock.volume,
                                stock.amount,
                                stock.volume_ratio,
                                stock.net_money_flow,
                                stock.main_net_inflow,
                                stock.limit_up_reason,
                                stock.symbol,
                                stock.trade_date
                            ]
                        )
                    else:
                        # 插入
                        conn.execute(
                            """
                            INSERT INTO limit_up_stocks (
                                id, symbol, stock_name, trade_date, close_price, change_pct,
                                board_count, is_limit_up, limit_up_time, open_count,
                                turnover_rate, volume, amount, volume_ratio,
                                net_money_flow, main_net_inflow, limit_up_reason
                            ) VALUES (
                                nextval('limit_up_stocks_id_seq'), ?, ?, ?, ?, ?,
                                ?, ?, ?, ?,
                                ?, ?, ?, ?,
                                ?, ?, ?
                            )
                            """,
                            [
                                stock.symbol,
                                stock.stock_name,
                                stock.trade_date,
                                stock.close_price,
                                stock.change_pct,
                                stock.board_count,
                                stock.is_limit_up,
                                stock.limit_up_time,
                                stock.open_count,
                                stock.turnover_rate,
                                stock.volume,
                                stock.amount,
                                stock.volume_ratio,
                                stock.net_money_flow,
                                stock.main_net_inflow,
                                stock.limit_up_reason
                            ]
                        )

                    saved_count += 1

                except Exception as e:
                    logger.error(f"Failed to save limit-up stock {stock.symbol}: {e}")
                    continue

            logger.info(f"Saved {saved_count} limit-up stocks")
            return saved_count

        except Exception as e:
            logger.error(f"Failed to save limit-up stocks: {e}", exc_info=True)
            return 0

    def map_limit_up_to_sectors(self, trade_date: date | None = None) -> int:
        """将涨停股票映射到板块

        Args:
            trade_date: 交易日期

        Returns:
            映射的记录数
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN").date()

        try:
            conn = self.db.get_connection()

            # 获取当天的涨停股票
            limit_up_stocks = conn.execute(
                """
                SELECT id, symbol, stock_name
                FROM limit_up_stocks
                WHERE trade_date = ?
                """,
                [trade_date]
            ).fetchall()

            if not limit_up_stocks:
                logger.warning(f"No limit-up stocks found for {trade_date}")
                return 0

            mapped_count = 0

            for limit_up_id, symbol, stock_name in limit_up_stocks:
                # 查询股票所属板块
                sectors = self.sector_repo.get_sectors_by_stock(symbol)

                if not sectors:
                    logger.debug(f"No sectors found for {symbol} {stock_name}")
                    continue

                # 保存映射关系
                for sector in sectors:
                    try:
                        # 检查是否已存在
                        existing = conn.execute(
                            """
                            SELECT id FROM limit_up_sector_mapping
                            WHERE limit_up_id = ? AND sector_id = ?
                            """,
                            [limit_up_id, sector['sector_id']]
                        ).fetchone()

                        if not existing:
                            conn.execute(
                                """
                                INSERT INTO limit_up_sector_mapping (
                                    id, limit_up_id, sector_id, symbol, trade_date, sector_name
                                ) VALUES (
                                    nextval('limit_up_sector_mapping_id_seq'), ?, ?, ?, ?, ?
                                )
                                """,
                                [
                                    limit_up_id,
                                    sector['sector_id'],
                                    symbol,
                                    trade_date,
                                    sector['sector_name']
                                ]
                            )
                            mapped_count += 1

                    except Exception as e:
                        logger.error(f"Failed to map {symbol} to sector {sector['sector_name']}: {e}")
                        continue

            logger.info(f"Mapped {mapped_count} limit-up stocks to sectors")
            return mapped_count

        except Exception as e:
            logger.error(f"Failed to map limit-up stocks to sectors: {e}", exc_info=True)
            return 0

    def collect_daily_limit_up_data(self, trade_date: date | None = None) -> dict[str, Any]:
        """收集每日涨停数据（完整流程）

        Args:
            trade_date: 交易日期

        Returns:
            统计信息
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN").date()

        logger.info(f"Collecting limit-up data for {trade_date}")

        # 1. 获取涨停股票
        limit_up_stocks = self.fetch_limit_up_stocks(trade_date)

        if not limit_up_stocks:
            logger.warning(f"No limit-up stocks found for {trade_date}")
            return {
                "trade_date": trade_date,
                "total_count": 0,
                "saved_count": 0,
                "mapped_count": 0
            }

        # 2. 保存到数据库
        saved_count = self.save_limit_up_stocks(limit_up_stocks)

        # 3. 映射到板块
        mapped_count = self.map_limit_up_to_sectors(trade_date)

        stats = {
            "trade_date": trade_date,
            "total_count": len(limit_up_stocks),
            "saved_count": saved_count,
            "mapped_count": mapped_count,
            "board_distribution": self._get_board_distribution(limit_up_stocks)
        }

        logger.info(f"Limit-up data collection completed: {stats}")
        return stats

    def _get_board_distribution(self, stocks: list[LimitUpStock]) -> dict[str, int]:
        """获取连板分布

        Args:
            stocks: 涨停股票列表

        Returns:
            连板分布统计
        """
        distribution = {
            "first_board": 0,
            "second_board": 0,
            "third_board": 0,
            "four_plus_board": 0
        }

        for stock in stocks:
            if stock.board_count == 1:
                distribution["first_board"] += 1
            elif stock.board_count == 2:
                distribution["second_board"] += 1
            elif stock.board_count == 3:
                distribution["third_board"] += 1
            else:
                distribution["four_plus_board"] += 1

        return distribution
