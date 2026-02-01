"""涨停板分析和统计服务

分析每日涨停板数据，生成统计报告
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.common.logging import logger
from app.common.time import get_last_market_day
from app.data.db import get_db


@dataclass
class BoardStats:
    """连板统计"""

    board_count: int  # 连板数
    stock_count: int  # 股票数量
    stocks: list[dict[str, Any]]  # 股票列表


@dataclass
class SectorLimitUpStats:
    """板块涨停统计"""

    sector_id: int
    sector_name: str
    total_count: int  # 总涨停数
    first_board_count: int  # 首板数
    second_board_count: int  # 二板数
    third_board_count: int  # 三板数
    four_plus_board_count: int  # 四板及以上数
    avg_board_count: float  # 平均连板数
    max_board_count: int  # 最高连板数
    strength_score: float  # 强度得分
    leading_stocks: list[dict[str, Any]]  # 龙头股票


@dataclass
class DailyLimitUpSummary:
    """每日涨停板总结"""

    trade_date: date
    total_limit_up: int
    first_board_count: int
    second_board_count: int
    third_board_count: int
    four_plus_board_count: int
    market_sentiment: str  # 强势/中性/弱势
    avg_board_count: float
    max_board_count: int
    hot_sectors: list[SectorLimitUpStats]
    leading_stocks: list[dict[str, Any]]
    board_stats: list[BoardStats]


class LimitUpAnalysisService:
    """涨停板分析服务"""

    def __init__(self):
        """初始化服务"""
        self.db = get_db()

    def analyze_daily_limit_up(self, trade_date: date | None = None) -> DailyLimitUpSummary | None:
        """分析每日涨停板数据

        Args:
            trade_date: 交易日期

        Returns:
            每日涨停板总结
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN").date()

        logger.info(f"Analyzing limit-up data for {trade_date}")

        try:
            conn = self.db.get_connection()

            # 1. 获取总体统计
            overall_stats = self._get_overall_stats(trade_date)

            if overall_stats['total_limit_up'] == 0:
                logger.warning(f"No limit-up stocks found for {trade_date}")
                return None

            # 2. 获取连板分布
            board_stats = self._get_board_stats(trade_date)

            # 3. 获取热门板块
            hot_sectors = self._get_hot_sectors(trade_date)

            # 4. 获取龙头股票
            leading_stocks = self._get_leading_stocks(trade_date)

            # 5. 计算市场情绪
            market_sentiment = self._calculate_market_sentiment(overall_stats, board_stats)

            summary = DailyLimitUpSummary(
                trade_date=trade_date,
                total_limit_up=overall_stats['total_limit_up'],
                first_board_count=overall_stats['first_board_count'],
                second_board_count=overall_stats['second_board_count'],
                third_board_count=overall_stats['third_board_count'],
                four_plus_board_count=overall_stats['four_plus_board_count'],
                market_sentiment=market_sentiment,
                avg_board_count=overall_stats['avg_board_count'],
                max_board_count=overall_stats['max_board_count'],
                hot_sectors=hot_sectors,
                leading_stocks=leading_stocks,
                board_stats=board_stats
            )

            # 6. 保存总结到数据库
            self._save_daily_summary(summary)

            logger.info(f"Limit-up analysis completed for {trade_date}")
            return summary

        except Exception as e:
            logger.error(f"Failed to analyze limit-up data: {e}", exc_info=True)
            return None

    def _get_overall_stats(self, trade_date: date) -> dict[str, Any]:
        """获取总体统计

        Args:
            trade_date: 交易日期

        Returns:
            统计数据
        """
        conn = self.db.get_connection()

        result = conn.execute(
            """
            SELECT
                COUNT(*) as total_limit_up,
                COUNT(CASE WHEN board_count = 1 THEN 1 END) as first_board_count,
                COUNT(CASE WHEN board_count = 2 THEN 1 END) as second_board_count,
                COUNT(CASE WHEN board_count = 3 THEN 1 END) as third_board_count,
                COUNT(CASE WHEN board_count >= 4 THEN 1 END) as four_plus_board_count,
                AVG(board_count) as avg_board_count,
                MAX(board_count) as max_board_count
            FROM limit_up_stocks
            WHERE trade_date = ?
            """,
            [trade_date]
        ).fetchone()

        return {
            'total_limit_up': result[0] or 0,
            'first_board_count': result[1] or 0,
            'second_board_count': result[2] or 0,
            'third_board_count': result[3] or 0,
            'four_plus_board_count': result[4] or 0,
            'avg_board_count': float(result[5]) if result[5] else 0.0,
            'max_board_count': result[6] or 0
        }

    def _get_board_stats(self, trade_date: date) -> list[BoardStats]:
        """获取连板分布统计

        Args:
            trade_date: 交易日期

        Returns:
            连板统计列表
        """
        conn = self.db.get_connection()

        # 获取每个连板数的统计
        results = conn.execute(
            """
            SELECT
                board_count,
                COUNT(*) as stock_count
            FROM limit_up_stocks
            WHERE trade_date = ?
            GROUP BY board_count
            ORDER BY board_count
            """,
            [trade_date]
        ).fetchall()

        board_stats = []

        for board_count, stock_count in results:
            # 获取该连板数的股票列表
            stocks = conn.execute(
                """
                SELECT symbol, stock_name, close_price, change_pct, turnover_rate, limit_up_time
                FROM limit_up_stocks
                WHERE trade_date = ? AND board_count = ?
                ORDER BY change_pct DESC
                LIMIT 10
                """,
                [trade_date, board_count]
            ).fetchall()

            stock_list = [
                {
                    'symbol': row[0],
                    'name': row[1],
                    'close_price': float(row[2]) if row[2] else 0.0,
                    'change_pct': float(row[3]) if row[3] else 0.0,
                    'turnover_rate': float(row[4]) if row[4] else 0.0,
                    'limit_up_time': row[5]
                }
                for row in stocks
            ]

            board_stats.append(BoardStats(
                board_count=board_count,
                stock_count=stock_count,
                stocks=stock_list
            ))

        return board_stats

    def _get_hot_sectors(self, trade_date: date, limit: int = 10) -> list[SectorLimitUpStats]:
        """获取热门板块

        Args:
            trade_date: 交易日期
            limit: 返回数量

        Returns:
            热门板块列表
        """
        conn = self.db.get_connection()

        # 使用视图查询板块统计
        results = conn.execute(
            """
            SELECT
                sector_id,
                sector_name,
                limit_up_count,
                first_board_count,
                second_board_count,
                third_board_count,
                four_plus_board_count,
                avg_board_count,
                max_board_count
            FROM v_limit_up_sector_stats
            WHERE trade_date = ?
            ORDER BY limit_up_count DESC, avg_board_count DESC
            LIMIT ?
            """,
            [trade_date, limit]
        ).fetchall()

        hot_sectors = []

        for row in results:
            sector_id = row[0]
            sector_name = row[1]

            # 计算强度得分
            strength_score = self._calculate_sector_strength(
                total_count=row[2],
                avg_board_count=float(row[7]) if row[7] else 0.0,
                max_board_count=row[8] or 0
            )

            # 获取该板块的龙头股票
            leading_stocks = self._get_sector_leading_stocks(trade_date, sector_id, limit=5)

            hot_sectors.append(SectorLimitUpStats(
                sector_id=sector_id,
                sector_name=sector_name,
                total_count=row[2] or 0,
                first_board_count=row[3] or 0,
                second_board_count=row[4] or 0,
                third_board_count=row[5] or 0,
                four_plus_board_count=row[6] or 0,
                avg_board_count=float(row[7]) if row[7] else 0.0,
                max_board_count=row[8] or 0,
                strength_score=strength_score,
                leading_stocks=leading_stocks
            ))

        return hot_sectors

    def _get_sector_leading_stocks(
        self, trade_date: date, sector_id: int, limit: int = 5
    ) -> list[dict[str, Any]]:
        """获取板块龙头股票

        Args:
            trade_date: 交易日期
            sector_id: 板块ID
            limit: 返回数量

        Returns:
            龙头股票列表
        """
        conn = self.db.get_connection()

        results = conn.execute(
            """
            SELECT
                lu.symbol,
                lu.stock_name,
                lu.board_count,
                lu.change_pct,
                lu.close_price,
                lu.turnover_rate,
                lu.limit_up_time
            FROM limit_up_stocks lu
            JOIN limit_up_sector_mapping lsm ON lu.id = lsm.limit_up_id
            WHERE lu.trade_date = ?
              AND lsm.sector_id = ?
            ORDER BY lu.board_count DESC, lu.change_pct DESC
            LIMIT ?
            """,
            [trade_date, sector_id, limit]
        ).fetchall()

        return [
            {
                'symbol': row[0],
                'name': row[1],
                'board_count': row[2],
                'change_pct': float(row[3]) if row[3] else 0.0,
                'close_price': float(row[4]) if row[4] else 0.0,
                'turnover_rate': float(row[5]) if row[5] else 0.0,
                'limit_up_time': row[6]
            }
            for row in results
        ]

    def _get_leading_stocks(self, trade_date: date, limit: int = 10) -> list[dict[str, Any]]:
        """获取全市场龙头股票

        Args:
            trade_date: 交易日期
            limit: 返回数量

        Returns:
            龙头股票列表
        """
        conn = self.db.get_connection()

        results = conn.execute(
            """
            SELECT
                lu.symbol,
                lu.stock_name,
                lu.board_count,
                lu.change_pct,
                lu.close_price,
                lu.turnover_rate,
                lu.limit_up_time,
                GROUP_CONCAT(DISTINCT lsm.sector_name, ', ') as sectors
            FROM limit_up_stocks lu
            LEFT JOIN limit_up_sector_mapping lsm ON lu.id = lsm.limit_up_id
            WHERE lu.trade_date = ?
            GROUP BY lu.id, lu.symbol, lu.stock_name, lu.board_count, lu.change_pct,
                     lu.close_price, lu.turnover_rate, lu.limit_up_time
            ORDER BY lu.board_count DESC, lu.change_pct DESC
            LIMIT ?
            """,
            [trade_date, limit]
        ).fetchall()

        return [
            {
                'symbol': row[0],
                'name': row[1],
                'board_count': row[2],
                'change_pct': float(row[3]) if row[3] else 0.0,
                'close_price': float(row[4]) if row[4] else 0.0,
                'turnover_rate': float(row[5]) if row[5] else 0.0,
                'limit_up_time': row[6],
                'sectors': row[7] or ''
            }
            for row in results
        ]

    def _calculate_sector_strength(
        self, total_count: int, avg_board_count: float, max_board_count: int
    ) -> float:
        """计算板块强度得分

        Args:
            total_count: 涨停总数
            avg_board_count: 平均连板数
            max_board_count: 最高连板数

        Returns:
            强度得分
        """
        # 强度得分 = 涨停数量 * 0.4 + 平均连板数 * 20 * 0.3 + 最高连板数 * 10 * 0.3
        score = (
            total_count * 0.4
            + avg_board_count * 20 * 0.3
            + max_board_count * 10 * 0.3
        )
        return round(score, 2)

    def _calculate_market_sentiment(
        self, overall_stats: dict[str, Any], board_stats: list[BoardStats]
    ) -> str:
        """计算市场情绪

        Args:
            overall_stats: 总体统计
            board_stats: 连板统计

        Returns:
            市场情绪：强势/中性/弱势
        """
        total = overall_stats['total_limit_up']
        avg_board = overall_stats['avg_board_count']
        max_board = overall_stats['max_board_count']

        # 强势市场：涨停数>50 且 平均连板>1.5 且 最高连板>=3
        if total > 50 and avg_board > 1.5 and max_board >= 3:
            return "强势"

        # 弱势市场：涨停数<20 或 平均连板<1.2
        if total < 20 or avg_board < 1.2:
            return "弱势"

        # 中性市场
        return "中性"

    def _save_daily_summary(self, summary: DailyLimitUpSummary) -> bool:
        """保存每日总结到数据库

        Args:
            summary: 每日总结

        Returns:
            是否成功
        """
        try:
            conn = self.db.get_connection()

            # 序列化热门板块和龙头股票
            hot_sectors_json = json.dumps(
                [
                    {
                        'sector_name': s.sector_name,
                        'count': s.total_count,
                        'strength': s.strength_score,
                        'avg_board': s.avg_board_count
                    }
                    for s in summary.hot_sectors
                ],
                ensure_ascii=False
            )

            leading_stocks_json = json.dumps(
                [
                    {
                        'symbol': s['symbol'],
                        'name': s['name'],
                        'board_count': s['board_count'],
                        'sectors': s.get('sectors', '')
                    }
                    for s in summary.leading_stocks
                ],
                ensure_ascii=False
            )

            # 检查是否已存在
            existing = conn.execute(
                """
                SELECT id FROM daily_limit_up_summary
                WHERE trade_date = ?
                """,
                [summary.trade_date]
            ).fetchone()

            if existing:
                # 更新
                conn.execute(
                    """
                    UPDATE daily_limit_up_summary
                    SET total_limit_up = ?,
                        first_board_count = ?,
                        second_board_count = ?,
                        third_board_count = ?,
                        four_plus_board_count = ?,
                        market_sentiment = ?,
                        avg_board_count = ?,
                        max_board_count = ?,
                        hot_sectors = ?,
                        leading_stocks = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE trade_date = ?
                    """,
                    [
                        summary.total_limit_up,
                        summary.first_board_count,
                        summary.second_board_count,
                        summary.third_board_count,
                        summary.four_plus_board_count,
                        summary.market_sentiment,
                        summary.avg_board_count,
                        summary.max_board_count,
                        hot_sectors_json,
                        leading_stocks_json,
                        summary.trade_date
                    ]
                )
            else:
                # 插入
                conn.execute(
                    """
                    INSERT INTO daily_limit_up_summary (
                        id, trade_date, total_limit_up, first_board_count, second_board_count,
                        third_board_count, four_plus_board_count, market_sentiment,
                        avg_board_count, max_board_count, hot_sectors, leading_stocks
                    ) VALUES (
                        nextval('daily_limit_up_summary_id_seq'), ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?
                    )
                    """,
                    [
                        summary.trade_date,
                        summary.total_limit_up,
                        summary.first_board_count,
                        summary.second_board_count,
                        summary.third_board_count,
                        summary.four_plus_board_count,
                        summary.market_sentiment,
                        summary.avg_board_count,
                        summary.max_board_count,
                        hot_sectors_json,
                        leading_stocks_json
                    ]
                )

            logger.info(f"Saved daily limit-up summary for {summary.trade_date}")
            return True

        except Exception as e:
            logger.error(f"Failed to save daily summary: {e}", exc_info=True)
            return False

    def get_daily_summary(self, trade_date: date | None = None) -> DailyLimitUpSummary | None:
        """获取每日总结

        Args:
            trade_date: 交易日期

        Returns:
            每日总结
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN").date()

        try:
            conn = self.db.get_connection()

            result = conn.execute(
                """
                SELECT
                    trade_date, total_limit_up, first_board_count, second_board_count,
                    third_board_count, four_plus_board_count, market_sentiment,
                    avg_board_count, max_board_count, hot_sectors, leading_stocks
                FROM daily_limit_up_summary
                WHERE trade_date = ?
                """,
                [trade_date]
            ).fetchone()

            if not result:
                return None

            # 解析JSON
            hot_sectors_data = json.loads(result[9]) if result[9] else []
            leading_stocks_data = json.loads(result[10]) if result[10] else []

            # 重新分析以获取完整数据
            return self.analyze_daily_limit_up(trade_date)

        except Exception as e:
            logger.error(f"Failed to get daily summary: {e}", exc_info=True)
            return None
