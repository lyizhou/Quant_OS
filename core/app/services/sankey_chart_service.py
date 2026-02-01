"""桑基图生成服务 - 可视化资金流向."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import plotly.graph_objects as go

from app.common.logging import logger
from app.common.time import format_date
from app.services.money_flow_service import MarketMoneyFlow, MoneyFlowService


class SankeyChartService:
    """桑基图生成服务."""

    def __init__(self):
        """初始化桑基图服务."""
        self.money_flow_service = MoneyFlowService()
        logger.info("SankeyChartService initialized")

    def generate_money_flow_sankey(
        self,
        date: datetime | None = None,
        top_n: int = 10,
        output_path: str | None = None,
    ) -> str:
        """生成资金流向桑基图.

        Args:
            date: 目标日期 (default: 最后一个交易日)
            top_n: 显示前N个板块
            output_path: 输出文件路径 (default: data/charts/money_flow_sankey_{date}.png)

        Returns:
            生成的图片文件路径

        Raises:
            Exception: 生成失败
        """
        logger.info(f"Generating money flow sankey chart for {format_date(date) if date else 'latest'}")

        # 获取资金流向数据
        market_flow = self.money_flow_service.get_sector_money_flow(date=date, top_n=top_n)

        # 生成桑基图
        fig = self._create_sankey_figure(market_flow, top_n)

        # 保存图片
        if output_path is None:
            date_str = format_date(market_flow.trade_date).replace("-", "")
            output_dir = Path("data/charts")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"money_flow_sankey_{date_str}.png")

        # 保存为PNG
        fig.write_image(output_path, width=1200, height=800, scale=2)
        logger.info(f"Sankey chart saved to {output_path}")

        return output_path

    def _create_sankey_figure(
        self, market_flow: MarketMoneyFlow, top_n: int
    ) -> go.Figure:
        """创建桑基图Figure.

        Args:
            market_flow: 市场资金流向数据
            top_n: 显示前N个板块

        Returns:
            Plotly Figure对象
        """
        # 准备桑基图数据
        # 节点: [市场总资金, 流入板块1, 流入板块2, ..., 流出板块1, 流出板块2, ...]
        # 连接: 市场总资金 -> 各板块

        nodes = ["市场总资金"]
        node_colors = ["#1f77b4"]  # 市场总资金节点颜色

        # 添加流入板块节点
        inflow_sectors = market_flow.top_inflow_sectors
        for sector in inflow_sectors:
            nodes.append(f"📈 {sector.sector_name}")
            node_colors.append("#2ca02c")  # 绿色表示流入

        # 添加流出板块节点
        outflow_sectors = market_flow.top_outflow_sectors
        for sector in outflow_sectors:
            nodes.append(f"📉 {sector.sector_name}")
            node_colors.append("#d62728")  # 红色表示流出

        # 创建连接
        sources = []
        targets = []
        values = []
        link_colors = []

        # 市场总资金 -> 流入板块
        for i, sector in enumerate(inflow_sectors, 1):
            if sector.net_inflow > 0:
                sources.append(0)  # 市场总资金
                targets.append(i)  # 流入板块
                values.append(float(sector.net_inflow))
                link_colors.append("rgba(44, 160, 44, 0.4)")  # 半透明绿色

        # 流出板块 -> 市场总资金
        outflow_start_idx = len(inflow_sectors) + 1
        for i, sector in enumerate(outflow_sectors):
            if sector.net_inflow < 0:
                sources.append(outflow_start_idx + i)  # 流出板块
                targets.append(0)  # 市场总资金
                values.append(float(abs(sector.net_inflow)))
                link_colors.append("rgba(214, 39, 40, 0.4)")  # 半透明红色

        # 创建桑基图
        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="white", width=0.5),
                        label=nodes,
                        color=node_colors,
                    ),
                    link=dict(
                        source=sources,
                        target=targets,
                        value=values,
                        color=link_colors,
                    ),
                )
            ]
        )

        # 设置标题和布局
        date_str = format_date(market_flow.trade_date)
        total_inflow = sum(s.net_inflow for s in inflow_sectors if s.net_inflow > 0)
        total_outflow = sum(abs(s.net_inflow) for s in outflow_sectors if s.net_inflow < 0)

        fig.update_layout(
            title=dict(
                text=f"📊 A股市场资金流向桑基图<br>"
                     f"<sub>{date_str} | "
                     f"流入: {total_inflow:,.0f}万元 | "
                     f"流出: {total_outflow:,.0f}万元 | "
                     f"净流入: {market_flow.total_net_inflow:,.0f}万元</sub>",
                x=0.5,
                xanchor="center",
                font=dict(size=20),
            ),
            font=dict(size=12, family="Microsoft YaHei, Arial"),
            height=800,
            margin=dict(l=20, r=20, t=100, b=20),
        )

        return fig

    def generate_detailed_sankey(
        self,
        date: datetime | None = None,
        top_n: int = 8,
        output_path: str | None = None,
    ) -> str:
        """生成详细的资金流向桑基图（包含资金类型分层）.

        Args:
            date: 目标日期
            top_n: 显示前N个板块
            output_path: 输出文件路径

        Returns:
            生成的图片文件路径
        """
        logger.info("Generating detailed money flow sankey chart")

        # 获取资金流向数据
        market_flow = self.money_flow_service.get_sector_money_flow(date=date, top_n=top_n)

        # 创建详细桑基图
        fig = self._create_detailed_sankey_figure(market_flow, top_n)

        # 保存图片
        if output_path is None:
            date_str = format_date(market_flow.trade_date).replace("-", "")
            output_dir = Path("data/charts")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"money_flow_detailed_sankey_{date_str}.png")

        fig.write_image(output_path, width=1400, height=900, scale=2)
        logger.info(f"Detailed sankey chart saved to {output_path}")

        return output_path

    def _create_detailed_sankey_figure(
        self, market_flow: MarketMoneyFlow, top_n: int
    ) -> go.Figure:
        """创建详细的桑基图（包含资金类型分层）.

        结构:
        市场总资金 -> [超大单, 大单, 中单, 小单] -> 各板块

        Args:
            market_flow: 市场资金流向数据
            top_n: 显示前N个板块

        Returns:
            Plotly Figure对象
        """
        # 节点列表
        nodes = [
            "市场总资金",
            "超大单资金",
            "大单资金",
            "中单资金",
            "小单资金",
        ]
        node_colors = [
            "#1f77b4",  # 市场总资金
            "#ff7f0e",  # 超大单
            "#2ca02c",  # 大单
            "#d62728",  # 中单
            "#9467bd",  # 小单
        ]

        # 添加板块节点
        inflow_sectors = market_flow.top_inflow_sectors[:top_n]
        for sector in inflow_sectors:
            nodes.append(f"📈 {sector.sector_name}")
            node_colors.append("#2ca02c")

        outflow_sectors = market_flow.top_outflow_sectors[:top_n]
        for sector in outflow_sectors:
            nodes.append(f"📉 {sector.sector_name}")
            node_colors.append("#d62728")

        # 创建连接
        sources = []
        targets = []
        values = []
        link_colors = []

        # 第一层: 市场总资金 -> 资金类型
        money_types = [
            ("超大单资金", 1, "#ff7f0e"),
            ("大单资金", 2, "#2ca02c"),
            ("中单资金", 3, "#d62728"),
            ("小单资金", 4, "#9467bd"),
        ]

        # 计算各类型资金总量
        total_super_large = sum(abs(s.super_large_net_inflow) for s in market_flow.sector_flows)
        total_large = sum(abs(s.large_net_inflow) for s in market_flow.sector_flows)
        total_medium = sum(abs(s.medium_net_inflow) for s in market_flow.sector_flows)
        total_small = sum(abs(s.small_net_inflow) for s in market_flow.sector_flows)

        for money_type, target_idx, color in money_types:
            total = [total_super_large, total_large, total_medium, total_small][target_idx - 1]
            if total > 0:
                sources.append(0)
                targets.append(target_idx)
                values.append(float(total))
                link_colors.append(f"rgba{tuple(list(int(color[i:i+2], 16) for i in (1, 3, 5)) + [0.3])}")

        # 第二层: 资金类型 -> 板块
        sector_start_idx = 5

        # 流入板块
        for i, sector in enumerate(inflow_sectors):
            sector_idx = sector_start_idx + i

            # 超大单 -> 板块
            if sector.super_large_net_inflow > 0:
                sources.append(1)
                targets.append(sector_idx)
                values.append(float(sector.super_large_net_inflow))
                link_colors.append("rgba(255, 127, 14, 0.3)")

            # 大单 -> 板块
            if sector.large_net_inflow > 0:
                sources.append(2)
                targets.append(sector_idx)
                values.append(float(sector.large_net_inflow))
                link_colors.append("rgba(44, 160, 44, 0.3)")

            # 中单 -> 板块
            if sector.medium_net_inflow > 0:
                sources.append(3)
                targets.append(sector_idx)
                values.append(float(sector.medium_net_inflow))
                link_colors.append("rgba(214, 39, 40, 0.3)")

            # 小单 -> 板块
            if sector.small_net_inflow > 0:
                sources.append(4)
                targets.append(sector_idx)
                values.append(float(sector.small_net_inflow))
                link_colors.append("rgba(148, 103, 189, 0.3)")

        # 流出板块
        outflow_start_idx = sector_start_idx + len(inflow_sectors)
        for i, sector in enumerate(outflow_sectors):
            sector_idx = outflow_start_idx + i

            # 板块 -> 资金类型（流出）
            if sector.super_large_net_inflow < 0:
                sources.append(sector_idx)
                targets.append(1)
                values.append(float(abs(sector.super_large_net_inflow)))
                link_colors.append("rgba(255, 127, 14, 0.3)")

            if sector.large_net_inflow < 0:
                sources.append(sector_idx)
                targets.append(2)
                values.append(float(abs(sector.large_net_inflow)))
                link_colors.append("rgba(44, 160, 44, 0.3)")

            if sector.medium_net_inflow < 0:
                sources.append(sector_idx)
                targets.append(3)
                values.append(float(abs(sector.medium_net_inflow)))
                link_colors.append("rgba(214, 39, 40, 0.3)")

            if sector.small_net_inflow < 0:
                sources.append(sector_idx)
                targets.append(4)
                values.append(float(abs(sector.small_net_inflow)))
                link_colors.append("rgba(148, 103, 189, 0.3)")

        # 创建桑基图
        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=20,
                        thickness=25,
                        line=dict(color="white", width=1),
                        label=nodes,
                        color=node_colors,
                    ),
                    link=dict(
                        source=sources,
                        target=targets,
                        value=values,
                        color=link_colors,
                    ),
                )
            ]
        )

        # 设置标题和布局
        date_str = format_date(market_flow.trade_date)
        fig.update_layout(
            title=dict(
                text=f"📊 A股市场资金流向详细桑基图<br>"
                     f"<sub>{date_str} | "
                     f"净流入: {market_flow.total_net_inflow:,.0f}万元 | "
                     f"超大单: {total_super_large:,.0f}万 | "
                     f"大单: {total_large:,.0f}万 | "
                     f"中单: {total_medium:,.0f}万 | "
                     f"小单: {total_small:,.0f}万</sub>",
                x=0.5,
                xanchor="center",
                font=dict(size=20),
            ),
            font=dict(size=11, family="Microsoft YaHei, Arial"),
            height=900,
            margin=dict(l=20, r=20, t=120, b=20),
        )

        return fig


if __name__ == "__main__":
    # Test the service
    from app.common.logging import setup_logging

    setup_logging(level="INFO")

    service = SankeyChartService()

    # 生成简单桑基图
    print("Generating simple sankey chart...")
    simple_path = service.generate_money_flow_sankey(top_n=10)
    print(f"✓ Simple sankey chart saved to: {simple_path}")

    # 生成详细桑基图
    print("\nGenerating detailed sankey chart...")
    detailed_path = service.generate_detailed_sankey(top_n=8)
    print(f"✓ Detailed sankey chart saved to: {detailed_path}")
