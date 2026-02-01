#!/usr/bin/env python3
"""板块强度计算单元测试

测试核心计算逻辑（不需要数据库）
"""

import sys
from pathlib import Path

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

from decimal import Decimal

from app.common.logging import logger, setup_logging
from app.drivers.cn_market_driver.driver import CNStockData
from app.services.sector_strength_service import SectorStrengthService


def test_strength_score_calculation():
    """测试强度得分计算"""
    setup_logging(level="INFO")
    logger.info("=== 测试强度得分计算 ===")

    service = SectorStrengthService("test_token")

    # 测试1: 看涨股票
    score1 = service.calculate_strength_score(
        avg_change_pct=5.0,  # 平均涨幅5%
        up_ratio=0.7,  # 70%上涨
        avg_volume_ratio=1.5,  # 量比1.5
        avg_turnover_rate=3.0,  # 换手率3%
        avg_money_flow_ratio=2.0,  # 资金净流入2%
    )
    logger.info(f"✓ 看涨股票强度得分: {score1:.2f}")
    assert score1 > 0, "看涨股票强度应该大于0"

    # 测试2: 看跌股票
    score2 = service.calculate_strength_score(
        avg_change_pct=-3.0,  # 平均跌幅3%
        up_ratio=0.3,  # 30%上涨
        avg_volume_ratio=0.8,  # 量比0.8
        avg_turnover_rate=1.0,  # 换手率1%
        avg_money_flow_ratio=-1.0,  # 资金净流出1%
    )
    logger.info(f"✓ 看跌股票强度得分: {score2:.2f}")
    assert score2 < score1, "看跌股票强度应该低于看涨股票"

    # 测试3: 平衡股票
    score3 = service.calculate_strength_score(
        avg_change_pct=0.0,  # 平盘
        up_ratio=0.5,  # 50%上涨
        avg_volume_ratio=1.0,  # 量比1
        avg_turnover_rate=2.0,  # 换手率2%
        avg_money_flow_ratio=0.0,  # 资金平衡
    )
    logger.info(f"✓ 平衡股票强度得分: {score3:.2f}")

    logger.info("✅ 强度得分计算测试通过")
    return True


def test_stock_strength_calculation():
    """测试个股强度计算"""
    logger.info("\n=== 测试个股强度计算 ===")

    service = SectorStrengthService("test_token")

    # 创建测试股票数据
    stock_data = CNStockData(
        symbol="000001",
        name="平安银行",
        date=None,
        open=Decimal("10.0"),
        high=Decimal("10.5"),
        low=Decimal("9.8"),
        close=Decimal("10.3"),
        volume=1000000,
        amount=Decimal("103000000"),
        change_pct=Decimal("3.0"),  # 涨幅3%
        turnover_rate=Decimal("2.5"),  # 换手率2.5%
        volume_ratio=Decimal("1.2"),  # 量比1.2
        prev_close=Decimal("10.0"),
        net_money_flow=Decimal("5000"),  # 净流入5000万元
    )

    # 计算强度
    strength = service.get_stock_strength("000001", stock_data)

    assert strength is not None, "强度计算不应返回None"
    logger.info("✓ 个股强度计算成功:")
    logger.info(f"  - 股票: {strength.name} ({strength.symbol})")
    logger.info(f"  - 涨跌幅: {strength.change_pct:.2f}%")
    logger.info(f"  - 价格: {strength.price:.2f}")
    logger.info(f"  - 量比: {strength.volume_ratio:.2f}")
    logger.info(f"  - 换手率: {strength.turnover_rate:.2f}%")
    logger.info(f"  - 主力净流入: {strength.net_money_flow:.2f}万元")
    logger.info(f"  - 资金流向占比: {strength.money_flow_ratio:.2f}%")
    logger.info(f"  - 强度得分: {strength.strength_score:.2f}")

    assert strength.change_pct == 3.0, "涨跌幅应为3%"
    assert strength.net_money_flow == 5000.0, "主力净流入应为5000万元"
    assert strength.money_flow_ratio > 0, "资金流向占比应大于0"

    logger.info("✅ 个股强度计算测试通过")
    return True


def test_money_flow_calculation():
    """测试资金流向占比计算"""
    logger.info("\n=== 测试资金流向占比计算 ===")

    service = SectorStrengthService("test_token")

    # 测试1: 净流入
    stock1 = CNStockData(
        symbol="000001",
        name="股票A",
        date=None,
        open=Decimal("10"),
        high=Decimal("10"),
        low=Decimal("10"),
        close=Decimal("10"),
        volume=1000000,
        amount=Decimal("100000000"),  # 1亿成交额
        change_pct=Decimal("2"),
        turnover_rate=Decimal("2"),
        volume_ratio=Decimal("1"),
        net_money_flow=Decimal("5000"),  # 5000万净流入
    )
    strength1 = service.get_stock_strength("000001", stock1)
    expected_ratio = (5000 * 10000 / 100000000) * 100  # 5000万/1亿 * 100
    logger.info(f"✓ 净流入占比: {strength1.money_flow_ratio:.2f}% (预期: {expected_ratio:.2f}%)")
    assert abs(strength1.money_flow_ratio - expected_ratio) < 0.01, "资金流向占比计算错误"

    # 测试2: 净流出
    stock2 = CNStockData(
        symbol="000002",
        name="股票B",
        date=None,
        open=Decimal("10"),
        high=Decimal("10"),
        low=Decimal("10"),
        close=Decimal("10"),
        volume=1000000,
        amount=Decimal("100000000"),
        change_pct=Decimal("-2"),
        turnover_rate=Decimal("2"),
        volume_ratio=Decimal("1"),
        net_money_flow=Decimal("-3000"),  # 3000万净流出
    )
    strength2 = service.get_stock_strength("000002", stock2)
    logger.info(f"✓ 净流出占比: {strength2.money_flow_ratio:.2f}%")
    assert strength2.money_flow_ratio < 0, "净流出占比应该为负"

    # 测试3: 无资金流向数据
    stock3 = CNStockData(
        symbol="000003",
        name="股票C",
        date=None,
        open=Decimal("10"),
        high=Decimal("10"),
        low=Decimal("10"),
        close=Decimal("10"),
        volume=1000000,
        amount=Decimal("100000000"),
        change_pct=Decimal("1"),
        turnover_rate=Decimal("1"),
        volume_ratio=Decimal("1"),
        net_money_flow=None,  # 无数据
    )
    strength3 = service.get_stock_strength("000003", stock3)
    logger.info(f"✓ 无资金流向数据: {strength3.money_flow_ratio:.2f}%")
    assert strength3.money_flow_ratio == 0.0, "无数据时应为0"

    logger.info("✅ 资金流向占比计算测试通过")
    return True


if __name__ == "__main__":
    success = True
    try:
        success = test_strength_score_calculation() and success
        success = test_stock_strength_calculation() and success
        success = test_money_flow_calculation() and success

        if success:
            logger.info("\n" + "=" * 50)
            logger.info("✅ 所有单元测试通过！")
            logger.info("=" * 50)
        else:
            logger.error("\n" + "=" * 50)
            logger.error("❌ 部分测试失败")
            logger.error("=" * 50)
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        success = False

    sys.exit(0 if success else 1)
