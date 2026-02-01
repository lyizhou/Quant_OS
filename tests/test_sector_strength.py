#!/usr/bin/env python3
"""测试板块强度计算功能

验证修复后的板块强度计算是否正常工作
"""

import sys
from pathlib import Path

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent / "core"))

import os
from pathlib import Path

from app.common.logging import logger, setup_logging
from app.data.db import get_db
from app.data.repositories.sector_repo import SectorRepository
from app.services.sector_strength_service import SectorStrengthService


def test_sector_strength():
    """测试板块强度计算"""
    setup_logging(level="INFO")

    # 获取 Tushare token
    tushare_token = os.getenv("TUSHARE_TOKEN")
    if not tushare_token:
        logger.error("TUSHARE_TOKEN environment variable not set")
        return False

    logger.info("=== 测试板块强度计算功能 ===")

    # 初始化数据库
    logger.info("初始化数据库...")
    db = get_db()
    db.initialize()

    # 运行数据库迁移
    logger.info("运行数据库迁移...")
    migrations_dir = Path(__file__).parent / "core" / "app" / "data" / "migrations"
    if migrations_dir.exists():
        migration_files = sorted(migrations_dir.glob("*.sql"))
        for migration_file in migration_files:
            logger.info(f"  运行迁移: {migration_file.name}")
            try:
                db.execute_script(str(migration_file))
            except Exception as e:
                logger.warning(f"  迁移警告: {e}")

    logger.info("✓ 数据库初始化完成")

    # 初始化服务
    service = SectorStrengthService(tushare_token)
    repo = SectorRepository()

    # 测试1: 获取所有板块
    logger.info("\n测试1: 获取所有板块")
    sectors = repo.list_all_sectors()
    logger.info(f"✓ 找到 {len(sectors)} 个板块")

    if not sectors:
        logger.warning("⚠ 数据库中没有板块数据")
        return True  # 不是错误，只是没有数据

    # 测试2: 计算单个板块强度
    logger.info(f"\n测试2: 计算板块 '{sectors[0]['name']}' 的强度")
    try:
        strength = service.calculate_sector_strength(sectors[0]["id"])
        if strength:
            logger.info("✓ 板块强度计算成功:")
            logger.info(f"  - 板块名称: {strength.sector_name}")
            logger.info(f"  - 平均涨幅: {strength.avg_change_pct}%")
            logger.info(f"  - 上涨比例: {strength.up_ratio * 100:.1f}%")
            logger.info(f"  - 总股票数: {strength.total_count}")
            logger.info(f"  - 强度得分: {strength.strength_score}")
            logger.info(f"  - Top股票数: {len(strength.top_stocks)}")
            logger.info(f"  - 子分类数: {len(strength.categories)}")
        else:
            logger.warning("⚠ 板块强度计算返回空结果（可能市场已收盘）")
    except Exception as e:
        logger.error(f"✗ 板块强度计算失败: {e}", exc_info=True)
        return False

    # 测试3: 计算所有板块强度
    logger.info("\n测试3: 计算所有板块强度排行")
    try:
        all_strengths = service.get_all_sectors_strength()
        if all_strengths:
            logger.info(f"✓ 成功计算 {len(all_strengths)} 个板块的强度")
            logger.info("\nTop 5 最强板块:")
            for i, s in enumerate(all_strengths[:5], 1):
                logger.info(
                    f"  {i}. {s.sector_name}: 强度={s.strength_score:.2f}, 涨幅={s.avg_change_pct:+.2f}%"
                )
        else:
            logger.warning("⚠ 所有板块强度计算返回空结果（可能市场已收盘）")
    except Exception as e:
        logger.error(f"✗ 所有板块强度计算失败: {e}", exc_info=True)
        return False

    # 测试4: 测试资金流向数据处理
    logger.info("\n测试4: 验证资金流向数据获取")
    try:
        strength = service.calculate_sector_strength(sectors[0]["id"])
        if strength and strength.top_stocks:
            top_stock = strength.top_stocks[0]
            logger.info("✓ Top股票资金流向数据:")
            logger.info(f"  - 股票: {top_stock.name}")
            logger.info(f"  - 主力净流入: {top_stock.net_money_flow:.2f}万元")
            logger.info(f"  - 资金流向占比: {top_stock.money_flow_ratio:.2f}%")
            logger.info(f"  - 强度得分: {top_stock.strength_score}")
        else:
            logger.warning("⚠ 无股票数据可测试资金流向")
    except Exception as e:
        logger.error(f"✗ 资金流向数据测试失败: {e}", exc_info=True)
        return False

    logger.info("\n=== ✅ 所有测试通过 ===")
    return True


if __name__ == "__main__":
    success = test_sector_strength()
    sys.exit(0 if success else 1)
