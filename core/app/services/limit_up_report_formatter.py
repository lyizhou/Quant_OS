"""涨停板报告格式化服务

将涨停板分析结果格式化为美观的Telegram消息
"""

from datetime import date

from app.services.limit_up_analysis_service import (
    BoardStats,
    DailyLimitUpSummary,
    SectorLimitUpStats,
)


class LimitUpReportFormatter:
    """涨停板报告格式化器"""

    @staticmethod
    def format_daily_summary(summary: DailyLimitUpSummary) -> str:
        """格式化每日涨停板总结

        Args:
            summary: 每日总结

        Returns:
            格式化的文本
        """
        lines = []

        # 标题
        lines.append("📊 每日涨停板复盘")
        lines.append(f"📅 日期：{summary.trade_date.strftime('%Y-%m-%d')}")
        lines.append("")

        # 总体统计
        lines.append("=" * 40)
        lines.append("📈 总体统计")
        lines.append("=" * 40)
        lines.append(f"涨停总数：{summary.total_limit_up} 只")
        lines.append(f"首板：{summary.first_board_count} 只")
        lines.append(f"二板：{summary.second_board_count} 只")
        lines.append(f"三板：{summary.third_board_count} 只")
        lines.append(f"四板及以上：{summary.four_plus_board_count} 只")
        lines.append("")
        lines.append(f"平均连板数：{summary.avg_board_count:.2f}")
        lines.append(f"最高连板数：{summary.max_board_count}")

        # 市场情绪
        sentiment_emoji = {
            "强势": "🔥",
            "中性": "😐",
            "弱势": "❄️"
        }
        emoji = sentiment_emoji.get(summary.market_sentiment, "")
        lines.append(f"市场情绪：{emoji} {summary.market_sentiment}")
        lines.append("")

        # 连板分布
        lines.append("=" * 40)
        lines.append("📊 连板分布")
        lines.append("=" * 40)

        for board_stat in summary.board_stats:
            board_name = LimitUpReportFormatter._get_board_name(board_stat.board_count)
            lines.append(f"\n【{board_name}】 共 {board_stat.stock_count} 只")

            # 显示前5只股票
            for i, stock in enumerate(board_stat.stocks[:5], 1):
                time_str = f" ({stock['limit_up_time']})" if stock.get('limit_up_time') else ""
                lines.append(
                    f"  {i}. {stock['symbol']} {stock['name']}"
                    f" {stock['change_pct']:+.2f}%{time_str}"
                )

            if board_stat.stock_count > 5:
                lines.append(f"  ... 还有 {board_stat.stock_count - 5} 只")

        lines.append("")

        # 热门板块
        lines.append("=" * 40)
        lines.append("🔥 热门题材板块 TOP10")
        lines.append("=" * 40)

        for i, sector in enumerate(summary.hot_sectors[:10], 1):
            lines.append(
                f"\n{i}. {sector.sector_name} "
                f"(强度: {sector.strength_score:.1f})"
            )
            lines.append(
                f"   涨停数: {sector.total_count} "
                f"(首板{sector.first_board_count} "
                f"二板{sector.second_board_count} "
                f"三板{sector.third_board_count} "
                f"四板+{sector.four_plus_board_count})"
            )
            lines.append(
                f"   平均连板: {sector.avg_board_count:.2f} "
                f"最高连板: {sector.max_board_count}"
            )

            # 显示龙头股票
            if sector.leading_stocks:
                leading = sector.leading_stocks[0]
                lines.append(
                    f"   龙头: {leading['symbol']} {leading['name']} "
                    f"{leading['board_count']}板 {leading['change_pct']:+.2f}%"
                )

        lines.append("")

        # 全市场龙头
        lines.append("=" * 40)
        lines.append("👑 全市场龙头股 TOP10")
        lines.append("=" * 40)

        for i, stock in enumerate(summary.leading_stocks[:10], 1):
            board_name = LimitUpReportFormatter._get_board_name(stock['board_count'])
            time_str = f" ({stock['limit_up_time']})" if stock.get('limit_up_time') else ""
            sectors_str = f"\n   题材: {stock['sectors']}" if stock.get('sectors') else ""

            lines.append(
                f"\n{i}. {stock['symbol']} {stock['name']}"
            )
            lines.append(
                f"   {board_name} {stock['change_pct']:+.2f}%{time_str}"
            )
            if sectors_str:
                lines.append(sectors_str)

        return "\n".join(lines)

    @staticmethod
    def format_board_detail(
        board_count: int, board_stat: BoardStats, trade_date: date
    ) -> str:
        """格式化连板详情

        Args:
            board_count: 连板数
            board_stat: 连板统计
            trade_date: 交易日期

        Returns:
            格式化的文本
        """
        lines = []

        board_name = LimitUpReportFormatter._get_board_name(board_count)

        lines.append(f"📊 {board_name}详情")
        lines.append(f"📅 日期：{trade_date.strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append(f"总数：{board_stat.stock_count} 只")
        lines.append("")

        # 显示所有股票
        for i, stock in enumerate(board_stat.stocks, 1):
            time_str = f" ({stock['limit_up_time']})" if stock.get('limit_up_time') else ""
            turnover_str = f" 换手{stock['turnover_rate']:.1f}%" if stock.get('turnover_rate') else ""

            lines.append(
                f"{i}. {stock['symbol']} {stock['name']}"
            )
            lines.append(
                f"   {stock['change_pct']:+.2f}%{time_str}{turnover_str}"
            )

        return "\n".join(lines)

    @staticmethod
    def format_sector_detail(sector: SectorLimitUpStats, trade_date: date) -> str:
        """格式化板块详情

        Args:
            sector: 板块统计
            trade_date: 交易日期

        Returns:
            格式化的文本
        """
        lines = []

        lines.append(f"🔥 {sector.sector_name}")
        lines.append(f"📅 日期：{trade_date.strftime('%Y-%m-%d')}")
        lines.append("")

        # 统计信息
        lines.append("📊 统计信息")
        lines.append(f"涨停总数：{sector.total_count} 只")
        lines.append(f"  首板：{sector.first_board_count} 只")
        lines.append(f"  二板：{sector.second_board_count} 只")
        lines.append(f"  三板：{sector.third_board_count} 只")
        lines.append(f"  四板及以上：{sector.four_plus_board_count} 只")
        lines.append("")
        lines.append(f"平均连板数：{sector.avg_board_count:.2f}")
        lines.append(f"最高连板数：{sector.max_board_count}")
        lines.append(f"强度得分：{sector.strength_score:.1f}")
        lines.append("")

        # 龙头股票
        lines.append("👑 龙头股票")
        for i, stock in enumerate(sector.leading_stocks, 1):
            board_name = LimitUpReportFormatter._get_board_name(stock['board_count'])
            time_str = f" ({stock['limit_up_time']})" if stock.get('limit_up_time') else ""

            lines.append(
                f"{i}. {stock['symbol']} {stock['name']}"
            )
            lines.append(
                f"   {board_name} {stock['change_pct']:+.2f}%{time_str}"
            )

        return "\n".join(lines)

    @staticmethod
    def format_simple_summary(summary: DailyLimitUpSummary) -> str:
        """格式化简要总结（用于通知）

        Args:
            summary: 每日总结

        Returns:
            格式化的文本
        """
        lines = []

        sentiment_emoji = {
            "强势": "🔥",
            "中性": "😐",
            "弱势": "❄️"
        }
        emoji = sentiment_emoji.get(summary.market_sentiment, "")

        lines.append(f"📊 涨停板复盘 {summary.trade_date.strftime('%m-%d')}")
        lines.append("")
        lines.append(
            f"{emoji} {summary.market_sentiment} | "
            f"涨停{summary.total_limit_up}只 | "
            f"最高{summary.max_board_count}板"
        )
        lines.append("")
        lines.append(
            f"首板{summary.first_board_count} "
            f"二板{summary.second_board_count} "
            f"三板{summary.third_board_count} "
            f"四板+{summary.four_plus_board_count}"
        )
        lines.append("")

        # 热门板块TOP3
        if summary.hot_sectors:
            lines.append("🔥 热门板块:")
            for i, sector in enumerate(summary.hot_sectors[:3], 1):
                lines.append(
                    f"{i}. {sector.sector_name} ({sector.total_count}只)"
                )

        lines.append("")

        # 龙头股TOP3
        if summary.leading_stocks:
            lines.append("👑 龙头股:")
            for i, stock in enumerate(summary.leading_stocks[:3], 1):
                board_name = LimitUpReportFormatter._get_board_name(stock['board_count'])
                lines.append(
                    f"{i}. {stock['symbol']} {stock['name']} {board_name}"
                )

        return "\n".join(lines)

    @staticmethod
    def _get_board_name(board_count: int) -> str:
        """获取连板名称

        Args:
            board_count: 连板数

        Returns:
            连板名称
        """
        if board_count == 1:
            return "首板"
        elif board_count == 2:
            return "二板"
        elif board_count == 3:
            return "三板"
        elif board_count == 4:
            return "四板"
        elif board_count == 5:
            return "五板"
        else:
            return f"{board_count}板"
