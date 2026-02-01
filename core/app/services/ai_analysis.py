"""AI Analysis Service - 使用大模型进行深度持仓分析"""

import os

import httpx
from loguru import logger


class AIAnalysisService:
    """AI 分析服务 - 生成深度投资建议"""

    def __init__(self, api_key: str | None = None, provider: str = "zhipu"):
        """初始化 AI 分析服务

        Args:
            api_key: API密钥
            provider: 服务提供商 (zhipu/openai)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY") or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning("AI API Key not found, AI analysis will be disabled")
            return

        if self.provider == "zhipu":
            self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            self.model = "glm-4-flash"
        elif self.provider == "openai":
            self.api_url = "https://api.openai.com/v1/chat/completions"
            self.model = "gpt-4o"
        else:
            self.provider = "zhipu"
            self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            self.model = "glm-4-flash"

    def analyze_portfolio(self, overview: dict, positions: list[dict]) -> str:
        """生成持仓整体分析报告"""
        if not self.api_key:
            return "AI分析服务未配置"

        try:
            # 构建提示词
            prompt = self._build_portfolio_prompt(overview, positions)

            response = self._call_llm(prompt)
            return response

        except Exception as e:
            logger.error(f"Portfolio analysis failed: {e}")
            return "AI分析生成失败，请稍后重试"

    def analyze_stock(self, stock_info: dict, technical_data: dict, news: list[dict]) -> str:
        """生成个股深度分析"""
        if not self.api_key:
            return ""

        try:
            prompt = self._build_stock_prompt(stock_info, technical_data, news)
            response = self._call_llm(prompt)
            return response
        except Exception as e:
            logger.error(f"Stock analysis failed: {e}")
            return "分析生成失败"

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM API"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _build_portfolio_prompt(self, overview: dict, positions: list[dict]) -> str:
        """构建持仓分析提示词"""
        positions_str = ""
        for p in positions[:10]:  # 限制只分析前10大持仓
            profit_emoji = "🔴" if p["profit_loss_ratio"] < 0 else "🟢"
            positions_str += f"- {p['stock_name']}({p['stock_code']}): 仓位{p['position_ratio']:.1f}%, 盈亏{p['profit_loss_ratio']:.1f}% {profit_emoji}, 行业:{p.get('sector', '未知')}\n"

        return f"""你是一位专业的投资顾问。请根据以下用户的A股持仓数据，生成一份简明扼要的诊断报告。

【持仓概览】
- 总市值: {overview["total_market_value"]:.2f}
- 总盈亏: {overview["total_profit_loss"]:.2f} ({overview["profit_loss_ratio"]:.2f}%)
- 持仓数量: {overview["position_count"]}
- 仓位占比: {overview["position_ratio"]:.1f}%

【主要持仓】
{positions_str}

请从以下维度进行分析（使用Markdown格式）：
1. **仓位配置评价**: 仓位是否过重？持股集中度如何？
2. **行业分布分析**: 是否过于集中在某些行业？（如科技、消费、周期等）
3. **盈亏归因**: 主要盈利/亏损来源是什么？
4. **调整建议**: 针对当前市场环境，给出调仓或风控建议。

风格要求：客观、专业、犀利，不要说废话，直接给出建议。字数控制在300字以内。"""

    def _build_stock_prompt(self, stock: dict, tech: dict, news: list[dict]) -> str:
        """构建个股分析提示词"""
        news_str = "\n".join([f"- {n['title']} ({n['date']})" for n in news[:3]])

        return f"""请分析股票 {stock["stock_name"]}({stock["stock_code"]})：

【基本数据】
- 现价: {stock["current_price"]}
- 盈亏: {stock["profit_loss_ratio"]:.2f}%
- 估值: PE(TTM) {stock.get("pe_ttm", "N/A")}, PB {stock.get("pb", "N/A")}

【技术指标】
- 趋势: {tech.get("trend", "未知")}
- 信号: {tech.get("recommendation", "无")}
- RSI: {tech.get("indicators", {}).get("rsi6", "N/A")}
- MACD: {"金叉" if tech.get("indicators", {}).get("macd_hist", 0) > 0 else "死叉"}

【近期新闻】
{news_str}

请给出简短点评（100字以内）：
1. 结合技术面和消息面，判断当前走势。
2. 给出明确的操作建议（持有/止盈/止损/加仓）。
"""
