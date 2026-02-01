"""Tavily News Search Service - 使用Tavily API搜索新闻."""

import os
from datetime import datetime, timedelta

from loguru import logger

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logger.warning("tavily-python not installed. Install with: uv add tavily-python")


class TavilyNewsService:
    """Tavily新闻搜索服务."""

    def __init__(self, api_key: str | None = None):
        """初始化Tavily新闻搜索服务.

        Args:
            api_key: Tavily API密钥，如果不提供则从环境变量读取
        """
        if not TAVILY_AVAILABLE:
            raise ImportError("tavily-python is not installed")

        # 获取API密钥
        if api_key is None:
            api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            logger.error("TAVILY_API_KEY not found in environment")
            raise ValueError("TAVILY_API_KEY is required")

        # 初始化Tavily客户端
        try:
            self.client = TavilyClient(api_key=api_key)
            logger.info("TavilyNewsService initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Tavily client: {e}")
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
            # 构建搜索查询
            query = f"{stock_name} {stock_code} 最新新闻 股票"

            logger.info(f"Searching Tavily for: {query}")

            # 调用Tavily搜索API
            response = self.client.search(
                query=query,
                search_depth="basic",  # basic or advanced
                max_results=max_results,
                include_domains=["sina.com.cn", "eastmoney.com", "cnstock.com", "cs.com.cn"],
                days=days,
            )

            # 解析结果
            news_list = []
            if response and "results" in response:
                for item in response["results"]:
                    news_item = {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "summary": item.get("content", "")[:200],  # 限制摘要长度
                        "date": self._parse_date(item.get("published_date", "")),
                        "source": self._extract_source(item.get("url", "")),
                    }
                    news_list.append(news_item)

            logger.info(f"Found {len(news_list)} news items for {stock_name}")
            return news_list

        except Exception as e:
            logger.error(f"Failed to search Tavily news: {e}")
            return []

    def _parse_date(self, date_str: str) -> str:
        """解析日期字符串."""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")

        try:
            # Tavily返回ISO格式日期，可能包含时区信息
            # 处理多种日期格式
            from datetime import timezone, timedelta

            # 移除 'Z' 并替换为 UTC 时区
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'

            # 解析ISO格式日期
            dt = datetime.fromisoformat(date_str)

            # 如果有时区信息，转换为中国时间 (UTC+8)
            if dt.tzinfo is not None:
                china_tz = timezone(timedelta(hours=8))
                dt = dt.astimezone(china_tz)

            return dt.strftime("%Y-%m-%d")
        except Exception as e:
            # 如果解析失败，尝试只取日期部分
            try:
                # 尝试提取 YYYY-MM-DD 格式
                if len(date_str) >= 10:
                    return date_str[:10]
            except Exception:
                pass

            # 最后返回今天的日期
            return datetime.now().strftime("%Y-%m-%d")

    def _extract_source(self, url: str) -> str:
        """从URL提取来源."""
        if "sina.com" in url:
            return "新浪财经"
        elif "eastmoney.com" in url:
            return "东方财富"
        elif "cnstock.com" in url:
            return "中国证券网"
        elif "cs.com.cn" in url:
            return "中证网"
        elif "hexun.com" in url:
            return "和讯网"
        elif "10jqka.com.cn" in url:
            return "同花顺"
        else:
            # 提取域名
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                return domain.replace("www.", "")
            except Exception:
                return "未知来源"

    def format_news_card(
        self, news_list: list[dict[str, str]], stock_name: str, stock_code: str
    ) -> str:
        """格式化新闻卡片.

        Args:
            news_list: 新闻列表
            stock_name: 股票名称
            stock_code: 股票代码

        Returns:
            格式化的新闻卡片HTML
        """
        if not news_list:
            return (
                f"📰 <b>{stock_name} ({stock_code})</b> 相关新闻\n\n"
                f"⚠️ 暂无最新新闻\n\n"
                f"💡 可能原因:\n"
                f"• 该股票近期无重大新闻\n"
                f"• 新闻源暂时无法访问\n"
                f"• 搜索关键词未匹配到结果"
            )

        msg = f"📰 <b>{stock_name} ({stock_code})</b> 最新新闻\n"
        msg += f"{'=' * 30}\n\n"

        for i, news in enumerate(news_list[:5], 1):
            msg += f"{i}. <b>{news['title']}</b>\n"
            msg += f"   📅 {news['date']} | 📰 {news['source']}\n"

            if news.get("summary"):
                summary = news["summary"][:100]
                if len(news["summary"]) > 100:
                    summary += "..."
                msg += f"   💬 {summary}\n"

            if news.get("url"):
                msg += f"   🔗 <a href='{news['url']}'>查看详情</a>\n"

            msg += "\n"

        msg += f"💡 数据来源: Tavily Search API"

        return msg
