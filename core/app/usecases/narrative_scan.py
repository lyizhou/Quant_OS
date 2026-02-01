"""Narrative Scanning UseCase - 叙事扫描用例."""


from app.common.logging import logger
from app.drivers.info_driver.driver import (
    DeepSeekAnalyzer,
    InfoDriver,
    TwitterInfoSource,
)
from app.kernel.narrative_core.core import Narrative, NarrativeCore


class NarrativeScanUseCase:
    """叙事扫描用例 - 从Twitter等信息源扫描市场叙事."""

    def __init__(
        self,
        rapidapi_key: str,
        deepseek_api_key: str,
        twitter_users: list[str] | None = None,
    ) -> None:
        """初始化叙事扫描用例.

        Args:
            rapidapi_key: RapidAPI密钥（Twitter数据）
            deepseek_api_key: DeepSeek API密钥
            twitter_users: 监控的Twitter用户列表（默认: elonmusk）
        """
        self.rapidapi_key = rapidapi_key
        self.deepseek_api_key = deepseek_api_key
        self.twitter_users = twitter_users or ["elonmusk"]

        # 初始化组件
        self.analyzer = DeepSeekAnalyzer(api_key=deepseek_api_key)
        self.narrative_core = NarrativeCore(analyzer=self.analyzer)

        # 初始化信息源
        self.sources = [
            TwitterInfoSource(api_key=rapidapi_key, target_user=user) for user in self.twitter_users
        ]
        self.info_driver = InfoDriver(sources=self.sources, analyzer=self.analyzer)

    def scan_narratives(self, top_n: int = 5) -> tuple[list[Narrative], str]:
        """扫描市场叙事.

        Args:
            top_n: 返回Top N叙事

        Returns:
            (叙事列表, 格式化报告) 元组
        """
        logger.info("开始叙事扫描...")

        try:
            # Step 1: 获取信息
            logger.info(f"从{len(self.sources)}个信息源获取数据...")
            info_items = self.info_driver.fetch_all(limit_per_source=10)

            if not info_items:
                logger.warning("未获取到任何信息")
                return [], "暂无信息数据"

            logger.info(f"获取到{len(info_items)}条信息")

            # Step 2: 聚类叙事
            logger.info(f"聚类为Top {top_n}叙事...")
            narratives = self.narrative_core.get_top_narratives(info_items, top_n=top_n)

            if not narratives:
                logger.warning("未生成叙事")
                return [], "叙事生成失败"

            logger.info(f"生成{len(narratives)}个叙事")

            # Step 3: 格式化报告
            report = self.narrative_core.format_narrative_report(narratives)

            logger.info("叙事扫描完成")
            return narratives, report

        except Exception as e:
            logger.error(f"叙事扫描失败: {e}")
            return [], f"扫描失败: {e}"


def generate_narrative_scan_report(
    rapidapi_key: str,
    deepseek_api_key: str,
    twitter_users: list[str] | None = None,
    top_n: int = 5,
) -> str:
    """生成叙事扫描报告（快捷函数）.

    Args:
        rapidapi_key: RapidAPI密钥
        deepseek_api_key: DeepSeek API密钥
        twitter_users: Twitter用户列表
        top_n: Top N叙事

    Returns:
        格式化的报告文本
    """
    usecase = NarrativeScanUseCase(
        rapidapi_key=rapidapi_key,
        deepseek_api_key=deepseek_api_key,
        twitter_users=twitter_users,
    )

    narratives, report = usecase.scan_narratives(top_n=top_n)
    return report
