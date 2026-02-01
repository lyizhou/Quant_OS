"""持仓诊断报告 Markdown 格式化服务"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any


class DiagnosisFormatter:
    """诊断报告 Markdown 格式化服务"""

    def format_report(
        self,
        overview: Any,
        stock_diagnoses: list[Any],
        risk_assessment: dict,
        suggestions: dict,
        update_date: datetime,
        portfolio_ai_analysis: str = "",
    ) -> str:
        """
        格式化完整报告

        Args:
            overview: 持仓概览数据
            stock_diagnoses: 个股诊断列表
            risk_assessment: 风险评估
            suggestions: 操作建议
            update_date: 更新日期
            portfolio_ai_analysis: AI 投资组合分析

        Returns:
            str: Markdown 格式的报告
        """
        sections = [
            self._format_header(update_date),
            self._format_overview(overview),
            self._format_portfolio_ai_analysis(portfolio_ai_analysis),
            self._format_stock_diagnoses(stock_diagnoses),
            self._format_overall_suggestions(risk_assessment, suggestions),
            self._format_footer(update_date),
        ]

        return "\n\n".join(sections)

    def _format_portfolio_ai_analysis(self, analysis: str) -> str:
        """格式化 AI 投资组合分析"""
        if not analysis:
            return ""

        return f"""## 🤖 AI 投资组合分析

{analysis}

---"""

    def _format_header(self, update_date: datetime) -> str:
        """格式化报告头部"""
        return f"""---
title: "持仓诊断"
created: {update_date.strftime("%Y-%m-%d")}
updated: {update_date.strftime("%Y-%m-%d")}
type: note
domain: finance
status: active
tags:
  - 持仓
  - 诊断
---

# 📊 持仓诊断

> 📅 **更新时间**: {update_date.strftime("%Y-%m-%d")} (最新交易日)

---"""

    def _format_overview(self, overview: Any) -> str:
        """格式化持仓概览"""
        # 风险提示
        risk_warning = ""
        if overview.position_ratio > 90:
            risk_warning = f"""
> [!warning] 风险提示
> 当前满仓运行（{overview.position_ratio:.0f}%），无可用资金，风险承受能力低，建议保留适当流动性。
"""
        elif overview.position_ratio > 80:
            risk_warning = f"""
> [!info] 提示
> 当前仓位较高（{overview.position_ratio:.0f}%），建议保留一定现金储备。
"""

        # 盈亏状态
        pl_emoji = "📈" if overview.total_profit_loss >= 0 else "📉"

        return f"""## 📈 持仓概览

| 指标 | 数值 |
|:-----|------:|
| 💰 持仓总值 | **{overview.total_market_value:,.2f} 元** |
| 📦 账户总值 | **{overview.total_account_value:,.2f} 元** |
| {pl_emoji} 总盈亏 | **{overview.total_profit_loss:+,.2f} 元** |
| 📈 盈亏比例 | **{overview.profit_loss_ratio:+.2f}%** |
| 🔢 持仓数量 | **{overview.position_count} 只** |
| ⚖️ 仓位比例 | **{overview.position_ratio:.0f}%** |
{risk_warning}
---"""

    def _format_stock_diagnoses(self, diagnoses: list[Any]) -> str:
        """格式化个股诊断"""
        sections = ["## 🔍 个股诊断"]

        for diagnosis in diagnoses:
            sections.append(self._format_single_stock(diagnosis))

        return "\n\n---\n\n".join(sections)

    def _format_single_stock(self, d: Any) -> str:
        """格式化单只股票诊断"""
        # 技术指标状态
        rsi_status = self._get_rsi_status(d.rsi)
        macd_status = "🟢 多头排列" if d.macd_dif > d.macd_dea else "🔴 死叉信号"
        kdj_status = "🟢 短期反弹" if d.kdj_k > d.kdj_d else "🟡 短期回调"
        boll_status = self._get_boll_status(d.current_price, d.boll_upper, d.boll_lower)

        # 估值状态
        pe_status = self._get_pe_status(d.pe)
        pb_status = self._get_pb_status(d.pb)

        # 近期走势表格
        recent_table = self._format_recent_prices(d.recent_prices)

        # 成交量显示（万手）
        volume_wan = d.volume / 10000

        return f"""### {self._get_sector_emoji(d.sector)} {d.stock_name} ({d.stock_code}) - {d.sector}

> [!summary] 核心判断
> {d.rating_color} **{d.rating}**

#### 💼 持仓情况

| 项目 | 数据 |
|:-----|------:|
| 现价 | **{d.current_price:.2f} 元** |
| 成本 | {d.cost_price:.2f} 元 |
| 持仓 | {d.quantity:,} 股 |
| 市值 | **{d.market_value:,.2f} 元** |
| 盈亏 | **{d.profit_loss:+,.2f} 元 ({d.profit_loss_ratio:+.2f}%)** |
| 仓位 | **{d.position_ratio:.2f}%** |

#### 📊 市场表现与技术分析

##### 市场表现
- **今日**: {d.today_change:+.2f}% ({d.current_price:.2f} 元)
- **成交量**: {volume_wan:.2f} 万手 (换手率 {d.turnover_rate:.2f}%)
- **振幅**: {d.amplitude:.2f}%

##### 技术分析
| 指标 | 数值 | 状态 |
|:-----|------|------:|
| **RSI** | {d.rsi:.2f} | {rsi_status} |
| **MACD** | DIF({d.macd_dif:.3f}) vs DEA({d.macd_dea:.3f}) | {macd_status} |
| **KDJ** | K({d.kdj_k:.2f}) vs D({d.kdj_d:.2f}) | {kdj_status} |
| **BOLL** | 收盘价 {d.current_price:.2f} / 上轨 {d.boll_upper:.2f} | {boll_status} |

##### 估值分析
- **PE**: {d.pe:.2f if d.pe else 'N/A'} ({pe_status})
- **PE TTM**: {d.pe_ttm:.2f if d.pe_ttm else 'N/A'}
- **PB**: {d.pb:.2f if d.pb else 'N/A'} ({pb_status})
- **PS**: {d.ps:.2f if d.ps else 'N/A'}

##### 近期走势
{recent_table}

#### 🤖 AI 深度点评
{d.ai_analysis if hasattr(d, "ai_analysis") and d.ai_analysis else "暂无分析"}

#### 📋 诊断结论

{self._format_diagnosis_conclusion(d)}"""

    def _format_diagnosis_conclusion(self, d: Any) -> str:
        """格式化诊断结论"""
        risk_factors = []
        positive_factors = []

        # 风险因素
        if d.profit_loss_ratio < -5:
            risk_factors.append(f"较大亏损{d.profit_loss_ratio:.2f}%，远低于成本价")
        elif d.profit_loss_ratio < 0:
            risk_factors.append(f"小幅亏损{d.profit_loss_ratio:.2f}%，低于成本价")

        if d.rsi > 70:
            risk_factors.append(f"RSI处于超买区域({d.rsi:.0f})，回调风险较大")
        elif d.rsi > 60:
            risk_factors.append(f"RSI接近超买区域({d.rsi:.0f})，短期可能回调")

        if d.pe:
            if d.pe > 500:
                risk_factors.append(f"🔴🔴🔴 PE高达{d.pe:.0f}倍，估值极度偏离基本面")
            elif d.pe > 100:
                risk_factors.append(f"PE高达{d.pe:.0f}倍，估值严重偏高")
            elif d.pe > 50:
                risk_factors.append(f"PE达{d.pe:.0f}倍，估值偏高")

        if d.macd_dif < d.macd_dea:
            risk_factors.append("MACD死叉，中期趋势转弱")

        if d.turnover_rate > 10:
            risk_factors.append(f"换手率过高({d.turnover_rate:.2f}%)，筹码不稳")

        if d.position_ratio > 50:
            risk_factors.append(f"仓位占比过高({d.position_ratio:.2f}%)，风险集中")

        # 积极因素
        if d.profit_loss_ratio > 10:
            positive_factors.append(f"盈利丰厚{d.profit_loss_ratio:+.2f}%，获利空间充足")
        elif d.profit_loss_ratio > 0:
            positive_factors.append(f"盈利{d.profit_loss_ratio:+.2f}%，高于成本价")

        if d.macd_dif > d.macd_dea:
            positive_factors.append("MACD多头排列，趋势向好")

        if d.pb and d.pb < 2:
            positive_factors.append(f"PB仅{d.pb:.2f}，估值较低")

        if d.rsi < 40:
            positive_factors.append(f"RSI处于低位({d.rsi:.0f})，有反弹空间")

        if 1 < d.turnover_rate < 5:
            positive_factors.append(f"换手率适中({d.turnover_rate:.2f}%)，交易活跃但不过度")

        # 操作建议
        if "🔴🔴🔴" in d.rating_color:
            suggestion = """- **紧急**: 建议立即减仓50%以上
- **止损位**: 严格执行，不可放松
- **警告**: 估值风险极大，不宜长期持有"""
        elif "🔴🔴" in d.rating_color:
            suggestion = """- **短期**: 建议减仓30%-50%
- **止损位**: 设置并严格执行
- **注意**: 风险较高，密切关注"""
        elif "🔴" in d.rating_color:
            suggestion = f"""- **短期**: 谨慎持有，关注压力位
- **止损位**: {d.cost_price * Decimal("0.95"):.2f}元 (成本价-5%)
- **建议**: 适当降低仓位"""
        elif "🟡" in d.rating_color:
            suggestion = f"""- **短期**: 持有观察，关注技术面变化
- **止损位**: {d.cost_price * Decimal("0.9"):.2f}元 (成本价-10%)
- **止盈位**: 根据压力位设置"""
        else:
            suggestion = """- **短期**: 可继续持有
- **止盈**: 适时兑现部分利润
- **加仓**: 回调时可考虑加仓"""

        risk_text = (
            "\n".join([f"> - {f}" for f in risk_factors]) if risk_factors else "> - 暂无明显风险"
        )
        positive_text = (
            "\n".join([f"> - {f}" for f in positive_factors])
            if positive_factors
            else "> - 暂无明显优势"
        )

        return f"""> [!danger] 风险因素
{risk_text}

> [!success] 积极因素
{positive_text}

> [!tip] 操作建议
{suggestion}"""

    def _format_overall_suggestions(self, risk: dict, suggestions: dict) -> str:
        """格式化整体建议"""
        urgent = (
            "\n".join([f"> {i + 1}. {a}" for i, a in enumerate(suggestions["urgent_actions"])])
            if suggestions["urgent_actions"]
            else "> 暂无紧急操作"
        )

        medium_term = (
            "\n".join([f"- {a}" for a in suggestions["medium_term_actions"]])
            if suggestions["medium_term_actions"]
            else "- 保持现有策略，关注市场变化"
        )

        risk_controls = (
            "\n".join([f"- {c}" for c in suggestions["risk_controls"]])
            if suggestions["risk_controls"]
            else "- 继续保持当前风控策略"
        )

        warnings = (
            "\n".join([f"> - {w}" for w in suggestions["warnings"]])
            if suggestions["warnings"]
            else "> 暂无重大风险警示"
        )

        return f"""## 💡 整体建议

### 🎯 风险评估

| 维度 | 评级 | 说明 |
|:-----|------|------|
| **整体风险** | {risk["overall_risk"]} | 综合评估 |
| **技术面** | {risk["technical_risk"]} | 技术指标分析 |
| **基本面** | {risk["fundamental_risk"]} | 估值分析 |
| **仓位管理** | {risk["position_risk"]} | 仓位比例 |

### 📝 操作建议

#### ⚡ 紧急操作 (1-3个交易日)

> [!important] 立即执行
{urgent}

#### 🔄 中期调整 (1-2周)

{medium_term}

#### 🛡️ 风险控制

{risk_controls}

---

### ⚠️ 警示

> [!caution] 风险预警
{warnings}

---

> [!note] 免责声明
> 本诊断报告仅供参考，不构成投资建议。投资有风险，决策需谨慎。"""

    def _format_footer(self, update_date: datetime) -> str:
        """格式化报告尾部"""
        return f"""---

## 📝 更新记录

| 日期 | 内容 |
|:-----|------|
| {update_date.strftime("%Y-%m-%d")} | 自动生成诊断报告 |"""

    # ========== 辅助方法 ==========

    def _get_sector_emoji(self, sector: str) -> str:
        """获取板块emoji"""
        emoji_map = {
            "银行": "🏦",
            "证券": "📈",
            "保险": "🛡️",
            "房地产": "🏠",
            "建筑": "🏗️",
            "钢铁": "⚙️",
            "煤炭": "⛏️",
            "有色": "🔩",
            "化工": "🧪",
            "石化": "🛢️",
            "汽车": "🚗",
            "机械": "🔧",
            "电力": "⚡",
            "公用": "🏭",
            "交通": "🚚",
            "物流": "🚚",
            "医药": "💊",
            "食品": "🍔",
            "农业": "🌾",
            "电子": "📱",
            "通信": "📡",
            "计算机": "💻",
            "传媒": "📺",
            "金融": "💰",
            "多元金融": "💰",
        }
        for key, emoji in emoji_map.items():
            if key in sector:
                return emoji
        return "📊"

    def _get_rsi_status(self, rsi: Decimal) -> str:
        """RSI状态"""
        if rsi > 80:
            return "🔴🔴 极度超买"
        elif rsi > 70:
            return "🔴 超买区域"
        elif rsi > 60:
            return "🟡 中性偏强"
        elif rsi > 40:
            return "🟢 中性区域"
        elif rsi > 30:
            return "🟡 中性偏弱"
        elif rsi > 20:
            return "🟢 超卖区域"
        else:
            return "🟢🟢 极度超卖"

    def _get_boll_status(self, price: Decimal, upper: Decimal, lower: Decimal) -> str:
        """布林带状态"""
        if upper == 0 or lower == 0:
            return "🟡 数据不足"

        if price > upper:
            return "🔴 突破上轨"
        elif price > upper * Decimal("0.98"):
            return "🟡 接近上轨"
        elif price < lower:
            return "🟢 跌破下轨"
        elif price < lower * Decimal("1.02"):
            return "🟡 接近下轨"
        else:
            return "🟢 中轨附近"

    def _get_pe_status(self, pe: Decimal | None) -> str:
        """PE估值状态"""
        if not pe:
            return "N/A"
        if pe > 500:
            return "🔴🔴🔴 极度偏高"
        elif pe > 100:
            return "🔴🔴 严重偏高"
        elif pe > 50:
            return "🔴 偏高"
        elif pe > 30:
            return "🟡 适中"
        elif pe > 0:
            return "🟢 合理"
        else:
            return "⚠️ 负值"

    def _get_pb_status(self, pb: Decimal | None) -> str:
        """PB估值状态"""
        if not pb:
            return "N/A"
        if pb > 10:
            return "🔴 极度偏高"
        elif pb > 5:
            return "🔴 偏高"
        elif pb > 2:
            return "🟡 适中"
        elif pb > 1:
            return "🟢 合理"
        else:
            return "🟢🟢 低估"

    def _format_recent_prices(self, prices: list[dict]) -> str:
        """格式化近期价格表格"""
        if not prices:
            return "暂无数据"

        rows = []
        for p in prices[:5]:  # 最近5天
            date = p.get("trade_date", "")
            close = p.get("close", 0)
            pct_chg = p.get("pct_chg", 0)

            # 格式化日期（如果是 YYYYMMDD 格式）
            if len(str(date)) == 8:
                date = f"{date[4:6]}/{date[6:8]}"

            rows.append(f"| {date} | {close:.2f} 元 | {pct_chg:+.2f}% |")

        return f"""| 日期 | 收盘价 | 涨跌幅 |
|:-----|--------:|-------:|
{chr(10).join(rows)}"""
