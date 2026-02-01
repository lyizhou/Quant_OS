"""每日资金流向桑基图定时任务."""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from app.common.config import get_config
from app.common.logging import logger
from app.common.time import format_date, get_last_market_day
from app.services.sankey_chart_service import SankeyChartService


class DailyMoneyFlowJob:
    """每日资金流向桑基图定时任务."""

    def __init__(self, bot: Bot, chat_id: str):
        """初始化定时任务.

        Args:
            bot: Telegram Bot实例
            chat_id: 目标聊天ID
        """
        self.bot = bot
        self.chat_id = chat_id
        self.sankey_service = SankeyChartService()
        self.scheduler = AsyncIOScheduler()
        logger.info("DailyMoneyFlowJob initialized")

    async def send_daily_money_flow(self):
        """发送每日资金流向桑基图."""
        try:
            logger.info("Starting daily money flow sankey chart generation")

            # 获取最后一个交易日
            last_market_day = get_last_market_day(market="CN")
            date_str = format_date(last_market_day)

            # 发送开始消息
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"📊 正在生成 {date_str} 的资金流向桑基图...",
            )

            # 生成简单桑基图
            logger.info("Generating simple sankey chart")
            simple_path = self.sankey_service.generate_money_flow_sankey(
                date=last_market_day, top_n=10
            )

            # 发送简单桑基图
            with open(simple_path, "rb") as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=f"📊 A股市场资金流向桑基图\n日期: {date_str}\n\n"
                    f"图表展示了当日资金在各板块间的流动情况\n"
                    f"🟢 绿色表示资金流入\n"
                    f"🔴 红色表示资金流出",
                )

            logger.info("Simple sankey chart sent successfully")

            # 生成详细桑基图
            logger.info("Generating detailed sankey chart")
            detailed_path = self.sankey_service.generate_detailed_sankey(
                date=last_market_day, top_n=8
            )

            # 发送详细桑基图
            with open(detailed_path, "rb") as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=f"📊 A股市场资金流向详细桑基图\n日期: {date_str}\n\n"
                    f"图表展示了不同资金类型的流向:\n"
                    f"🟠 超大单资金 (机构)\n"
                    f"🟢 大单资金 (大户)\n"
                    f"🔴 中单资金 (中户)\n"
                    f"🟣 小单资金 (散户)",
                )

            logger.info("Detailed sankey chart sent successfully")

            # 发送完成消息
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"✅ {date_str} 资金流向桑基图已生成完成！",
            )

            logger.info("Daily money flow sankey chart job completed successfully")

        except Exception as e:
            logger.error(f"Failed to send daily money flow sankey chart: {e}", exc_info=True)
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"❌ 生成资金流向桑基图失败: {str(e)}\n\n"
                    f"可能原因:\n"
                    f"1. Tushare API权限不足\n"
                    f"2. 网络连接问题\n"
                    f"3. 数据暂时不可用\n\n"
                    f"请稍后使用 /moneyflow 命令手动重试",
                )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")

    def start(self):
        """启动定时任务.

        默认配置:
        - 每个交易日 17:30 (收盘后) 自动发送
        - 时区: Asia/Shanghai
        """
        # 每个交易日 17:30 发送
        self.scheduler.add_job(
            self.send_daily_money_flow,
            trigger="cron",
            hour=17,
            minute=30,
            timezone="Asia/Shanghai",
            id="daily_money_flow",
            name="每日资金流向桑基图",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Daily money flow job scheduled: every trading day at 17:30 (Asia/Shanghai)")

    def stop(self):
        """停止定时任务."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Daily money flow job stopped")

    async def run_now(self):
        """立即执行一次任务（用于测试或手动触发）."""
        logger.info("Running daily money flow job manually")
        await self.send_daily_money_flow()


# 便捷函数
def create_daily_money_flow_job(bot: Bot, chat_id: str | None = None) -> DailyMoneyFlowJob:
    """创建每日资金流向定时任务.

    Args:
        bot: Telegram Bot实例
        chat_id: 目标聊天ID (default: from config)

    Returns:
        DailyMoneyFlowJob实例
    """
    if chat_id is None:
        chat_id = get_config().telegram.chat_id

    return DailyMoneyFlowJob(bot=bot, chat_id=chat_id)


if __name__ == "__main__":
    # Test the job
    import asyncio

    from app.common.logging import setup_logging

    setup_logging(level="INFO")

    async def test_job():
        """测试定时任务."""
        from telegram import Bot

        config = get_config()
        bot = Bot(token=config.telegram.bot_token)

        job = create_daily_money_flow_job(bot=bot, chat_id=config.telegram.chat_id)

        # 立即执行一次
        await job.run_now()

    asyncio.run(test_job())
