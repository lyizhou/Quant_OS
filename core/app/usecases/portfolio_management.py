"""Portfolio Management UseCase - 持仓管理用例."""


from app.common.logging import logger
from app.data.repositories.user_portfolio_repo import UserPortfolioRepository
from app.drivers.cn_market_driver.driver import CNMarketDriver


class PortfolioManagementUseCase:
    """持仓管理用例."""

    def __init__(self, user_id: str, tushare_token: str | None = None):
        """初始化持仓管理用例.

        Args:
            user_id: 用户ID
            tushare_token: Tushare Token（可选，用于实时价格）
        """
        self.user_id = user_id
        self.portfolio_repo = UserPortfolioRepository()
        self.market_driver = CNMarketDriver(tushare_token) if tushare_token else None

    def add_buy_position(
        self, symbol: str, quantity: float, price: float, market: str = "CN"
    ) -> dict:
        """添加买入持仓.

        Args:
            symbol: 股票代码
            quantity: 买入数量
            price: 买入价格
            market: 市场（CN/US）

        Returns:
            操作结果字典
        """
        try:
            position_id = self.portfolio_repo.update_or_add_position(
                user_id=self.user_id,
                symbol=symbol,
                market=market,
                quantity=quantity,
                price=price,
                operation="buy",
            )

            logger.info(f"Buy position added: {symbol} x{quantity} @{price}")
            return {
                "success": True,
                "position_id": position_id,
                "message": f"Buy {symbol} {quantity} shares @{price:.2f}",
            }

        except Exception as e:
            logger.error(f"Failed to add buy position: {e}")
            return {"success": False, "message": f"Buy failed: {e}"}

    def add_sell_position(
        self, symbol: str, quantity: float, price: float, market: str = "CN"
    ) -> dict:
        """卖出持仓.

        Args:
            symbol: 股票代码
            quantity: 卖出数量
            price: 卖出价格
            market: 市场（CN/US）

        Returns:
            操作结果字典
        """
        try:
            # 获取持仓信息（用于计算盈亏）
            existing = self.portfolio_repo.get_position_by_symbol(self.user_id, symbol, market)
            if not existing:
                return {"success": False, "message": f"No position found for {symbol}"}

            avg_cost = existing["avg_cost"]
            profit = (price - avg_cost) * quantity
            profit_pct = ((price - avg_cost) / avg_cost) * 100

            # 执行卖出
            position_id = self.portfolio_repo.update_or_add_position(
                user_id=self.user_id,
                symbol=symbol,
                market=market,
                quantity=quantity,
                price=price,
                operation="sell",
            )

            logger.info(f"Sell position: {symbol} x{quantity} @{price}, profit: {profit:.2f}")
            return {
                "success": True,
                "position_id": position_id,
                "profit": profit,
                "profit_pct": profit_pct,
                "message": f"Sell {symbol} {quantity} shares @{price:.2f}\n"
                f"P&L: {profit:+.2f} ({profit_pct:+.2f}%)",
            }

        except Exception as e:
            logger.error(f"Failed to sell position: {e}")
            return {"success": False, "message": f"Sell failed: {e}"}

    def get_all_positions(self) -> list[dict]:
        """获取所有持仓.

        Returns:
            持仓列表
        """
        positions = self.portfolio_repo.list_positions_by_user(self.user_id)
        return positions

    def get_positions_with_current_price(self) -> list[dict]:
        """获取所有持仓及当前价格.

        Returns:
            持仓列表（含当前价格、盈亏）
        """
        positions = self.get_all_positions()

        if not positions:
            return []

        # 获取所有股票的当前价格
        symbols = [p["symbol"] for p in positions if p["market"] == "CN"]
        current_prices = {}

        if self.market_driver and symbols:
            try:
                stock_data_list = self.market_driver.fetch_stock_data(symbols)
                current_prices = {s.symbol: s.close for s in stock_data_list}
            except Exception as e:
                logger.warning(f"Failed to fetch current prices: {e}")

        # 计算盈亏
        result = []
        for pos in positions:
            symbol = pos["symbol"]
            avg_cost = pos["avg_cost"]
            quantity = pos["quantity"]
            current_price = current_prices.get(symbol)

            if current_price:
                profit = (current_price - avg_cost) * quantity
                profit_pct = ((current_price - avg_cost) / avg_cost) * 100
                market_value = current_price * quantity
            else:
                profit = None
                profit_pct = None
                market_value = None

            result.append(
                {
                    **pos,
                    "current_price": current_price,
                    "profit": profit,
                    "profit_pct": profit_pct,
                    "market_value": market_value,
                    "cost_value": avg_cost * quantity,
                }
            )

        return result

    def set_stop_loss_profit(
        self, symbol: str, stop_loss: float | None, take_profit: float | None, market: str = "CN"
    ) -> dict:
        """设置止损止盈.

        Args:
            symbol: 股票代码
            stop_loss: 止损价
            take_profit: 止盈价
            market: 市场

        Returns:
            操作结果字典
        """
        try:
            position = self.portfolio_repo.get_position_by_symbol(self.user_id, symbol, market)
            if not position:
                return {"success": False, "message": f"No position found for {symbol}"}

            self.portfolio_repo.update_position(
                position["id"], stop_loss=stop_loss, take_profit=take_profit
            )

            logger.info(f"Set stop loss/profit for {symbol}: {stop_loss}/{take_profit}")
            return {
                "success": True,
                "message": f"Set {symbol} stop loss/profit: {stop_loss or 'N/A'} / {take_profit or 'N/A'}",
            }

        except Exception as e:
            logger.error(f"Failed to set stop loss/profit: {e}")
            return {"success": False, "message": f"Failed: {e}"}

    def get_portfolio_summary(self) -> dict:
        """获取持仓汇总.

        Returns:
            汇总数据字典
        """
        positions = self.get_positions_with_current_price()

        if not positions:
            return {
                "total_positions": 0,
                "total_cost": 0,
                "total_market_value": 0,
                "total_profit": 0,
                "total_profit_pct": 0,
            }

        total_cost = sum(p["cost_value"] for p in positions)
        total_market_value = sum(
            p["market_value"] for p in positions if p["market_value"] is not None
        )
        total_profit = sum(p["profit"] for p in positions if p["profit"] is not None)
        total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_positions": len(positions),
            "total_cost": total_cost,
            "total_market_value": total_market_value,
            "total_profit": total_profit,
            "total_profit_pct": total_profit_pct,
            "positions": positions,
        }
