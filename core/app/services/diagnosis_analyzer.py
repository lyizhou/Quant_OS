"""持仓诊断分析服务"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.common.logging import logger
from app.drivers.cn_market_driver.driver import CNMarketDriver


@dataclass
class OverviewData:
    """持仓概览数据"""

    total_market_value: Decimal  # 持仓总值
    total_account_value: Decimal  # 账户总值
    total_profit_loss: Decimal  # 总盈亏
    profit_loss_ratio: Decimal  # 盈亏比例
    position_count: int  # 持仓数量
    position_ratio: Decimal  # 仓位比例
    cash_ratio: Decimal  # 现金比例


@dataclass
class StockDiagnosis:
    """个股诊断数据"""

    stock_code: str
    stock_name: str
    sector: str

    # 持仓信息
    current_price: Decimal
    cost_price: Decimal
    quantity: int
    market_value: Decimal
    profit_loss: Decimal
    profit_loss_ratio: Decimal
    position_ratio: Decimal

    # 市场表现
    today_change: Decimal
    volume: int
    turnover_rate: Decimal
    amplitude: Decimal

    # 技术指标
    rsi: Decimal
    macd_dif: Decimal
    macd_dea: Decimal
    kdj_k: Decimal
    kdj_d: Decimal
    boll_upper: Decimal
    boll_lower: Decimal

    # 估值指标
    pe: Decimal | None
    pe_ttm: Decimal | None
    pb: Decimal | None
    ps: Decimal | None

    # 近期走势
    recent_prices: list[dict[str, Any]]

    # 综合评级
    rating: str  # "看好" / "中性" / "风险"
    rating_color: str  # "🟢" / "🟡" / "🔴"

    # AI 分析
    ai_analysis: str = ""


class DiagnosisAnalyzer:
    """诊断分析服务"""

    def __init__(self, market_driver: CNMarketDriver):
        self.market_driver = market_driver

    def calculate_overview(self, positions: list[dict]) -> OverviewData:
        """
        计算持仓概览

        Args:
            positions: 持仓列表

        Returns:
            OverviewData: 持仓概览数据
        """
        total_market_value = Decimal(0)
        total_cost = Decimal(0)

        for pos in positions:
            quantity = Decimal(pos["quantity"])

            # 兼容字段名
            cost_val = (
                pos.get("cost_price")
                if pos.get("cost_price") is not None
                else pos.get("avg_cost", 0)
            )
            cost_price = Decimal(str(cost_val))

            stock_code = pos.get("stock_code") or pos.get("symbol")
            if not stock_code:
                continue

            # 获取实时价格
            quote = self.market_driver.get_realtime_quote(stock_code)
            if quote:
                current_price = Decimal(quote["close"])
            else:
                logger.warning(f"无法获取 {stock_code} 实时价格，使用成本价")
                current_price = cost_price

            market_value = current_price * quantity
            cost_value = cost_price * quantity

            total_market_value += market_value
            total_cost += cost_value

        total_profit_loss = total_market_value - total_cost
        profit_loss_ratio = (total_profit_loss / total_cost * 100) if total_cost > 0 else Decimal(0)

        # 假设账户总值 = 持仓总值（实际应从账户数据获取）
        total_account_value = total_market_value
        position_ratio = Decimal(100)  # 100% 仓位
        cash_ratio = Decimal(0)

        return OverviewData(
            total_market_value=total_market_value,
            total_account_value=total_account_value,
            total_profit_loss=total_profit_loss,
            profit_loss_ratio=profit_loss_ratio,
            position_count=len(positions),
            position_ratio=position_ratio,
            cash_ratio=cash_ratio,
        )

    def analyze_stock(self, position: dict, total_value: Decimal) -> StockDiagnosis | None:
        """
        分析单只股票

        Args:
            position: 持仓信息
            total_value: 总市值（用于计算仓位占比）

        Returns:
            StockDiagnosis | None: 个股诊断数据，失败返回 None
        """
        stock_code = position.get("stock_code") or position.get("symbol")
        if not stock_code:
            logger.error("持仓数据缺少代码信息")
            return None

        # 提取股票名称
        stock_name = position.get("stock_name", "")
        if not stock_name and position.get("notes"):
            # 尝试从备注提取: "股票名称:xxxx"
            import re

            match = re.search(r"股票名称[:：](.+)", position["notes"])
            if match:
                stock_name = match.group(1).strip()

        if not stock_name:
            stock_name = stock_code

        try:
            # 1. 获取实时行情
            quote = self.market_driver.get_realtime_quote(stock_code)
            if not quote:
                logger.error(f"无法获取 {stock_code} 行情数据")
                return None

            # 2. 获取技术指标
            technical = self.market_driver.calculate_technical_indicators(stock_code, days=60)

            # 3. 获取近期走势（最近5个交易日）
            recent_data = self.market_driver.get_historical_data(stock_code, days=5)
            recent_prices = []
            if recent_data is not None and not recent_data.empty:
                for _, row in recent_data.iterrows():
                    recent_prices.append(
                        {
                            "trade_date": row.get("trade_date", ""),
                            "close": float(row.get("close", 0)),
                            "pct_chg": float(row.get("pct_chg", 0)),
                        }
                    )

            # 4. 计算持仓盈亏
            current_price = Decimal(str(quote["close"]))

            cost_val = (
                position.get("cost_price")
                if position.get("cost_price") is not None
                else position.get("avg_cost", 0)
            )
            cost_price = Decimal(str(cost_val))

            quantity = int(position["quantity"])

            market_value = current_price * quantity
            cost_value = cost_price * quantity
            profit_loss = market_value - cost_value
            profit_loss_ratio = (profit_loss / cost_value * 100) if cost_value > 0 else Decimal(0)

            # 计算仓位占比
            position_ratio = (market_value / total_value * 100) if total_value > 0 else Decimal(0)

            # 5. 提取技术指标
            rsi = Decimal(str(technical.get("rsi", 50)))
            macd_dif = Decimal(str(technical.get("macd_dif", 0)))
            macd_dea = Decimal(str(technical.get("macd_dea", 0)))
            kdj_k = Decimal(str(technical.get("kdj_k", 50)))
            kdj_d = Decimal(str(technical.get("kdj_d", 50)))
            boll_upper = Decimal(str(technical.get("boll_upper", 0)))
            boll_lower = Decimal(str(technical.get("boll_lower", 0)))

            # 6. 综合评级
            macd_status = "多头" if macd_dif > macd_dea else "死叉"
            rating, rating_color = self._calculate_rating(
                profit_loss_ratio=profit_loss_ratio,
                rsi=rsi,
                pe=Decimal(str(quote["pe"])) if quote.get("pe") else None,
                macd_status=macd_status,
            )

            return StockDiagnosis(
                stock_code=stock_code,
                stock_name=stock_name,
                sector=position.get("sector", "未知"),
                current_price=current_price,
                cost_price=cost_price,
                quantity=quantity,
                market_value=market_value,
                profit_loss=profit_loss,
                profit_loss_ratio=profit_loss_ratio,
                position_ratio=position_ratio,
                today_change=Decimal(str(quote.get("pct_chg", 0))),
                volume=int(quote.get("vol", 0) * 100),  # 手 -> 股
                turnover_rate=Decimal(str(quote.get("turnover_rate", 0))),
                amplitude=Decimal(str(quote.get("amplitude", 0))),
                rsi=rsi,
                macd_dif=macd_dif,
                macd_dea=macd_dea,
                kdj_k=kdj_k,
                kdj_d=kdj_d,
                boll_upper=boll_upper,
                boll_lower=boll_lower,
                pe=Decimal(str(quote["pe"])) if quote.get("pe") else None,
                pe_ttm=Decimal(str(quote["pe_ttm"])) if quote.get("pe_ttm") else None,
                pb=Decimal(str(quote["pb"])) if quote.get("pb") else None,
                ps=Decimal(str(quote["ps"])) if quote.get("ps") else None,
                recent_prices=recent_prices,
                rating=rating,
                rating_color=rating_color,
            )

        except Exception as e:
            logger.error(f"分析股票 {stock_code} 失败: {e}", exc_info=True)
            return None

    def _calculate_rating(
        self,
        profit_loss_ratio: Decimal,
        rsi: Decimal | None,
        pe: Decimal | None,
        macd_status: str | None,
    ) -> tuple[str, str]:
        """
        计算综合评级

        Args:
            profit_loss_ratio: 盈亏比例
            rsi: RSI 指标
            pe: 市盈率
            macd_status: MACD 状态

        Returns:
            (rating, color): ("看好"/"中性"/"风险", "🟢"/"🟡"/"🔴")
        """
        risk_score = 0

        # 盈亏情况
        if profit_loss_ratio < -5:
            risk_score += 2
        elif profit_loss_ratio < 0:
            risk_score += 1

        # RSI
        if rsi and rsi > 70:
            risk_score += 2
        elif rsi and rsi > 60:
            risk_score += 1

        # PE估值
        if pe:
            if pe > 500:
                risk_score += 4
            elif pe > 100:
                risk_score += 3
            elif pe > 50:
                risk_score += 2
            elif pe > 30:
                risk_score += 1

        # MACD
        if macd_status == "死叉":
            risk_score += 2

        # 评级判断
        if risk_score >= 7:
            return "高风险区域", "🔴🔴🔴"
        elif risk_score >= 5:
            return "高风险", "🔴🔴"
        elif risk_score >= 3:
            return "风险", "🔴"
        elif risk_score >= 2:
            return "中性观望", "🟡"
        else:
            return "看好", "🟢"

    def generate_risk_assessment(
        self, overview: OverviewData, stock_diagnoses: list[StockDiagnosis]
    ) -> dict:
        """
        生成风险评估

        Args:
            overview: 持仓概览
            stock_diagnoses: 个股诊断列表

        Returns:
            dict: 风险评估结果
        """
        # 仓位风险
        if overview.position_ratio > 90:
            position_risk = "🔴🔴"
        elif overview.position_ratio > 70:
            position_risk = "🔴"
        elif overview.position_ratio > 50:
            position_risk = "🟡"
        else:
            position_risk = "🟢"

        # 技术面风险
        high_risk_count = sum(1 for d in stock_diagnoses if "🔴" in d.rating_color)
        if high_risk_count >= len(stock_diagnoses) // 2:
            technical_risk = "🔴"
        elif high_risk_count > 0:
            technical_risk = "🟡"
        else:
            technical_risk = "🟢"

        # 基本面风险（估值）
        high_pe_count = sum(1 for d in stock_diagnoses if d.pe and d.pe > 100)
        if high_pe_count >= len(stock_diagnoses) // 2:
            fundamental_risk = "🔴"
        elif high_pe_count > 0:
            fundamental_risk = "🟡"
        else:
            fundamental_risk = "🟢"

        # 整体风险
        risk_levels = [position_risk, technical_risk, fundamental_risk]
        red_count = sum(1 for r in risk_levels if "🔴" in r)
        if red_count >= 2:
            overall_risk = "🔴🔴"
        elif red_count >= 1:
            overall_risk = "🔴"
        else:
            overall_risk = "🟡"

        return {
            "overall_risk": overall_risk,
            "technical_risk": technical_risk,
            "fundamental_risk": fundamental_risk,
            "position_risk": position_risk,
        }

    def generate_suggestions(
        self, overview: OverviewData, stock_diagnoses: list[StockDiagnosis]
    ) -> dict:
        """
        生成操作建议

        Args:
            overview: 持仓概览
            stock_diagnoses: 个股诊断列表

        Returns:
            dict: 操作建议
        """
        urgent_actions = []
        medium_term_actions = []
        risk_controls = []
        warnings = []

        # 紧急操作
        for diagnosis in stock_diagnoses:
            if "🔴🔴🔴" in diagnosis.rating_color:
                urgent_actions.append(
                    f"**{diagnosis.stock_name}**: 建议立即减仓50%以上，降低高估值风险"
                )
            elif "🔴🔴" in diagnosis.rating_color:
                urgent_actions.append(f"**{diagnosis.stock_name}**: 建议减仓30%-50%，控制风险敞口")

        # 中期调整
        for diagnosis in stock_diagnoses:
            if diagnosis.profit_loss_ratio > 20:
                medium_term_actions.append(f"{diagnosis.stock_name}: 盈利丰厚，可考虑分批止盈")
            elif diagnosis.profit_loss_ratio < -10:
                medium_term_actions.append(f"{diagnosis.stock_name}: 亏损较大，关注止损位")

        # 仓位控制
        if overview.position_ratio > 90:
            risk_controls.append("总仓位降至70%以下，保留资金应对机会")
            warnings.append("当前满仓运行，无抗风险能力")
        elif overview.position_ratio > 80:
            risk_controls.append("建议保留20%-30%现金储备")

        # 止损建议
        for diagnosis in stock_diagnoses:
            if diagnosis.profit_loss_ratio < -5:
                risk_controls.append(f"{diagnosis.stock_name}: 设置严格止损位")

        # 估值警示
        for diagnosis in stock_diagnoses:
            if diagnosis.pe and diagnosis.pe > 100:
                warnings.append(f"{diagnosis.stock_name}: PE高达{diagnosis.pe:.0f}倍，估值风险极大")

        return {
            "urgent_actions": urgent_actions,
            "medium_term_actions": medium_term_actions,
            "risk_controls": risk_controls,
            "warnings": warnings,
        }
