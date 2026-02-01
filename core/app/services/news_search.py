"""News Search Service - 使用Perplexity AI搜索新闻."""

import os
import re
from datetime import datetime

from loguru import logger
from openai import OpenAI


class NewsSearchService:
    """新闻搜索服务 - 使用Perplexity AI搜索."""

    def __init__(self, api_key: str | None = None):
        """初始化新闻搜索服务.

        Args:
            api_key: Perplexity API密钥，如果不提供则从环境变量读取
        """
        # 获取API密钥
        if api_key is None:
            api_key = os.getenv("PERPLEXITY_API_KEY")

        if not api_key:
            logger.error("PERPLEXITY_API_KEY not found in environment")
            raise ValueError("PERPLEXITY_API_KEY is required")

        # 初始化Perplexity客户端（使用OpenAI客户端格式）
        try:
            self.client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
            self.model = "sonar"  # Perplexity的轻量级搜索模型
            logger.info("NewsSearchService initialized with Perplexity AI (sonar model)")
        except Exception as e:
            logger.error(f"Failed to initialize Perplexity client: {e}")
            raise

    def search_stock_news(
        self, stock_name: str, stock_code: str, days: int = 7, max_results: int = 5
    ) -> list[dict[str, str]]:
        """搜索股票相关新闻.

        Args:
            stock_name: 股票名称
            stock_code: 股票代码
            days: 搜索最近几天的新闻
            max_results: 最大返回结果数

        Returns:
            新闻列表，格式: [{"title": "", "url": "", "summary": "", "date": "", "source": ""}, ...]
        """
        try:
            logger.info(f"Searching news for {stock_name}({stock_code})...")

            # 构建搜索提示词
            prompt = f"""请搜索{stock_name}({stock_code})的最新新闻，包括股价动态、公司公告、行业新闻。

请严格按照以下格式返回{max_results}条最重要的新闻，每条新闻一行：

标题。摘要内容（50-100字）。时间：YYYY-MM-DD。来源：网站名

示例：
贵州茅台股价创新高。受市场情绪影响，贵州茅台股价今日上涨2%，收盘价1500元，成交额突破100亿。2026-01-15。新浪财经

请直接按格式返回新闻，不要添加其他说明文字。"""

            logger.debug(f"Perplexity search prompt: {prompt[:100]}...")

            # 调用Perplexity API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3,  # 降低温度以获得更确定的答案
            )

            # 解析响应
            content = response.choices[0].message.content
            logger.debug(f"Perplexity response length: {len(content)}")

            # 提取新闻条目
            news_list = self._parse_perplexity_response(content, stock_name, stock_code)

            # 如果解析出的新闻少于max_results，使用原始内容作为一条新闻
            if not news_list:
                logger.warning("Failed to parse structured news from Perplexity response")
                news_list = [
                    {
                        "title": f"{stock_name}({stock_code}) 最新动态",
                        "url": f"https://www.perplexity.ai/search?q={stock_name}+{stock_code}",
                        "summary": content[:500] if len(content) > 500 else content,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "Perplexity AI",
                    }
                ]

            logger.info(f"Found {len(news_list)} news articles for {stock_name}")

            # 限制返回数量
            return news_list[:max_results]

        except Exception as e:
            logger.error(f"Failed to search news for {stock_name}: {e}", exc_info=True)

            # 返回错误占位符
            return [
                {
                    "title": f"{stock_name}({stock_code}) 新闻搜索",
                    "url": f"https://www.perplexity.ai/search?q={stock_name}+{stock_code}+新闻",
                    "summary": "暂时无法获取新闻，请稍后重试",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "Perplexity AI",
                }
            ]

    def _parse_perplexity_response(
        self, content: str, stock_name: str, stock_code: str
    ) -> list[dict[str, str]]:
        """解析Perplexity AI的响应，提取结构化的新闻条目.

        Args:
            content: Perplexity AI返回的内容
            stock_name: 股票名称
            stock_code: 股票代码

        Returns:
            新闻列表
        """
        news_list = []

        try:
            # 清理内容
            content = re.sub(r"\[\d+\]", "", content)  # 移除引用标记
            content = re.sub(r"\*\*", "", content)  # 移除粗体标记

            # 按行分割
            lines = content.split("\n")

            for line in lines:
                line = line.strip()
                if not line or len(line) < 20:
                    continue

                # 跳过示例行和说明行
                if any(
                    keyword in line
                    for keyword in ["示例", "格式", "标题。摘要", "贵州茅台股价", "说明"]
                ):
                    continue

                # 解析格式：标题。摘要。时间：YYYY-MM-DD。来源：网站名
                # 或者：标题。摘要（50-100字）。时间。来源
                parts = re.split(r"。", line)
                if len(parts) < 3:
                    continue

                # 提取标题（第一部分）
                title = parts[0].strip()
                # 移除可能的编号前缀
                title = re.sub(r"^\d+[\.\、]\s*", "", title)
                title = re.sub(r"^\d+\.\s*[股价动态|公司公告|行业新闻][：:]\s*", "", title)

                if len(title) < 5:
                    continue

                # 提取摘要（中间部分）
                summary = "。".join(parts[1:-2]).strip() if len(parts) > 3 else parts[1].strip()
                # 清理摘要中的时间、来源等字段
                summary = re.sub(
                    r"时间[：:]\s*20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*。?", "", summary
                )
                summary = re.sub(r"时间[：:][^。]*。?", "", summary)
                summary = re.sub(r"来源[：:][^。]*。?", "", summary)
                summary = summary.strip()

                if len(summary) < 10:
                    continue

                # 提取日期和来源（最后部分）
                date = datetime.now().strftime("%Y-%m-%d")
                source = "Perplexity AI"

                last_part = parts[-1].strip()
                # 尝试提取日期
                date_match = re.search(r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)", last_part)
                if date_match:
                    date = self._normalize_date(date_match.group(1))
                    # 尝试提取来源
                    source_match = re.search(r"来源[：:]\s*([^\s。]+)", last_part)
                    if source_match:
                        source = source_match.group(1).strip()[:20]
                else:
                    # 检查倒数第二部分
                    if len(parts) > 2:
                        second_last = parts[-2].strip()
                        date_match = re.search(
                            r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)", second_last
                        )
                        if date_match:
                            date = self._normalize_date(date_match.group(1))
                        source_match = re.search(r"来源[：:]\s*([^\s。]+)", second_last)
                        if source_match:
                            source = source_match.group(1).strip()[:20]

                # 从内容中查找URL
                url_match = re.search(r"https?://[^\s\]]+", line)
                url = (
                    url_match.group(0)
                    if url_match
                    else f"https://www.perplexity.ai/search?q={stock_name}+{stock_code}"
                )

                news_list.append(
                    {
                        "title": title,
                        "url": url,
                        "summary": summary[:300],
                        "date": date,
                        "source": source,
                    }
                )

            # 如果没有找到新闻，尝试其他格式
            if not news_list:
                # 尝试按Markdown列表格式解析
                items = re.split(r"\n(?=\d+[\.\、]|-|\*)", content)
                for item in items:
                    item = item.strip()
                    if len(item) < 30:
                        continue

                    # 提取信息
                    lines = item.split("\n")
                    if lines:
                        # 第一行作为标题
                        title = re.sub(r"^[\d\.\-\*\s]+", "", lines[0]).strip()
                        title = re.sub(r"^[股价动态|公司公告|行业新闻][：:]\s*", "", title)

                        if len(title) < 5:
                            continue

                        # 其余行作为摘要
                        summary = "\n".join(lines[1:]).strip()
                        summary = re.sub(r"\n+", " ", summary)
                        summary = re.sub(r"\[\d+\]", "", summary)

                        if len(summary) < 10:
                            continue

                        # 提取日期
                        date_match = re.search(r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)", item)
                        date = (
                            date_match.group(1)
                            if date_match
                            else datetime.now().strftime("%Y-%m-%d")
                        )
                        date = self._normalize_date(date)

                        news_list.append(
                            {
                                "title": title,
                                "url": f"https://www.perplexity.ai/search?q={stock_name}+{stock_code}",
                                "summary": summary[:300],
                                "date": date,
                                "source": "Perplexity AI",
                            }
                        )

            # 如果仍然没有找到，使用整个内容
            if not news_list:
                clean_content = re.sub(r"\n+", " ", content).strip()[:500]
                news_list.append(
                    {
                        "title": f"{stock_name}({stock_code}) 最新动态",
                        "url": f"https://www.perplexity.ai/search?q={stock_name}+{stock_code}",
                        "summary": clean_content,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "Perplexity AI",
                    }
                )

        except Exception as e:
            logger.error(f"Error parsing Perplexity response: {e}", exc_info=True)
            clean_content = re.sub(r"\[\d+\]", "", content)
            clean_content = re.sub(r"\n+", " ", clean_content).strip()
            news_list = [
                {
                    "title": f"{stock_name}({stock_code}) 最新动态",
                    "url": f"https://www.perplexity.ai/search?q={stock_name}+{stock_code}",
                    "summary": clean_content[:500] if len(clean_content) > 500 else clean_content,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "Perplexity AI",
                }
            ]

        return news_list

    def _normalize_date(self, date_str: str) -> str:
        """标准化日期格式.

        Args:
            date_str: 日期字符串

        Returns:
            格式化的日期 (YYYY-MM-DD)
        """
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")

        try:
            # 移除中文日期字符
            date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")

            # 尝试解析各种格式
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue

            return datetime.now().strftime("%Y-%m-%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")

    def _extract_source(self, url: str) -> str:
        """从URL提取网站来源.

        Args:
            url: 新闻链接

        Returns:
            网站名称
        """
        if not url:
            return "Perplexity AI"

        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc

            # 移除 www. 前缀
            if domain.startswith("www."):
                domain = domain[4:]

            # 特殊域名处理
            domain_map = {
                "perplexity.ai": "Perplexity AI",
                "sina.com.cn": "新浪财经",
                "eastmoney.com": "东方财富",
                "10jqka.com.cn": "同花顺",
                "stcn.com": "证券时报",
            }

            if domain in domain_map:
                return domain_map[domain]

            # 提取主域名
            parts = domain.split(".")
            if len(parts) >= 2:
                return parts[-2]

            return domain
        except Exception:
            return "网络"

    def format_news_card(self, news_list: list[dict], stock_name: str, stock_code: str) -> str:
        """格式化新闻为卡片样式.

        Args:
            news_list: 新闻列表
            stock_name: 股票名称
            stock_code: 股票代码

        Returns:
            格式化的新闻卡片文本（HTML格式）
        """
        if not news_list:
            return f"""📰 <b>{stock_name}({stock_code}) 新闻</b>

暂无最新新闻

💡 提示：请稍后再试或使用搜索引擎查询"""

        msg = f"📰 <b>{stock_name}({stock_code})</b> 新闻动态\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, news in enumerate(news_list, 1):
            # 标题
            title = news.get("title", "未知标题")
            msg += f"<b>{i}. {title[:50]}...</b>\n" if len(title) > 50 else f"<b>{i}. {title}</b>\n"

            # 摘要
            summary = news.get("summary", "")
            if summary:
                msg += f"   {summary}\n"

            # 来源和日期
            source = news.get("source", "未知来源")
            date = news.get("date", "")
            if date or source:
                msg += f"   <code>{date} {source}</code>\n"

            # 链接
            url = news.get("url", "")
            if url:
                msg += f'   🔗 <a href="{url}">查看详情</a>\n'

            msg += "\n"

        # 添加底部提示
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🕐 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        msg += "🤖 由 Perplexity AI 提供搜索"

        return msg


# 全局单例
_news_search_service: NewsSearchService | None = None


def get_news_search_service() -> NewsSearchService:
    """获取新闻搜索服务单例.

    Returns:
        NewsSearchService实例
    """
    global _news_search_service
    if _news_search_service is None:
        try:
            _news_search_service = NewsSearchService()
        except Exception as e:
            logger.error(f"Failed to initialize NewsSearchService: {e}")
            raise
    return _news_search_service
