"""Technical Analysis Module for CN Market."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt

from app.common.logging import logger

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


@dataclass
class TechnicalIndicators:
    """技术指标数据."""

    # 移动平均线
    ma5: float | None = None
    ma10: float | None = None
    ma20: float | None = None
    ma60: float | None = None

    # 指数移动平均线
    ema5: float | None = None
    ema12: float | None = None
    ema26: float | None = None

    # MACD
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None

    # RSI
    rsi6: float | None = None
    rsi12: float | None = None
    rsi24: float | None = None

    # 布林带
    boll_upper: float | None = None
    boll_middle: float | None = None
    boll_lower: float | None = None

    # KDJ
    k: float | None = None
    d: float | None = None
    j: float | None = None


@dataclass
class TechnicalAnalysis:
    """技术分析结果."""

    symbol: str
    name: str
    indicators: TechnicalIndicators
    trend: str  # 上升、下降、震荡
    strength: str  # 强、中、弱
    support: float | None = None
    resistance: float | None = None
    recommendation: str = ""  # 买入、持有、卖出
    analysis_text: str = ""


class TechnicalAnalyzer:
    """技术分析器."""

    def __init__(self):
        """初始化技术分析器."""

    def calculate_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """计算技术指标.

        Args:
            df: 历史数据 DataFrame (需要包含 close, open, high, low 列)

        Returns:
            TechnicalIndicators 数据
        """
        if df.empty or len(df) < 5:
            return TechnicalIndicators()

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        indicators = TechnicalIndicators()

        try:
            # 移动平均线
            indicators.ma5 = close.rolling(window=5).mean().iloc[-1] if len(df) >= 5 else None
            indicators.ma10 = close.rolling(window=10).mean().iloc[-1] if len(df) >= 10 else None
            indicators.ma20 = close.rolling(window=20).mean().iloc[-1] if len(df) >= 20 else None
            indicators.ma60 = close.rolling(window=60).mean().iloc[-1] if len(df) >= 60 else None

            # 指数移动平均线
            indicators.ema5 = close.ewm(span=5, adjust=False).mean().iloc[-1]
            indicators.ema12 = close.ewm(span=12, adjust=False).mean().iloc[-1]
            indicators.ema26 = close.ewm(span=26, adjust=False).mean().iloc[-1]

            # MACD
            if indicators.ema12 and indicators.ema26:
                ema12_series = close.ewm(span=12, adjust=False).mean()
                ema26_series = close.ewm(span=26, adjust=False).mean()
                macd_line = ema12_series - ema26_series
                signal_line = macd_line.ewm(span=9, adjust=False).mean()

                indicators.macd = macd_line.iloc[-1]
                indicators.macd_signal = signal_line.iloc[-1]
                indicators.macd_hist = indicators.macd - indicators.macd_signal

            # RSI (Relative Strength Index)
            if len(df) >= 7:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
                rs = gain / loss
                indicators.rsi6 = 100 - (100 / (1 + rs)).iloc[-1]

            if len(df) >= 13:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=12).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=12).mean()
                rs = gain / loss
                indicators.rsi12 = 100 - (100 / (1 + rs)).iloc[-1]

            if len(df) >= 25:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=24).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=24).mean()
                rs = gain / loss
                indicators.rsi24 = 100 - (100 / (1 + rs)).iloc[-1]

            # 布林带
            if len(df) >= 20:
                boll_middle = close.rolling(window=20).mean()
                boll_std = close.rolling(window=20).std()
                indicators.boll_middle = boll_middle.iloc[-1]
                indicators.boll_upper = (boll_middle + 2 * boll_std).iloc[-1]
                indicators.boll_lower = (boll_middle - 2 * boll_std).iloc[-1]

            # KDJ
            if len(df) >= 9:
                low_min = low.rolling(window=9).min()
                high_max = high.rolling(window=9).max()
                rsv = (close - low_min) / (high_max - low_min) * 100

                k_series = rsv.ewm(com=2, adjust=False).mean()
                d_series = k_series.ewm(com=2, adjust=False).mean()

                indicators.k = k_series.iloc[-1]
                indicators.d = d_series.iloc[-1]
                indicators.j = 3 * indicators.k - 2 * indicators.d

        except Exception as e:
            logger.warning(f"Error calculating indicators: {e}")

        return indicators

    def analyze_trend(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> tuple[str, str]:
        """分析趋势.

        Returns:
            (趋势, 强度) - (上升/下降/震荡, 强/中/弱)
        """
        if df.empty or len(df) < 10:
            return "未知", "弱"

        close = df["close"].astype(float)
        current_price = close.iloc[-1]

        # 计算趋势
        trend = "震荡"
        strength = "中"

        if indicators.ma5 and indicators.ma10:
            # 短期均线排列
            if indicators.ma5 > indicators.ma10 > indicators.ma20:
                trend = "上升"
            elif indicators.ma5 < indicators.ma10 < indicators.ma20:
                trend = "下降"

        # 判断强度
        if indicators.ma60:
            if current_price > indicators.ma60:
                if indicators.ma5 > indicators.ma20:
                    strength = "强"
                else:
                    strength = "中"
            else:
                strength = "弱"

        # 使用价格变化率确认
        if len(df) >= 10:
            recent_change = (current_price - close.iloc[-10]) / close.iloc[-10] * 100
            if recent_change > 5:
                strength = "强"
            elif recent_change < -5:
                strength = "弱"

        return trend, strength

    def find_support_resistance(
        self, df: pd.DataFrame, current_price: float
    ) -> tuple[float | None, float | None]:
        """寻找支撑位和阻力位.

        Returns:
            (支撑位, 阻力位)
        """
        if df.empty or len(df) < 20:
            return None, None

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        # 使用最近20天的最高价和最低价
        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()

        # 阻力位：最近的显著高点
        resistance = recent_high if recent_high > current_price else None

        # 支撑位：最近的显著低点
        support = recent_low if recent_low < current_price else None

        # 使用布林带辅助判断
        return support, resistance

    def generate_recommendation(
        self, indicators: TechnicalIndicators, trend: str, strength: str, current_price: float
    ) -> str:
        """生成操作建议.

        Returns:
            买入/持有/卖出
        """
        score = 0

        # MACD 分析
        if indicators.macd_hist:
            if indicators.macd_hist > 0:
                score += 1
            else:
                score -= 1

        # RSI 分析
        if indicators.rsi6:
            if indicators.rsi6 < 30:
                score += 2  # 超卖，买入信号
            elif indicators.rsi6 > 70:
                score -= 2  # 超买，卖出信号
            elif indicators.rsi6 < 40:
                score += 1
            elif indicators.rsi6 > 60:
                score -= 1

        # KDJ 分析
        if indicators.k and indicators.d:
            if indicators.k < 20 and indicators.d < 20:
                score += 1  # 低位
            elif indicators.k > 80 and indicators.d > 80:
                score -= 1  # 高位
            if indicators.k > indicators.d:
                score += 1
            else:
                score -= 1

        # 均线排列
        if indicators.ma5 and indicators.ma10 and indicators.ma20:
            if indicators.ma5 > indicators.ma10 > indicators.ma20:
                score += 2
            elif indicators.ma5 < indicators.ma10 < indicators.ma20:
                score -= 2

        # 布林带
        if indicators.boll_lower and current_price < indicators.boll_lower:
            score += 1  # 价格在下轨下方，可能反弹
        if indicators.boll_upper and current_price > indicators.boll_upper:
            score -= 1  # 价格在上轨上方，可能回调

        # 趋势加分
        if trend == "上升":
            score += 1
        elif trend == "下降":
            score -= 1

        # 强度加分
        if strength == "强":
            score += 1
        elif strength == "弱":
            score -= 1

        # 根据分数给出建议
        if score >= 4:
            return "买入"
        elif score >= 1:
            return "持有偏多"
        elif score >= -1:
            return "持有"
        elif score >= -4:
            return "持有偏空"
        else:
            return "卖出"

    def generate_analysis_text(
        self,
        indicators: TechnicalIndicators,
        trend: str,
        strength: str,
        support: float | None,
        resistance: float | None,
        recommendation: str,
    ) -> str:
        """生成分析文本."""
        lines = ["📊 技术分析:\n"]

        # 均线分析
        if indicators.ma5 and indicators.ma10:
            ma_trend = "多头" if indicators.ma5 > indicators.ma10 else "空头"
            lines.append(f"📈 均线: {ma_trend}排列")
            if indicators.ma20:
                lines.append(
                    f"   MA5: ¥{indicators.ma5:.2f} | MA10: ¥{indicators.ma10:.2f} | MA20: ¥{indicators.ma20:.2f}"
                )

        # MACD
        if indicators.macd is not None:
            macd_signal = "金叉" if indicators.macd > indicators.macd_signal else "死叉"
            macd_trend = "↑" if indicators.macd_hist > 0 else "↓"
            lines.append(f"📊 MACD: {macd_signal} ({macd_trend})")

        # KDJ
        if indicators.k is not None:
            kdj_signal = "超买" if indicators.k > 80 else "超卖" if indicators.k < 20 else "正常"
            kdj_trend = "↑" if indicators.k > indicators.d else "↓"
            lines.append(f"🔸 KDJ: {kdj_signal} ({kdj_trend}) K={indicators.k:.1f}")

        # RSI
        if indicators.rsi6 is not None:
            rsi_status = (
                "超买" if indicators.rsi6 > 70 else "超卖" if indicators.rsi6 < 30 else "正常"
            )
            lines.append(f"📉 RSI(6): {rsi_status} ({indicators.rsi6:.1f})")

        # 布林带
        if indicators.boll_upper and indicators.boll_lower:
            lines.append(
                f"📊 布林带: 上¥{indicators.boll_upper:.2f} / 中¥{indicators.boll_middle:.2f} / 下¥{indicators.boll_lower:.2f}"
            )

        # 趋势和强度
        lines.append(f"\n🎯 趋势: {trend} | 强度: {strength}")

        # 支撑和阻力
        if support and resistance:
            lines.append(f"💪 支撑: ¥{support:.2f} | 阻力: ¥{resistance:.2f}")

        # 建议
        emoji_map = {
            "买入": "🟢",
            "持有偏多": "🟢",
            "持有": "🟡",
            "持有偏空": "🟠",
            "卖出": "🔴",
        }
        lines.append(f"\n{emoji_map.get(recommendation, '⚪')} 建议: {recommendation}")

        return "\n".join(lines)

    def create_chart(
        self,
        df: pd.DataFrame,
        symbol: str,
        name: str,
        save_path: str | Path,
        support: float = None,
        resistance: float = None,
    ) -> None:
        """生成蜡烛图、成交量和MACD图.

        Args:
            df: 历史数据 DataFrame
            symbol: 股票代码
            name: 股票名称
            save_path: 保存路径
            support: 支撑位价格
            resistance: 阻力位价格
        """
        if df.empty:
            logger.warning(f"Empty data for {symbol}, cannot create chart")
            return

        # 准备数据
        df = df.copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
        df = df.sort_values("trade_date")
        # 重置索引以便绘制
        df = df.reset_index(drop=True)

        # 创建图表 - 3个子图
        fig, (ax1, ax3, ax2) = plt.subplots(
            3, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [3, 1, 1]}
        )
        fig.suptitle(f"{name} ({symbol}) - 120日K线图", fontsize=14, fontweight="bold")

        # 蜡烛图颜色
        up_color = "#FF4136"  # 上涨红色
        down_color = "#00A65A"  # 下跌绿色

        # 绘制蜡烛图 - 使用整数索引作为x轴
        for i, row in df.iterrows():
            open_price = row["open"]
            close = row["close"]
            high = row["high"]
            low = row["low"]

            # 确定颜色
            color = up_color if close >= open_price else down_color

            # 绘制影线
            ax1.plot([i, i], [low, high], color=color, linewidth=1)

            # 绘制实体
            height = abs(close - open_price)
            bottom = min(open_price, close)
            ax1.bar(
                i, height, bottom=bottom, width=0.6, color=color, edgecolor="black", linewidth=0.5
            )

        # 绘制移动平均线
        close = df["close"].astype(float)
        x_range = range(len(df))

        if len(df) >= 5:
            ma5 = close.rolling(window=5).mean()
            ax1.plot(x_range, ma5, label="MA5", color="#FFD700", linewidth=1.2, alpha=0.9)
        if len(df) >= 10:
            ma10 = close.rolling(window=10).mean()
            ax1.plot(x_range, ma10, label="MA10", color="#00CED1", linewidth=1.2, alpha=0.9)
        if len(df) >= 20:
            ma20 = close.rolling(window=20).mean()
            ax1.plot(x_range, ma20, label="MA20", color="#FF69B4", linewidth=1.2, alpha=0.9)

        # 绘制布林带
        if len(df) >= 20:
            boll_middle = close.rolling(window=20).mean()
            boll_std = close.rolling(window=20).std()
            boll_upper = boll_middle + 2 * boll_std
            boll_lower = boll_middle - 2 * boll_std

            # 布林带上轨
            ax1.plot(
                x_range,
                boll_upper,
                label="布林上轨",
                color="#9370DB",
                linewidth=1,
                alpha=0.7,
                linestyle="--",
            )
            # 布林带下轨
            ax1.plot(
                x_range,
                boll_lower,
                label="布林下轨",
                color="#9370DB",
                linewidth=1,
                alpha=0.7,
                linestyle="--",
            )

            # 填充布林带区域
            ax1.fill_between(x_range, boll_lower, boll_upper, alpha=0.1, color="#9370DB")

        # 绘制支撑位和阻力位
        if support:
            ax1.axhline(
                y=support,
                color="green",
                linestyle="-.",
                linewidth=1.5,
                alpha=0.7,
                label=f"支撑 {support:.2f}元",
            )
        if resistance:
            ax1.axhline(
                y=resistance,
                color="red",
                linestyle="-.",
                linewidth=1.5,
                alpha=0.7,
                label=f"阻力 {resistance:.2f}元",
            )

        ax1.set_ylabel("价格 (元)", fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="upper left", fontsize=7, ncol=3)
        ax1.set_xticklabels([])  # 隐藏x轴标签

        # 绘制MACD
        if len(df) >= 26:
            # 计算MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_hist = macd_line - signal_line

            # 绘制柱状图
            colors_macd = [up_color if v > 0 else down_color for v in macd_hist]
            ax3.bar(x_range, macd_hist, color=colors_macd, alpha=0.7, linewidth=0.5)

            # 绘制MACD线
            ax3.plot(x_range, macd_line, label="MACD", color="#FFD700", linewidth=1.2)
            ax3.plot(x_range, signal_line, label="Signal", color="#00CED1", linewidth=1.2)

            ax3.set_ylabel("MACD", fontsize=10)
            ax3.axhline(y=0, color="gray", linestyle="-", linewidth=0.5, alpha=0.5)
            ax3.grid(True, alpha=0.3)
            ax3.legend(loc="upper left", fontsize=7)
            ax3.set_xticklabels([])  # 隐藏x轴标签

        # 绘制成交量
        colors = [
            up_color if row["close"] >= row["open"] else down_color for _, row in df.iterrows()
        ]
        ax2.bar(
            x_range, df["vol"] / 10000, color=colors, alpha=0.7, edgecolor="black", linewidth=0.5
        )
        ax2.set_ylabel("成交量 (万手)", fontsize=10)
        ax2.set_xlabel("日期", fontsize=10)
        ax2.grid(True, alpha=0.3)

        # 设置x轴刻度 - 使用日期标签
        # 选择约8-10个日期作为刻度
        n_ticks = min(10, len(df))
        tick_indices = [int(i * len(df) / n_ticks) for i in range(n_ticks)]
        tick_labels = [df.iloc[i]["trade_date"].strftime("%m-%d") for i in tick_indices]
        ax2.set_xticks(tick_indices)
        ax2.set_xticklabels(tick_labels, rotation=0)

        # 调整布局
        plt.tight_layout()

        # 保存图表
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches="tight")
        plt.close()

        logger.info(f"Chart saved to {save_path}")

    def analyze(self, df: pd.DataFrame, symbol: str, name: str) -> TechnicalAnalysis:
        """完整技术分析.

        Args:
            df: 历史数据 DataFrame
            symbol: 股票代码
            name: 股票名称

        Returns:
            TechnicalAnalysis 分析结果
        """
        if df.empty:
            return TechnicalAnalysis(
                symbol=symbol,
                name=name,
                indicators=TechnicalIndicators(),
                trend="未知",
                strength="弱",
                analysis_text="数据不足，无法分析",
            )

        # 计算指标
        indicators = self.calculate_indicators(df)

        # 分析趋势
        trend, strength = self.analyze_trend(df, indicators)

        # 找支撑阻力
        current_price = float(df["close"].iloc[-1])
        support, resistance = self.find_support_resistance(df, current_price)

        # 生成建议
        recommendation = self.generate_recommendation(indicators, trend, strength, current_price)

        # 生成分析文本
        analysis_text = self.generate_analysis_text(
            indicators, trend, strength, support, resistance, recommendation
        )

        return TechnicalAnalysis(
            symbol=symbol,
            name=name,
            indicators=indicators,
            trend=trend,
            strength=strength,
            support=support,
            resistance=resistance,
            recommendation=recommendation,
            analysis_text=analysis_text,
        )


# 便捷函数
def analyze_stock(symbol: str, name: str, df: pd.DataFrame) -> TechnicalAnalysis:
    """分析股票技术面 (便捷函数)."""
    analyzer = TechnicalAnalyzer()
    return analyzer.analyze(df, symbol, name)
