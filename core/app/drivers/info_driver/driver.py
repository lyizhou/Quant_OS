"""Info Driver - 抽象化信息源获取和AI分析."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


@dataclass
class InfoItem:
    """统一的信息条目数据结构."""

    id: str  # 唯一标识符
    source: str  # 来源（twitter, rss, weibo等）
    author: str  # 作者/来源账号
    text: str  # 原始文本
    timestamp: datetime  # 发布时间
    url: str | None = None  # 原文链接
    metadata: dict[str, Any] | None = None  # 额外元数据


class InfoSource(ABC):
    """信息源抽象基类."""

    @abstractmethod
    def fetch_latest(self, limit: int = 10) -> list[InfoItem]:
        """获取最新信息.

        Args:
            limit: 返回条目数量

        Returns:
            InfoItem列表
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """获取信息源名称."""
        pass


class TwitterInfoSource(InfoSource):
    """Twitter信息源（使用RapidAPI）."""

    def __init__(self, api_key: str, target_user: str = "elonmusk") -> None:
        """初始化Twitter信息源.

        Args:
            api_key: RapidAPI密钥
            target_user: 目标用户名
        """
        self.api_key = api_key
        self.target_user = target_user
        self.rapid_host = "twitterapi-io.p.rapidapi.com"

    def get_source_name(self) -> str:
        """获取信息源名称."""
        return f"twitter_{self.target_user}"

    def fetch_latest(self, limit: int = 10) -> list[InfoItem]:
        """获取最新推文.

        Args:
            limit: 返回推文数量

        Returns:
            InfoItem列表
        """
        url = f"https://{self.rapid_host}/user/tweets"
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.rapid_host}
        params = {
            "userName": self.target_user,
            "limit": str(limit),
            "includeReplies": "true",
        }

        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_tweets(data)
                else:
                    print(f"[Twitter API] Status code: {response.status_code}")
        except Exception as e:
            print(f"[Twitter Error] {e}")

        return []

    def _parse_tweets(self, data: dict) -> list[InfoItem]:
        """解析Twitter API响应.

        Args:
            data: API响应JSON

        Returns:
            InfoItem列表
        """
        if not data or "tweets" not in data:
            return []

        items = []
        for tweet in data["tweets"]:
            # 提取ID
            tweet_id = tweet.get("entryId") or tweet.get("id")
            if not tweet_id:
                continue

            # 提取文本
            text = tweet.get("text", "")
            if not text:
                try:
                    text = tweet["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
                        "full_text"
                    ]
                except (KeyError, TypeError):
                    text = ""

            # 提取作者
            author = tweet.get("author", self.target_user)

            # 创建InfoItem
            item = InfoItem(
                id=tweet_id,
                source="twitter",
                author=author,
                text=text,
                timestamp=datetime.now(),  # Twitter API不返回时间戳，使用当前时间
                url=f"https://twitter.com/{author}/status/{tweet_id}",
                metadata={"raw": tweet},
            )
            items.append(item)

        return items


class DeepSeekAnalyzer:
    """DeepSeek AI分析器."""

    def __init__(self, api_key: str) -> None:
        """初始化DeepSeek分析器.

        Args:
            api_key: DeepSeek API密钥
        """
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/chat/completions"

    def analyze(self, text: str, system_prompt: str | None = None, temperature: float = 1.0) -> str:
        """分析文本（翻译/摘要/分类等）.

        Args:
            text: 输入文本
            system_prompt: 系统提示词（可选）
            temperature: 温度参数

        Returns:
            分析结果文本
        """
        if not text or not self.api_key:
            return "（无分析结果）"

        if system_prompt is None:
            system_prompt = "你是一个专业的文本分析助手，擅长翻译和总结。"

        try:
            with httpx.Client(timeout=20) as client:
                response = client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text},
                        ],
                        "temperature": temperature,
                    },
                )

                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"[DeepSeek Error] {e}")

        return "分析服务暂时不可用"

    def batch_analyze(self, texts: list[str], system_prompt: str | None = None) -> list[str]:
        """批量分析多条文本.

        Args:
            texts: 文本列表
            system_prompt: 系统提示词（可选）

        Returns:
            分析结果列表
        """
        return [self.analyze(text, system_prompt) for text in texts]

    def translate_tweet(self, text: str) -> str:
        """翻译推文（保留Musk风格）.

        Args:
            text: 推文原文

        Returns:
            翻译后的中文
        """
        system_prompt = (
            "将 Elon Musk 的这条推文翻译成中文。保持他那种简短、神秘或讽刺的语气。"
            "如果包含加密货币术语（如 DOGE, HODL）或股市术语，请保留原词或专业意译。"
            "不需要任何解释性前言，直接输出译文。"
        )
        return self.analyze(text, system_prompt, temperature=1.3)

    def summarize_narrative(self, texts: list[str]) -> str:
        """聚类总结多条信息为叙事.

        Args:
            texts: 信息文本列表

        Returns:
            叙事总结
        """
        combined = "\n\n---\n\n".join(texts)
        system_prompt = (
            "你是一个市场叙事分析师。分析以下信息，提取出主要的市场叙事主题。"
            "用简洁的中文总结，不超过200字。突出关键词和情绪倾向。"
        )
        return self.analyze(combined, system_prompt, temperature=0.8)


class InfoDriver:
    """信息驱动器 - 统一管理多个信息源和AI分析."""

    def __init__(
        self,
        sources: list[InfoSource],
        analyzer: DeepSeekAnalyzer | None = None,
    ) -> None:
        """初始化信息驱动器.

        Args:
            sources: 信息源列表
            analyzer: AI分析器（可选）
        """
        self.sources = sources
        self.analyzer = analyzer

    def fetch_all(self, limit_per_source: int = 10) -> list[InfoItem]:
        """从所有信息源获取信息.

        Args:
            limit_per_source: 每个源的条目数量

        Returns:
            所有InfoItem列表（按时间戳排序）
        """
        all_items = []

        for source in self.sources:
            try:
                items = source.fetch_latest(limit_per_source)
                all_items.extend(items)
            except Exception as e:
                print(f"[Source Error] {source.get_source_name()}: {e}")

        # 按时间戳排序（新 -> 旧）
        all_items.sort(key=lambda x: x.timestamp, reverse=True)
        return all_items

    def fetch_and_analyze(
        self, limit_per_source: int = 10, system_prompt: str | None = None
    ) -> list[tuple[InfoItem, str]]:
        """获取信息并分析.

        Args:
            limit_per_source: 每个源的条目数量
            system_prompt: 分析的系统提示词

        Returns:
            (InfoItem, 分析结果) 元组列表
        """
        if not self.analyzer:
            raise ValueError("未配置analyzer，无法执行分析")

        items = self.fetch_all(limit_per_source)
        results = []

        for item in items:
            analysis = self.analyzer.analyze(item.text, system_prompt)
            results.append((item, analysis))

        return results
