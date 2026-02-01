"""每日市场行情总结服务

整合多个数据源生成每日市场总结报告：
- 市场指数数据（上证、深证、创业板）
- 涨停板分析数据
- 板块强度数据
- AI生成的市场分析
"""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.common.logging import logger
from app.common.time import format_date, get_last_market_day
from app.data.db import get_db
from app.services.limit_up_analysis_service import LimitUpAnalysisService


@dataclass
class IndexData:
    """指数数据"""

    name: str  # 指数名称
    code: str  # 指数代码
    close: float  # 收盘点位
    change_pct: float  # 涨跌幅
    volume: float  # 成交量（亿）
    amount: float  # 成交额（亿）


@dataclass
class MarketBreadth:
    """市场广度数据"""

    up_count: int  # 上涨家数
    down_count: int  # 下跌家数
    limit_up_count: int  # 涨停家数
    limit_down_count: int  # 跌停家数
    total_amount: float  # 总成交额（亿）


@dataclass
class DailyMarketSummary:
    """每日市场总结"""

    trade_date: date
    indices: list[IndexData]  # 主要指数
    market_breadth: MarketBreadth  # 市场广度
    limit_up_summary: Any  # 涨停板总结
    hot_sectors: list[dict[str, Any]]  # 热门板块
    market_sentiment: str  # 市场情绪
    summary_text: str  # 总结文本


class DailyMarketSummaryService:
    """每日市场总结服务"""

    def __init__(self):
        """初始化服务"""
        self.db = get_db()
        self.limit_up_service = LimitUpAnalysisService()

    def generate_daily_summary(
        self, trade_date: date | None = None, include_ai: bool = False
    ) -> DailyMarketSummary | None:
        """生成每日市场总结

        Args:
            trade_date: 交易日期（默认最后一个交易日）
            include_ai: 是否包含AI分析

        Returns:
            每日市场总结
        """
        if trade_date is None:
            trade_date = get_last_market_day(market="CN").date()

        logger.info(f"Generating daily market summary for {trade_date}")

        try:
            # 1. 获取指数数据
            indices = self._get_index_data(trade_date)

            # 2. 获取市场广度数据
            market_breadth = self._get_market_breadth(trade_date)

            # 3. 获取涨停板总结
            limit_up_summary = self.limit_up_service.analyze_daily_limit_up(trade_date)

            # 如果没有涨停板数据，记录警告但继续生成报告
            if not limit_up_summary:
                logger.warning(f"No limit-up data available for {trade_date}, continuing with other data")

            # 4. 获取热门板块
            hot_sectors = self._get_hot_sectors(trade_date)

            # 5. 计算市场情绪
            market_sentiment = self._calculate_market_sentiment(
                indices, market_breadth, limit_up_summary
            )

            # 6. 生成总结文本
            summary_text = self._generate_summary_text(
                trade_date, indices, market_breadth, limit_up_summary, hot_sectors, market_sentiment
            )

            summary = DailyMarketSummary(
                trade_date=trade_date,
                indices=indices,
                market_breadth=market_breadth,
                limit_up_summary=limit_up_summary,
                hot_sectors=hot_sectors,
                market_sentiment=market_sentiment,
                summary_text=summary_text,
            )

            logger.info(f"Daily market summary generated for {trade_date}")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate daily market summary: {e}", exc_info=True)
            return None

    def _get_index_data(self, trade_date: date) -> list[IndexData]:
        """获取主要指数数据

        Args:
            trade_date: 交易日期

        Returns:
            指数数据列表
        """
        # 主要指数代码
        index_codes = {
            "000001.SH": "上证指数",
            "399001.SZ": "深证成指",
            "399006.SZ": "创业板指",
            "000688.SH": "科创50",
        }

        indices = []

        try:
            from app.drivers.cn_market_driver.driver import CNMarketDriver
            import os

            tushare_token = os.getenv("TUSHARE_TOKEN")
            if not tushare_token:
                logger.warning("TUSHARE_TOKEN not found, skipping index data")
                return indices

            driver = CNMarketDriver(tushare_token)

            # 获取指数数据
            for code, name in index_codes.items():
                try:
                    # 使用Tushare获取指数数据
                    date_str = trade_date.strftime("%Y%m%d")
                    df = driver.pro.index_daily(ts_code=code, start_date=date_str, end_date=date_str)

                    if not df.empty:
                        row = df.iloc[0]
                        index_data = IndexData(
                            name=name,
                            code=code,
                            close=float(row["close"]),
                            change_pct=float(row["pct_chg"]),
                            volume=float(row["vol"]) / 100000000,  # 转换为亿
                            amount=float(row["amount"]) / 100000,  # 转换为亿
                        )
                        indices.append(index_data)
                        logger.info(f"Fetched index data for {name}: {index_data.close}")
                except Exception as e:
                    logger.warning(f"Failed to fetch index data for {code}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to get index data: {e}", exc_info=True)

        return indices

    def _get_market_breadth(self, trade_date: date) -> MarketBreadth:
        """获取市场广度数据

        Args:
            trade_date: 交易日期

        Returns:
            市场广度数据
        """
        conn = self.db.get_connection()

        try:
            # 从涨停板数据中获取涨停家数
            limit_up_result = conn.execute(
                """
                SELECT COUNT(*) as limit_up_count
                FROM limit_up_stocks
                WHERE trade_date = ?
                """,
                [trade_date],
            ).fetchone()

            limit_up_count = limit_up_result[0] if limit_up_result else 0

            # 从板块强度数据中获取市场广度（如果有）
            # 这里简化处理，实际可以从更详细的数据源获取
            market_breadth = MarketBreadth(
                up_count=0,  # 需要从详细数据源获取
                down_count=0,  # 需要从详细数据源获取
                limit_up_count=limit_up_count,
                limit_down_count=0,  # 需要从详细数据源获取
                total_amount=0.0,  # 需要从详细数据源获取
            )

            return market_breadth

        except Exception as e:
            logger.error(f"Failed to get market breadth: {e}", exc_info=True)
            return MarketBreadth(
                up_count=0, down_count=0, limit_up_count=0, limit_down_count=0, total_amount=0.0
            )

    def _get_hot_sectors(self, trade_date: date, top_n: int = 5) -> list[dict[str, Any]]:
        """获取热门板块

        Args:
            trade_date: 交易日期
            top_n: 返回前N个板块

        Returns:
            热门板块列表
        """
        conn = self.db.get_connection()

        try:
            # 从板块强度表获取热门板块（使用正确的表名）
            results = conn.execute(
                """
                SELECT
                    s.id,
                    s.name,
                    ss.limit_up_count,
                    ss.avg_change_pct,
                    ss.total_volume,
                    ss.strength_score
                FROM sector_strength_results ss
                JOIN sectors s ON ss.sector_id = s.id
                WHERE ss.calc_date = ?
                ORDER BY ss.strength_score DESC
                LIMIT ?
                """,
                [trade_date, top_n],
            ).fetchall()

            hot_sectors = []
            for row in results:
                sector = {
                    "id": row[0],
                    "name": row[1],
                    "limit_up_count": row[2] or 0,
                    "avg_change_pct": float(row[3]) if row[3] else 0.0,
                    "total_volume": float(row[4]) if row[4] else 0.0,
                    "strength_score": float(row[5]) if row[5] else 0.0,
                }
                hot_sectors.append(sector)

            return hot_sectors

        except Exception as e:
            logger.error(f"Failed to get hot sectors: {e}", exc_info=True)
            return []

    def _calculate_market_sentiment(
        self,
        indices: list[IndexData],
        market_breadth: MarketBreadth,
        limit_up_summary: Any,
    ) -> str:
        """计算市场情绪

        Args:
            indices: 指数数据
            market_breadth: 市场广度
            limit_up_summary: 涨停板总结

        Returns:
            市场情绪描述
        """
        # 计算指数平均涨跌幅
        if indices:
            avg_index_change = sum(idx.change_pct for idx in indices) / len(indices)
        else:
            avg_index_change = 0.0

        # 涨停板数量
        limit_up_count = market_breadth.limit_up_count

        # 综合判断市场情绪
        if avg_index_change > 1.0 and limit_up_count > 80:
            return "强势"
        elif avg_index_change > 0.5 and limit_up_count > 50:
            return "偏强"
        elif avg_index_change > -0.5 and limit_up_count > 30:
            return "中性"
        elif avg_index_change > -1.0:
            return "偏弱"
        else:
            return "弱势"

    def _generate_summary_text(
        self,
        trade_date: date,
        indices: list[IndexData],
        market_breadth: MarketBreadth,
        limit_up_summary: Any,
        hot_sectors: list[dict[str, Any]],
        market_sentiment: str,
    ) -> str:
        """生成总结文本

        Args:
            trade_date: 交易日期
            indices: 指数数据
            market_breadth: 市场广度
            limit_up_summary: 涨停板总结
            hot_sectors: 热门板块
            market_sentiment: 市场情绪

        Returns:
            总结文本
        """
        lines = [
            f"# A股市场每日总结 - {format_date(datetime.combine(trade_date, datetime.min.time()))}",
            "",
            f"**市场情绪：** {market_sentiment}",
            "",
            "## 📊 主要指数表现",
            "",
        ]

        # 指数表现
        if indices:
            lines.append("| 指数 | 收盘点位 | 涨跌幅 | 成交额（亿） |")
            lines.append("|:---|---:|---:|---:|")
            for idx in indices:
                change_emoji = "🔴" if idx.change_pct > 0 else "🟢" if idx.change_pct < 0 else "⚪"
                lines.append(
                    f"| {change_emoji} **{idx.name}** | {idx.close:.2f} | {idx.change_pct:+.2f}% | {idx.amount:.2f} |"
                )
            lines.append("")
        else:
            lines.append("*暂无指数数据*")
            lines.append("")

        # 市场广度
        lines.extend(
            [
                "## 📈 市场广度",
                "",
                f"- **涨停家数：** {market_breadth.limit_up_count}",
            ]
        )

        # 如果没有涨停板数据，添加说明
        if market_breadth.limit_up_count == 0:
            lines.append("- *注：当日暂无涨停板数据*")

        lines.append("")

        # 涨停板总结
        if limit_up_summary:
            lines.extend(
                [
                    "## 🔥 涨停板分析",
                    "",
                    f"- **总涨停数：** {limit_up_summary.total_limit_up}",
                    f"- **首板：** {limit_up_summary.first_board_count}",
                    f"- **二板：** {limit_up_summary.second_board_count}",
                    f"- **三板：** {limit_up_summary.third_board_count}",
                    f"- **四板+：** {limit_up_summary.four_plus_board_count}",
                    f"- **最高连板：** {limit_up_summary.max_board_count}板",
                    f"- **平均连板：** {limit_up_summary.avg_board_count:.2f}板",
                    "",
                ]
            )

            # 龙头股票
            if limit_up_summary.leading_stocks:
                lines.append("### 🌟 龙头股票")
                lines.append("")
                for i, stock in enumerate(limit_up_summary.leading_stocks[:5], 1):
                    lines.append(
                        f"{i}. **{stock['stock_name']}** ({stock['symbol']}) - {stock['board_count']}板"
                    )
                lines.append("")
        else:
            lines.extend(
                [
                    "## 🔥 涨停板分析",
                    "",
                    "*当日暂无涨停板数据*",
                    "",
                ]
            )

        # 热门板块
        if hot_sectors:
            lines.extend(["## 🎯 热门板块", ""])
            for i, sector in enumerate(hot_sectors, 1):
                lines.append(
                    f"{i}. **{sector['name']}** - 涨停{sector['limit_up_count']}只，"
                    f"平均涨幅{sector['avg_change_pct']:.2f}%"
                )
            lines.append("")

        # 底部说明
        lines.extend(
            [
                "---",
                "",
                f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*",
                "",
                "*注：本报告基于公开市场数据生成，仅供研究参考，不构成投资建议。*",
            ]
        )

        return "\n".join(lines)

    def save_summary_to_file(self, summary: DailyMarketSummary, output_dir: str | Path = None) -> Path:
        """保存总结到文件

        Args:
            summary: 每日市场总结
            output_dir: 输出目录

        Returns:
            文件路径
        """
        if output_dir is None:
            output_dir = Path("data/temp/reports")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"A股{summary.trade_date.strftime('%Y%m%d')}市场总结.md"
        file_path = output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(summary.summary_text)

        logger.info(f"Summary saved to {file_path}")
        return file_path


# 便捷函数
def get_daily_market_summary_service() -> DailyMarketSummaryService:
    """获取每日市场总结服务实例"""
    return DailyMarketSummaryService()
