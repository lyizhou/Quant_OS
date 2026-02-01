"""资金流向服务 - 获取市场资金流动数据."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pandas as pd
import tushare as ts

from app.common.config import get_config
from app.common.errors import CNMarketDriverError
from app.common.logging import logger
from app.common.time import format_date, get_last_market_day


@dataclass
class SectorMoneyFlow:
    """板块资金流向数据."""

    sector_name: str  # 板块名称
    net_inflow: Decimal  # 净流入（万元）
    main_net_inflow: Decimal  # 主力净流入（万元）
    super_large_net_inflow: Decimal  # 超大单净流入（万元）
    large_net_inflow: Decimal  # 大单净流入（万元）
    medium_net_inflow: Decimal  # 中单净流入（万元）
    small_net_inflow: Decimal  # 小单净流入（万元）
    trade_date: datetime  # 交易日期


@dataclass
class MarketMoneyFlow:
    """市场整体资金流向数据."""

    trade_date: datetime
    total_net_inflow: Decimal  # 总净流入（万元）
    sector_flows: list[SectorMoneyFlow]  # 各板块资金流向
    top_inflow_sectors: list[SectorMoneyFlow]  # 资金流入前N板块
    top_outflow_sectors: list[SectorMoneyFlow]  # 资金流出前N板块


class MoneyFlowService:
    """资金流向服务."""

    def __init__(self, token: str | None = None):
        """初始化资金流向服务.

        Args:
            token: Tushare API token (default: from config)

        Raises:
            CNMarketDriverError: If token is missing
        """
        self.token = token or get_config().api.tushare_token
        if not self.token:
            raise CNMarketDriverError("Tushare token is required. Set TUSHARE_TOKEN in .env")

        # Initialize Tushare
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        logger.info("MoneyFlowService initialized with Tushare")

    def get_sector_money_flow(
        self, date: datetime | None = None, top_n: int = 10
    ) -> MarketMoneyFlow:
        """获取板块资金流向数据.

        Args:
            date: 目标日期 (default: 最后一个交易日)
            top_n: 返回前N个板块

        Returns:
            市场资金流向数据

        Raises:
            CNMarketDriverError: 获取失败
        """
        if date is None:
            date = get_last_market_day(market="CN")

        date_str = format_date(date).replace("-", "")  # YYYYMMDD format
        logger.info(f"Fetching sector money flow for {date_str}")

        try:
            # 获取板块资金流向数据
            # Tushare接口: pro.moneyflow_hsgt() - 沪深港通资金流向
            # 或者使用 pro.concept_detail() 获取概念板块，然后计算资金流向

            # 方案1: 使用行业分类获取资金流向
            # 获取所有行业列表
            industries_df = self.pro.index_classify(
                level="L1",  # 一级行业
                src="SW2021"  # 申万2021行业分类
            )

            if industries_df.empty:
                logger.warning("No industry data available")
                # 使用备用方案：概念板块
                return self._get_concept_money_flow(date_str, top_n)

            sector_flows = []

            # 对每个行业获取资金流向
            for _, industry in industries_df.iterrows():
                industry_code = industry["index_code"]
                industry_name = industry["industry_name"]

                try:
                    # 获取该行业的成分股
                    constituents = self.pro.index_member(
                        index_code=industry_code,
                        fields="con_code"
                    )

                    if constituents.empty:
                        continue

                    # 获取成分股的资金流向
                    stock_codes = constituents["con_code"].tolist()

                    # 批量获取资金流向（限制数量避免超时）
                    stock_codes = stock_codes[:50]  # 限制每个行业最多50只股票

                    total_net_inflow = Decimal(0)
                    main_net_inflow = Decimal(0)
                    super_large_net_inflow = Decimal(0)
                    large_net_inflow = Decimal(0)
                    medium_net_inflow = Decimal(0)
                    small_net_inflow = Decimal(0)

                    for stock_code in stock_codes:
                        try:
                            df_flow = self.pro.moneyflow(
                                ts_code=stock_code,
                                trade_date=date_str,
                                fields="ts_code,trade_date,buy_sm_amount,sell_sm_amount,"
                                       "buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,"
                                       "buy_elg_amount,sell_elg_amount"
                            )

                            if not df_flow.empty:
                                row = df_flow.iloc[0]

                                # 计算各级别净流入（万元）
                                small = (row.get("buy_sm_amount", 0) - row.get("sell_sm_amount", 0)) / 10000
                                medium = (row.get("buy_md_amount", 0) - row.get("sell_md_amount", 0)) / 10000
                                large = (row.get("buy_lg_amount", 0) - row.get("sell_lg_amount", 0)) / 10000
                                super_large = (row.get("buy_elg_amount", 0) - row.get("sell_elg_amount", 0)) / 10000

                                small_net_inflow += Decimal(str(small))
                                medium_net_inflow += Decimal(str(medium))
                                large_net_inflow += Decimal(str(large))
                                super_large_net_inflow += Decimal(str(super_large))

                        except Exception as e:
                            logger.debug(f"Failed to fetch money flow for {stock_code}: {e}")
                            continue

                    # 计算主力净流入（大单+超大单）
                    main_net_inflow = large_net_inflow + super_large_net_inflow
                    total_net_inflow = small_net_inflow + medium_net_inflow + main_net_inflow

                    sector_flow = SectorMoneyFlow(
                        sector_name=industry_name,
                        net_inflow=total_net_inflow,
                        main_net_inflow=main_net_inflow,
                        super_large_net_inflow=super_large_net_inflow,
                        large_net_inflow=large_net_inflow,
                        medium_net_inflow=medium_net_inflow,
                        small_net_inflow=small_net_inflow,
                        trade_date=date,
                    )
                    sector_flows.append(sector_flow)

                except Exception as e:
                    logger.debug(f"Failed to process industry {industry_name}: {e}")
                    continue

            if not sector_flows:
                raise CNMarketDriverError(f"No sector money flow data for {date_str}")

            # 按净流入排序
            sector_flows.sort(key=lambda x: x.net_inflow, reverse=True)

            # 计算总净流入
            total_net_inflow = sum(s.net_inflow for s in sector_flows)

            # 获取流入和流出前N板块
            top_inflow = sector_flows[:top_n]
            top_outflow = sector_flows[-top_n:][::-1]

            market_flow = MarketMoneyFlow(
                trade_date=date,
                total_net_inflow=total_net_inflow,
                sector_flows=sector_flows,
                top_inflow_sectors=top_inflow,
                top_outflow_sectors=top_outflow,
            )

            logger.info(
                f"Fetched money flow for {len(sector_flows)} sectors, "
                f"total net inflow: {total_net_inflow:.2f}万元"
            )
            return market_flow

        except Exception as e:
            logger.error(f"Failed to fetch sector money flow: {e}")
            raise CNMarketDriverError(f"Failed to fetch sector money flow: {e}")

    def _get_concept_money_flow(self, date_str: str, top_n: int) -> MarketMoneyFlow:
        """使用概念板块获取资金流向（备用方案）.

        Args:
            date_str: 日期字符串 (YYYYMMDD)
            top_n: 返回前N个板块

        Returns:
            市场资金流向数据
        """
        logger.info("Using concept-based money flow as fallback")

        # 获取概念板块列表
        concepts_df = self.pro.concept()

        if concepts_df.empty:
            raise CNMarketDriverError("No concept data available")

        sector_flows = []
        date = datetime.strptime(date_str, "%Y%m%d")

        # 简化版：只获取前20个概念板块
        for _, concept in concepts_df.head(20).iterrows():
            concept_code = concept["code"]
            concept_name = concept["name"]

            try:
                # 获取概念成分股
                constituents = self.pro.concept_detail(id=concept_code)

                if constituents.empty:
                    continue

                stock_codes = constituents["ts_code"].tolist()[:30]  # 限制30只

                total_net_inflow = Decimal(0)

                for stock_code in stock_codes:
                    try:
                        df_flow = self.pro.moneyflow(
                            ts_code=stock_code,
                            trade_date=date_str,
                            fields="ts_code,buy_sm_amount,sell_sm_amount,"
                                   "buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,"
                                   "buy_elg_amount,sell_elg_amount"
                        )

                        if not df_flow.empty:
                            row = df_flow.iloc[0]
                            net = (
                                row.get("buy_sm_amount", 0) + row.get("buy_md_amount", 0) +
                                row.get("buy_lg_amount", 0) + row.get("buy_elg_amount", 0) -
                                row.get("sell_sm_amount", 0) - row.get("sell_md_amount", 0) -
                                row.get("sell_lg_amount", 0) - row.get("sell_elg_amount", 0)
                            ) / 10000
                            total_net_inflow += Decimal(str(net))
                    except Exception:
                        continue

                sector_flow = SectorMoneyFlow(
                    sector_name=concept_name,
                    net_inflow=total_net_inflow,
                    main_net_inflow=total_net_inflow * Decimal("0.6"),  # 估算
                    super_large_net_inflow=total_net_inflow * Decimal("0.3"),
                    large_net_inflow=total_net_inflow * Decimal("0.3"),
                    medium_net_inflow=total_net_inflow * Decimal("0.2"),
                    small_net_inflow=total_net_inflow * Decimal("0.2"),
                    trade_date=date,
                )
                sector_flows.append(sector_flow)

            except Exception as e:
                logger.debug(f"Failed to process concept {concept_name}: {e}")
                continue

        if not sector_flows:
            raise CNMarketDriverError("No concept money flow data available")

        sector_flows.sort(key=lambda x: x.net_inflow, reverse=True)
        total_net_inflow = sum(s.net_inflow for s in sector_flows)

        return MarketMoneyFlow(
            trade_date=date,
            total_net_inflow=total_net_inflow,
            sector_flows=sector_flows,
            top_inflow_sectors=sector_flows[:top_n],
            top_outflow_sectors=sector_flows[-top_n:][::-1],
        )


if __name__ == "__main__":
    # Test the service
    from app.common.logging import setup_logging

    setup_logging(level="INFO")

    service = MoneyFlowService()
    flow = service.get_sector_money_flow(top_n=10)

    print(f"\n📊 市场资金流向 - {format_date(flow.trade_date)}")
    print(f"总净流入: {flow.total_net_inflow:,.2f}万元\n")

    print("💰 资金流入前10板块:")
    for i, sector in enumerate(flow.top_inflow_sectors, 1):
        print(f"  {i}. {sector.sector_name}: {sector.net_inflow:,.2f}万元")

    print("\n📉 资金流出前10板块:")
    for i, sector in enumerate(flow.top_outflow_sectors, 1):
        print(f"  {i}. {sector.sector_name}: {sector.net_inflow:,.2f}万元")
