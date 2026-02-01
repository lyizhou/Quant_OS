"""
板块强度计算服务

计算板块、子板块的强度，并选出最强个股
"""

from dataclasses import dataclass
from datetime import datetime

from app.common.logging import logger
from app.common.time import get_last_market_day
from app.data.repositories.sector_repo import SectorRepository
from app.drivers.cn_market_driver.driver import CNMarketDriver


@dataclass
class StockStrength:
    """个股强度数据"""

    symbol: str
    name: str
    change_pct: float
    price: float
    volume_ratio: float
    turnover_rate: float
    net_money_flow: float  # 主力净流入(万元)
    money_flow_ratio: float  # 主力净流入占比(%)
    strength_score: float


@dataclass
class CategoryStrength:
    """子分类强度数据"""

    category_id: int
    category_name: str
    avg_change_pct: float
    up_count: int
    down_count: int
    total_count: int
    up_ratio: float
    total_net_money_flow: float  # 总主力净流入(万元)
    strength_score: float
    top_stocks: list[StockStrength]


@dataclass
class SectorStrength:
    """板块强度数据"""

    sector_id: int
    sector_name: str
    category: str
    avg_change_pct: float
    up_count: int
    down_count: int
    total_count: int
    up_ratio: float
    avg_turnover_rate: float
    avg_volume_ratio: float
    total_net_money_flow: float  # 总主力净流入(万元)
    strength_score: float
    top_stocks: list[StockStrength]
    categories: list[CategoryStrength]


class SectorStrengthService:
    """板块强度计算服务"""

    def __init__(self, tushare_token: str):
        self.sector_repo = SectorRepository()
        self.market_driver = CNMarketDriver(tushare_token)
        self.tushare_token = tushare_token

    def calculate_strength_score(
        self,
        avg_change_pct: float,
        up_ratio: float,
        avg_volume_ratio: float = 1.0,
        avg_turnover_rate: float = 0.0,
        avg_money_flow_ratio: float = 0.0,
    ) -> float:
        """
        计算强度得分

        公式：
        强度 = 平均涨跌幅 * 0.4 + 上涨比例 * 30 * 0.2 + 量比 * 0.1 + 换手率 * 0.1 + 资金流向占比 * 10 * 0.2
        """
        score = (
            avg_change_pct * 0.4  # 平均涨幅权重40%
            + up_ratio * 30 * 0.2  # 上涨比例权重20% (转换为分数)
            + (avg_volume_ratio - 1) * 10 * 0.1  # 量比权重10%
            + avg_turnover_rate * 0.1  # 换手率权重10%
            + avg_money_flow_ratio * 10 * 0.2  # 资金流向占比权重20%
        )
        return round(score, 2)

    def get_stock_strength(self, symbol: str, stock_data: object) -> StockStrength | None:
        """获取单个股票的强度数据"""
        try:
            # stock_data is CNStockData object
            change_pct = float(stock_data.change_pct) if stock_data.change_pct is not None else 0.0
            price = float(stock_data.close)
            volume_ratio = (
                float(stock_data.volume_ratio) if stock_data.volume_ratio is not None else 1.0
            )
            turnover_rate = (
                float(stock_data.turnover_rate) if stock_data.turnover_rate is not None else 0.0
            )

            # 资金流向
            net_money_flow = (
                float(stock_data.net_money_flow)
                if hasattr(stock_data, "net_money_flow") and stock_data.net_money_flow is not None
                else 0.0
            )
            amount = float(stock_data.amount) if stock_data.amount else 0.0

            # 计算资金流向占比 (%)
            # net_money_flow 是万元, amount 是元
            money_flow_ratio = 0.0
            if amount > 0:
                money_flow_ratio = (net_money_flow * 10000 / amount) * 100

            # 计算个股强度分数
            strength_score = self.calculate_strength_score(
                avg_change_pct=change_pct,
                up_ratio=1.0 if change_pct > 0 else 0.0,
                avg_volume_ratio=volume_ratio,
                avg_turnover_rate=turnover_rate,
                avg_money_flow_ratio=money_flow_ratio,
            )

            return StockStrength(
                symbol=symbol,
                name=stock_data.name,
                change_pct=change_pct,
                price=price,
                volume_ratio=volume_ratio,
                turnover_rate=turnover_rate,
                net_money_flow=net_money_flow,
                money_flow_ratio=money_flow_ratio,
                strength_score=strength_score,
            )
        except Exception as e:
            logger.error(f"Failed to calculate stock strength for {symbol}: {e}")
            return None

    def calculate_sector_strength(
        self, sector_id: int, date: datetime | None = None
    ) -> SectorStrength | None:
        """
        计算板块强度

        Args:
            sector_id: 板块ID
            date: 交易日期，None表示最近交易日

        Returns:
            SectorStrength对象，包含板块强度信息
        """
        try:
            # 获取板块信息
            sector = self.sector_repo.get_sector_by_id(sector_id)
            if not sector:
                logger.warning(f"Sector {sector_id} not found")
                return None

            # 获取板块内所有股票
            stocks = self.sector_repo.get_stocks_by_sector(sector_id)
            if not stocks:
                logger.warning(f"No stocks found in sector {sector_id}")
                return None

            # 优化：限制最多处理前150只股票，避免API调用时间过长
            # 优先选择主板和大盘股（按股票代码前缀排序）
            MAX_STOCKS_PER_SECTOR = 150

            if len(stocks) > MAX_STOCKS_PER_SECTOR:
                logger.info(
                    f"Sector {sector['name']} has {len(stocks)} stocks, "
                    f"selecting top {MAX_STOCKS_PER_SECTOR} (prioritized by market type)"
                )

                def stock_priority(stock):
                    """计算股票优先级（用于排序）"""
                    symbol = stock['symbol']

                    # 优先级：上海主板 > 深圳主板 > 科创板 > 创业板 > 北交所
                    if symbol.startswith('60'):  # 上海主板
                        return 5
                    elif symbol.startswith('00'):  # 深圳主板
                        return 4
                    elif symbol.startswith('688') or symbol.startswith('689'):  # 科创板
                        return 3
                    elif symbol.startswith('30'):  # 创业板
                        return 2
                    else:  # 北交所等
                        return 1

                # 按优先级排序后取前N只
                stocks = sorted(stocks, key=stock_priority, reverse=True)[:MAX_STOCKS_PER_SECTOR]

            # 获取股票代码列表
            symbols = [s["symbol"] for s in stocks]

            # 获取交易日期
            if date is None:
                date = get_last_market_day(market="CN")

            # 获取股票行情数据
            logger.info(
                f"Fetching market data for {len(symbols)} stocks in sector {sector['name']}"
            )
            stock_data_list = self.market_driver.fetch_stock_data(symbols, date)

            if not stock_data_list:
                logger.warning(f"No market data available for sector {sector['name']}")
                return None

            # 创建股票代码到行情数据的映射
            stock_data_map = {data.symbol: data for data in stock_data_list}

            # 计算股票强度
            stock_strengths = []
            for stock in stocks:
                symbol = stock["symbol"]
                if symbol in stock_data_map:
                    strength = self.get_stock_strength(symbol, stock_data_map[symbol])
                    if strength:
                        strength.name = stock["stock_name"]  # 使用数据库中的名称
                        stock_strengths.append(strength)

            if not stock_strengths:
                logger.warning(f"No valid stock data for sector {sector['name']}")
                return None

            # 计算板块统计数据
            total_count = len(stock_strengths)
            up_count = sum(1 for s in stock_strengths if s.change_pct > 0)
            down_count = sum(1 for s in stock_strengths if s.change_pct < 0)
            up_ratio = up_count / total_count if total_count > 0 else 0

            avg_change_pct = sum(s.change_pct for s in stock_strengths) / total_count
            avg_volume_ratio = sum(s.volume_ratio for s in stock_strengths) / total_count
            avg_turnover_rate = sum(s.turnover_rate for s in stock_strengths) / total_count

            # 计算总资金流向
            total_net_money_flow = sum(s.net_money_flow for s in stock_strengths)
            avg_money_flow_ratio = sum(s.money_flow_ratio for s in stock_strengths) / total_count

            # 计算板块强度得分
            strength_score = self.calculate_strength_score(
                avg_change_pct=avg_change_pct,
                up_ratio=up_ratio,
                avg_volume_ratio=avg_volume_ratio,
                avg_turnover_rate=avg_turnover_rate,
                avg_money_flow_ratio=avg_money_flow_ratio,
            )

            # 按强度排序，获取Top股票
            top_stocks = sorted(stock_strengths, key=lambda x: x.change_pct, reverse=True)[:10]

            # 计算子分类强度
            categories = self._calculate_category_strengths(sector_id, stocks, stock_data_map)

            return SectorStrength(
                sector_id=sector_id,
                sector_name=sector["name"],
                category=sector.get("category", ""),
                avg_change_pct=round(avg_change_pct, 2),
                up_count=up_count,
                down_count=down_count,
                total_count=total_count,
                up_ratio=round(up_ratio, 2),
                avg_turnover_rate=round(avg_turnover_rate, 2),
                avg_volume_ratio=round(avg_volume_ratio, 2),
                total_net_money_flow=round(total_net_money_flow, 2),
                strength_score=strength_score,
                top_stocks=top_stocks,
                categories=categories,
            )

        except Exception as e:
            logger.error(f"Failed to calculate sector strength for {sector_id}: {e}", exc_info=True)
            return None

    def _calculate_category_strengths(
        self, sector_id: int, stocks: list[dict], stock_data_map: dict[str, object]
    ) -> list[CategoryStrength]:
        """计算子分类强度"""
        try:
            # 获取所有子分类
            categories = self.sector_repo.get_categories_by_sector(sector_id)
            if not categories:
                return []

            category_strengths = []

            # 按分类名称分组
            category_groups = {}
            for cat in categories:
                cat_name = cat["name"]
                if cat_name not in category_groups:
                    category_groups[cat_name] = []
                category_groups[cat_name].append(cat["id"])

            # 计算每个分类的强度
            for cat_name, cat_ids in category_groups.items():
                # 获取该分类下的股票
                cat_stocks = [s for s in stocks if s.get("category_id") in cat_ids]
                if not cat_stocks:
                    continue

                # 计算分类内股票强度
                stock_strengths = []
                for stock in cat_stocks:
                    symbol = stock["symbol"]
                    if symbol in stock_data_map:
                        strength = self.get_stock_strength(symbol, stock_data_map[symbol])
                        if strength:
                            strength.name = stock["stock_name"]
                            stock_strengths.append(strength)

                if not stock_strengths:
                    continue

                # 计算统计数据
                total_count = len(stock_strengths)
                up_count = sum(1 for s in stock_strengths if s.change_pct > 0)
                down_count = sum(1 for s in stock_strengths if s.change_pct < 0)
                up_ratio = up_count / total_count if total_count > 0 else 0
                avg_change_pct = sum(s.change_pct for s in stock_strengths) / total_count
                avg_volume_ratio = sum(s.volume_ratio for s in stock_strengths) / total_count

                # 资金流向
                total_net_money_flow = sum(s.net_money_flow for s in stock_strengths)
                avg_money_flow_ratio = (
                    sum(s.money_flow_ratio for s in stock_strengths) / total_count
                )

                # 计算强度得分
                strength_score = self.calculate_strength_score(
                    avg_change_pct=avg_change_pct,
                    up_ratio=up_ratio,
                    avg_volume_ratio=avg_volume_ratio,
                    avg_money_flow_ratio=avg_money_flow_ratio,
                )

                # Top股票
                top_stocks = sorted(stock_strengths, key=lambda x: x.change_pct, reverse=True)[:5]

                category_strengths.append(
                    CategoryStrength(
                        category_id=cat_ids[0],  # 使用第一个ID
                        category_name=cat_name,
                        avg_change_pct=round(avg_change_pct, 2),
                        up_count=up_count,
                        down_count=down_count,
                        total_count=total_count,
                        up_ratio=round(up_ratio, 2),
                        total_net_money_flow=round(total_net_money_flow, 2),
                        strength_score=strength_score,
                        top_stocks=top_stocks,
                    )
                )

            # 按强度排序
            category_strengths.sort(key=lambda x: x.strength_score, reverse=True)
            return category_strengths

        except Exception as e:
            logger.error(f"Failed to calculate category strengths: {e}", exc_info=True)
            return []

    def get_all_sectors_strength(self, date: datetime | None = None) -> list[SectorStrength]:
        """
        获取所有板块的强度排行

        Args:
            date: 交易日期，None表示最近交易日

        Returns:
            按强度排序的板块列表
        """
        try:
            # 获取所有板块
            all_sectors = self.sector_repo.list_all_sectors()
            if not all_sectors:
                logger.warning("No sectors found")
                return []

            logger.info(f"Calculating strength for {len(all_sectors)} sectors...")

            sector_strengths = []
            for sector in all_sectors:
                strength = self.calculate_sector_strength(sector["id"], date)
                if strength:
                    sector_strengths.append(strength)

            # 按强度得分排序
            sector_strengths.sort(key=lambda x: x.strength_score, reverse=True)

            logger.info(f"Calculated strength for {len(sector_strengths)} sectors")
            return sector_strengths

        except Exception as e:
            logger.error(f"Failed to get all sectors strength: {e}", exc_info=True)
            return []

    def get_top_stocks_in_sector(
        self, sector_id: int, limit: int = 10, date: datetime | None = None
    ) -> list[StockStrength]:
        """
        获取板块内涨幅Top N的股票

        Args:
            sector_id: 板块ID
            limit: 返回数量
            date: 交易日期

        Returns:
            按涨幅排序的股票列表
        """
        strength = self.calculate_sector_strength(sector_id, date)
        if not strength:
            return []

        return strength.top_stocks[:limit]
