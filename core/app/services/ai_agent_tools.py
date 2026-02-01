"""AI Agent Tools - Tool definitions for the AI agent to call.

These tools wrap existing functionality and provide a clean interface
for the AI agent to interact with the system.
"""

import os
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.data.repositories.user_portfolio_repo import UserPortfolioRepository
from app.data.repositories.sector_repo import SectorRepository
from app.drivers.cn_market_driver.driver import CNMarketDriver
from app.services.sector_strength_service import SectorStrengthService
from app.services.news_search import NewsSearchService
from loguru import logger


class AIAgentTools:
    """Collection of tools that the AI agent can use."""

    def __init__(self):
        """Initialize tools."""
        self.portfolio_repo = UserPortfolioRepository()
        self.sector_repo = SectorRepository()
        self.market_driver = CNMarketDriver()

        # Get tushare token from environment
        tushare_token = os.getenv("TUSHARE_TOKEN")
        self.sector_strength_service = SectorStrengthService(tushare_token)
        self.news_service = None  # Lazy initialization

    async def get_portfolio(self, user_id: str) -> dict:
        """Get user's portfolio with current prices and P&L.

        Args:
            user_id: User ID

        Returns:
            {
                "positions": [
                    {
                        "symbol": str,
                        "name": str,
                        "quantity": int,
                        "cost_price": float,
                        "current_price": float,
                        "profit_loss": float,
                        "profit_loss_ratio": float,
                    }
                ],
                "summary": {
                    "total_value": float,
                    "total_cost": float,
                    "total_profit_loss": float,
                    "total_profit_loss_ratio": float,
                }
            }
        """
        try:
            positions = self.portfolio_repo.get_all_positions(user_id)

            if not positions:
                return {
                    "positions": [],
                    "summary": {
                        "total_value": 0,
                        "total_cost": 0,
                        "total_profit_loss": 0,
                        "total_profit_loss_ratio": 0,
                    },
                }

            # Get current prices
            symbols = [p["symbol"] for p in positions]
            quotes = {}
            for symbol in symbols:
                try:
                    quote = self.market_driver.get_realtime_quote(symbol)
                    if quote:
                        quotes[symbol] = quote["close"]
                except Exception as e:
                    logger.warning(f"Failed to get quote for {symbol}: {e}")

            # Calculate P&L
            enriched_positions = []
            total_value = 0
            total_cost = 0

            for pos in positions:
                symbol = pos["symbol"]
                current_price = quotes.get(symbol, pos["cost_price"])
                quantity = pos["quantity"]
                cost_price = pos["cost_price"]

                value = current_price * quantity
                cost = cost_price * quantity
                profit_loss = value - cost
                profit_loss_ratio = (profit_loss / cost * 100) if cost > 0 else 0

                enriched_positions.append(
                    {
                        "symbol": symbol,
                        "name": pos["stock_name"],
                        "quantity": quantity,
                        "cost_price": cost_price,
                        "current_price": current_price,
                        "profit_loss": profit_loss,
                        "profit_loss_ratio": profit_loss_ratio,
                    }
                )

                total_value += value
                total_cost += cost

            total_profit_loss = total_value - total_cost
            total_profit_loss_ratio = (
                (total_profit_loss / total_cost * 100) if total_cost > 0 else 0
            )

            return {
                "positions": enriched_positions,
                "summary": {
                    "total_value": total_value,
                    "total_cost": total_cost,
                    "total_profit_loss": total_profit_loss,
                    "total_profit_loss_ratio": total_profit_loss_ratio,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get portfolio: {e}", exc_info=True)
            return {"error": str(e)}

    async def get_sector_strength(self, top_n: int = 10) -> dict:
        """Get top N sectors by strength.

        Args:
            top_n: Number of top sectors to return

        Returns:
            {
                "sectors": [
                    {
                        "name": str,
                        "strength_score": float,
                        "avg_change_pct": float,
                        "up_ratio": float,
                        "top_stocks": list,
                    }
                ]
            }
        """
        try:
            all_sectors = self.sector_strength_service.get_all_sectors_strength()

            # Sort by strength score
            sorted_sectors = sorted(
                all_sectors, key=lambda x: x.get("strength_score", 0), reverse=True
            )

            return {"sectors": sorted_sectors[:top_n]}

        except Exception as e:
            logger.error(f"Failed to get sector strength: {e}", exc_info=True)
            return {"error": str(e)}

    async def get_stock_quote(self, symbol: str) -> dict:
        """Get real-time quote for a stock.

        Args:
            symbol: Stock code (e.g., "600000" or "贵州茅台")

        Returns:
            {
                "symbol": str,
                "name": str,
                "price": float,
                "change": float,
                "change_pct": float,
                "volume": float,
                "turnover": float,
                "high": float,
                "low": float,
                "open": float,
            }
        """
        try:
            # Try to resolve name to code
            if not symbol.isdigit():
                resolved = self.market_driver.stock_mapper.get_stock_code(symbol)
                if resolved:
                    symbol = resolved

            quote = self.market_driver.get_realtime_quote(symbol)

            if not quote:
                return {"error": f"未找到股票: {symbol}"}

            return {
                "symbol": quote["ts_code"],
                "name": quote["name"],
                "price": quote["close"],
                "change": quote["change"],
                "change_pct": quote["pct_chg"],
                "volume": quote.get("vol", 0),
                "turnover": quote.get("amount", 0),
                "high": quote.get("high", 0),
                "low": quote.get("low", 0),
                "open": quote.get("open", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get stock quote: {e}", exc_info=True)
            return {"error": str(e)}

    async def search_stock(self, keyword: str) -> dict:
        """Search for stocks by keyword.

        Args:
            keyword: Search keyword (name or code)

        Returns:
            {
                "results": [
                    {
                        "symbol": str,
                        "name": str,
                    }
                ]
            }
        """
        try:
            results = self.market_driver.stock_mapper.search_stocks(keyword)

            return {
                "results": [
                    {"symbol": r["ts_code"], "name": r["name"]} for r in results[:10]
                ]
            }

        except Exception as e:
            logger.error(f"Failed to search stock: {e}", exc_info=True)
            return {"error": str(e)}

    async def get_hot_sectors(self, top_n: int = 5) -> dict:
        """Get hottest sectors today.

        Args:
            top_n: Number of sectors to return

        Returns:
            {
                "sectors": [
                    {
                        "name": str,
                        "avg_change_pct": float,
                        "up_ratio": float,
                        "leader": str,
                    }
                ]
            }
        """
        try:
            all_sectors = self.sector_strength_service.get_all_sectors_strength()

            # Sort by avg_change_pct
            sorted_sectors = sorted(
                all_sectors, key=lambda x: x.get("avg_change_pct", 0), reverse=True
            )

            hot_sectors = []
            for sector in sorted_sectors[:top_n]:
                top_stocks = sector.get("top_stocks", [])
                leader = top_stocks[0]["name"] if top_stocks else "N/A"

                hot_sectors.append(
                    {
                        "name": sector["sector_name"],
                        "avg_change_pct": sector["avg_change_pct"],
                        "up_ratio": sector["up_ratio"],
                        "leader": leader,
                    }
                )

            return {"sectors": hot_sectors}

        except Exception as e:
            logger.error(f"Failed to get hot sectors: {e}", exc_info=True)
            return {"error": str(e)}

    async def get_market_summary(self) -> dict:
        """Get overall market summary.

        Returns:
            {
                "indices": {
                    "sh": {"name": str, "close": float, "change_pct": float},
                    "sz": {"name": str, "close": float, "change_pct": float},
                    "cyb": {"name": str, "close": float, "change_pct": float},
                },
                "market_sentiment": str,
            }
        """
        try:
            # Get major indices
            indices = {}
            for code, name in [
                ("000001.SH", "上证指数"),
                ("399001.SZ", "深证成指"),
                ("399006.SZ", "创业板指"),
            ]:
                try:
                    quote = self.market_driver.get_realtime_quote(code)
                    if quote:
                        indices[code] = {
                            "name": name,
                            "close": quote["close"],
                            "change_pct": quote["pct_chg"],
                        }
                except Exception as e:
                    logger.warning(f"Failed to get index {code}: {e}")

            # Determine sentiment
            avg_change = sum(idx["change_pct"] for idx in indices.values()) / len(
                indices
            )
            if avg_change > 1:
                sentiment = "强势上涨"
            elif avg_change > 0:
                sentiment = "温和上涨"
            elif avg_change > -1:
                sentiment = "小幅下跌"
            else:
                sentiment = "明显下跌"

            return {"indices": indices, "market_sentiment": sentiment}

        except Exception as e:
            logger.error(f"Failed to get market summary: {e}", exc_info=True)
            return {"error": str(e)}

    async def search_news(self, query: str, max_results: int = 5) -> dict:
        """Search for news about a stock or topic.

        Args:
            query: Search query
            max_results: Max number of results

        Returns:
            {
                "news": [
                    {
                        "title": str,
                        "summary": str,
                        "url": str,
                        "date": str,
                        "source": str,
                    }
                ]
            }
        """
        try:
            # Lazy initialize news service
            if self.news_service is None:
                try:
                    self.news_service = NewsSearchService()
                except Exception as e:
                    logger.warning(f"Failed to initialize news service: {e}")
                    return {
                        "news": [],
                        "error": "新闻搜索服务不可用，请配置 PERPLEXITY_API_KEY"
                    }

            # Parse query to extract stock name and code if possible
            # For now, just use the query as is
            news_results = self.news_service.search_stock_news(
                stock_name=query,
                stock_code="",
                max_results=max_results
            )

            return {"news": news_results}

        except Exception as e:
            logger.error(f"Failed to search news: {e}", exc_info=True)
            return {"error": str(e), "news": []}


def register_all_tools(agent):
    """Register all tools with the AI agent.

    Args:
        agent: AIAgentService instance
    """
    tools = AIAgentTools()

    # Portfolio tools
    agent.register_tool(
        name="get_portfolio",
        description="获取用户的持仓信息，包括每只股票的盈亏情况",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户ID",
                }
            },
            "required": ["user_id"],
        },
        function=tools.get_portfolio,
    )

    # Sector tools
    agent.register_tool(
        name="get_sector_strength",
        description="获取板块强度排名，找出最强势的板块",
        parameters={
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "返回前N个板块，默认10",
                    "default": 10,
                }
            },
        },
        function=tools.get_sector_strength,
    )

    agent.register_tool(
        name="get_hot_sectors",
        description="获取今日最热门的板块",
        parameters={
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "返回前N个板块，默认5",
                    "default": 5,
                }
            },
        },
        function=tools.get_hot_sectors,
    )

    # Stock tools
    agent.register_tool(
        name="get_stock_quote",
        description="获取个股的实时行情数据",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码或名称，例如 '600000' 或 '贵州茅台'",
                }
            },
            "required": ["symbol"],
        },
        function=tools.get_stock_quote,
    )

    agent.register_tool(
        name="search_stock",
        description="搜索股票，支持模糊匹配",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词",
                }
            },
            "required": ["keyword"],
        },
        function=tools.search_stock,
    )

    # Market tools
    agent.register_tool(
        name="get_market_summary",
        description="获取市场整体概况，包括主要指数和市场情绪",
        parameters={"type": "object", "properties": {}},
        function=tools.get_market_summary,
    )

    # News tools
    agent.register_tool(
        name="search_news",
        description="搜索股票或主题相关的新闻",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回几条新闻，默认5",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        function=tools.search_news,
    )

    logger.info(f"✓ Registered {len(agent.tools)} tools for AI agent")
