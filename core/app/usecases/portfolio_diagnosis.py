"""持仓诊断用例"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.common.logging import logger
from app.data.repositories.user_portfolio_repo import UserPortfolioRepository
from app.drivers.cn_market_driver.driver import CNMarketDriver
from app.services.ai_analysis import AIAnalysisService
from app.services.diagnosis_analyzer import DiagnosisAnalyzer
from app.services.diagnosis_formatter import DiagnosisFormatter
from app.services.news_search import get_news_search_service


class PortfolioDiagnosisUseCase:
    """持仓诊断用例"""

    def __init__(self):
        self.portfolio_repo = UserPortfolioRepository()
        self.market_driver = CNMarketDriver()
        self.analyzer = DiagnosisAnalyzer(self.market_driver)
        self.formatter = DiagnosisFormatter()
        self.ai_service = AIAnalysisService()
        self.news_service = get_news_search_service()

    def generate_diagnosis_report(
        self, user_id: str = "default", output_path: str | None = None
    ) -> str:
        """
        生成持仓诊断报告

        Args:
            user_id: 用户ID
            output_path: 输出路径（可选，默认为 data/diagnosis/）

        Returns:
            报告文件路径
        """
        logger.info(f"开始生成持仓诊断报告 - 用户: {user_id}")

        # 1. 获取持仓数据
        positions = self.portfolio_repo.list_positions_by_user(user_id)
        if not positions:
            logger.warning("未找到持仓数据")
            raise ValueError("未找到持仓数据，请先添加持仓")

        logger.info(f"✓ 获取到 {len(positions)} 只持仓")

        # 2. 分析持仓概览
        overview = self.analyzer.calculate_overview(positions)
        logger.info(
            f"✓ 持仓概览: 总值 {overview.total_market_value:.2f} 元, "
            f"盈亏 {overview.total_profit_loss:+.2f} 元 ({overview.profit_loss_ratio:+.2f}%)"
        )

        # 3. 分析每只股票
        stock_diagnoses = []
        for position in positions:
            stock_code = position.get("stock_code") or position.get("symbol")
            stock_name = (
                position.get("stock_name") or position.get("notes", "").split(":")[-1] or stock_code
            )
            logger.info(f"正在分析: {stock_name}")

            # 基础分析
            diagnosis = self.analyzer.analyze_stock(position, overview.total_market_value)

            if diagnosis:
                # 获取新闻
                logger.info("  - 搜索新闻...")
                news = self.news_service.search_stock_news(
                    stock_name=diagnosis.stock_name, stock_code=diagnosis.stock_code, max_results=3
                )

                # AI 深度分析
                logger.info("  - AI深度分析...")
                stock_info = {
                    "stock_name": diagnosis.stock_name,
                    "stock_code": diagnosis.stock_code,
                    "current_price": float(diagnosis.current_price),
                    "profit_loss_ratio": float(diagnosis.profit_loss_ratio),
                    "pe_ttm": float(diagnosis.pe_ttm) if diagnosis.pe_ttm else "N/A",
                    "pb": float(diagnosis.pb) if diagnosis.pb else "N/A",
                }

                technical_data = {
                    "trend": "未知",  # analyze_stock 没返回 trend 字符串，只返回了指标
                    "recommendation": diagnosis.rating,
                    "indicators": {
                        "rsi6": float(diagnosis.rsi) if diagnosis.rsi else None,
                        "macd_hist": float(diagnosis.macd_dif - diagnosis.macd_dea),  # 粗略计算
                    },
                }

                ai_analysis = self.ai_service.analyze_stock(stock_info, technical_data, news)
                diagnosis.ai_analysis = ai_analysis

                stock_diagnoses.append(diagnosis)
                logger.info(
                    f"✓ {diagnosis.stock_name}: {diagnosis.rating} "
                    f"({diagnosis.profit_loss:+.2f} 元, {diagnosis.profit_loss_ratio:+.2f}%)"
                )
            else:
                logger.warning(f"✗ 无法分析 {position['stock_code']}")

        if not stock_diagnoses:
            raise ValueError("无法获取任何股票的诊断数据")

        # 4. 生成整体建议
        risk_assessment = self.analyzer.generate_risk_assessment(overview, stock_diagnoses)
        suggestions = self.analyzer.generate_suggestions(overview, stock_diagnoses)

        # AI 整体持仓分析
        logger.info("正在生成AI投资组合分析...")
        # 准备数据
        portfolio_positions = []
        for d in stock_diagnoses:
            portfolio_positions.append(
                {
                    "stock_name": d.stock_name,
                    "stock_code": d.stock_code,
                    "position_ratio": float(d.position_ratio),
                    "profit_loss_ratio": float(d.profit_loss_ratio),
                    "sector": d.sector,
                }
            )

        overview_dict = {
            "total_market_value": float(overview.total_market_value),
            "total_profit_loss": float(overview.total_profit_loss),
            "profit_loss_ratio": float(overview.profit_loss_ratio),
            "position_count": overview.position_count,
            "position_ratio": float(overview.position_ratio),
        }

        portfolio_ai_analysis = self.ai_service.analyze_portfolio(
            overview_dict, portfolio_positions
        )

        logger.info(
            f"✓ 风险评估: 整体 {risk_assessment['overall_risk']}, "
            f"技术面 {risk_assessment['technical_risk']}, "
            f"基本面 {risk_assessment['fundamental_risk']}, "
            f"仓位 {risk_assessment['position_risk']}"
        )

        # 5. 格式化为 Markdown
        markdown_content = self.formatter.format_report(
            overview=overview,
            stock_diagnoses=stock_diagnoses,
            risk_assessment=risk_assessment,
            suggestions=suggestions,
            update_date=datetime.now(),
            portfolio_ai_analysis=portfolio_ai_analysis,
        )

        # 6. 保存报告
        if output_path is None:
            output_dir = Path("data/diagnosis")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"持仓诊断_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(markdown_content, encoding="utf-8")
        logger.info(f"✓ 诊断报告已生成: {output_path}")

        return str(output_path)

    def get_diagnosis_summary(self, user_id: str = "default") -> dict:
        """
        获取诊断摘要（用于 Telegram 快速展示）

        Args:
            user_id: 用户ID

        Returns:
            dict: 诊断摘要信息
        """
        positions = self.portfolio_repo.list_positions_by_user(user_id)
        if not positions:
            return {
                "status": "empty",
                "message": "暂无持仓数据",
            }

        overview = self.analyzer.calculate_overview(positions)

        # 简要分析
        stock_diagnoses = []
        for position in positions:
            diagnosis = self.analyzer.analyze_stock(position, overview.total_market_value)
            if diagnosis:
                stock_diagnoses.append(diagnosis)

        risk_assessment = self.analyzer.generate_risk_assessment(overview, stock_diagnoses)

        # 统计风险股票
        high_risk_stocks = [d for d in stock_diagnoses if "🔴" in d.rating_color]
        profit_stocks = [d for d in stock_diagnoses if d.profit_loss > 0]
        loss_stocks = [d for d in stock_diagnoses if d.profit_loss < 0]

        return {
            "status": "ok",
            "overview": {
                "total_value": float(overview.total_market_value),
                "profit_loss": float(overview.total_profit_loss),
                "profit_loss_ratio": float(overview.profit_loss_ratio),
                "position_count": overview.position_count,
                "position_ratio": float(overview.position_ratio),
            },
            "risk": {
                "overall": risk_assessment["overall_risk"],
                "technical": risk_assessment["technical_risk"],
                "fundamental": risk_assessment["fundamental_risk"],
                "position": risk_assessment["position_risk"],
            },
            "stocks": {
                "high_risk_count": len(high_risk_stocks),
                "profit_count": len(profit_stocks),
                "loss_count": len(loss_stocks),
            },
            "high_risk_stocks": [
                {
                    "code": d.stock_code,
                    "name": d.stock_name,
                    "rating": d.rating,
                    "profit_loss_ratio": float(d.profit_loss_ratio),
                }
                for d in high_risk_stocks
            ],
        }
