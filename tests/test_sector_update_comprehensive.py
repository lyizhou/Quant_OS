#!/usr/bin/env python3
"""题材库数据更新功能 - 综合测试脚本

测试内容：
1. 板块强度计算服务 (SectorStrengthService)
2. 板块强度缓存服务 (SectorStrengthCacheService)
3. 题材库同步服务 (SectorSyncService)
4. 数据更新脚本 (update_sector_strength.py)
"""

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from app.common.logging import logger, setup_logging
from app.data.db import get_db, initialize_db


class TestResults:
    """测试结果收集器"""

    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = []
        self.bugs = []

    def add_test(self, name: str, status: str, message: str = "", details: str = ""):
        """添加测试结果"""
        self.tests.append({
            "name": name,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now()
        })

        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1

    def add_warning(self, category: str, message: str):
        """添加警告"""
        self.warnings.append({
            "category": category,
            "message": message,
            "timestamp": datetime.now()
        })

    def add_bug(self, category: str, severity: str, description: str, location: str):
        """添加发现的bug"""
        self.bugs.append({
            "category": category,
            "severity": severity,
            "description": description,
            "location": location,
            "timestamp": datetime.now()
        })

    def print_summary(self):
        """打印测试摘要"""
        logger.info("=" * 80)
        logger.info("测试摘要")
        logger.info("=" * 80)
        logger.info(f"总测试数: {len(self.tests)}")
        logger.info(f"✅ 通过: {self.passed}")
        logger.info(f"❌ 失败: {self.failed}")
        logger.info(f"⚠️  警告: {len(self.warnings)}")
        logger.info(f"🐛 发现Bug: {len(self.bugs)}")
        logger.info("=" * 80)


results = TestResults()


def test_database_schema():
    """测试1: 数据库表结构检查"""
    logger.info("\n" + "=" * 80)
    logger.info("测试1: 数据库表结构检查")
    logger.info("=" * 80)

    try:
        db = get_db()
        conn = db.get_connection()

        # 检查必需的表是否存在
        required_tables = [
            "sectors",
            "sector_categories",
            "stock_sector_mapping",
            "sector_strength_results",
            "sector_strength_history",
            "sector_sync_log",
            "sector_change_history",
            "stock_daily_data",
        ]

        for table in required_tables:
            try:
                result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = result[0]
                logger.info(f"  ✓ 表 {table} 存在，记录数: {count}")
                results.add_test(f"表存在检查: {table}", "PASS", f"记录数: {count}")
            except Exception as e:
                logger.error(f"  ✗ 表 {table} 不存在或无法访问: {e}")
                results.add_test(f"表存在检查: {table}", "FAIL", str(e))
                results.add_bug(
                    "数据库结构",
                    "HIGH",
                    f"表 {table} 不存在或无法访问",
                    "数据库迁移文件"
                )

        # 检查序列是否存在
        sequences = [
            "sectors_id_seq",
            "sector_categories_id_seq",
            "stock_sector_mapping_id_seq",
            "sector_strength_results_id_seq",
            "sector_strength_history_id_seq",
        ]

        for seq in sequences:
            try:
                result = conn.execute(f"SELECT nextval('{seq}')").fetchone()
                logger.info(f"  ✓ 序列 {seq} 存在")
                results.add_test(f"序列检查: {seq}", "PASS")
            except Exception as e:
                logger.error(f"  ✗ 序列 {seq} 不存在: {e}")
                results.add_test(f"序列检查: {seq}", "FAIL", str(e))

        db.return_connection(conn)
        return True

    except Exception as e:
        logger.error(f"数据库检查失败: {e}", exc_info=True)
        results.add_test("数据库连接", "FAIL", str(e))
        return False


def test_sector_repository():
    """测试2: SectorRepository 基础功能"""
    logger.info("\n" + "=" * 80)
    logger.info("测试2: SectorRepository 基础功能")
    logger.info("=" * 80)

    try:
        from app.data.repositories.sector_repo import SectorRepository

        repo = SectorRepository()

        # 测试获取所有板块
        sectors = repo.list_all_sectors()
        logger.info(f"  ✓ 获取到 {len(sectors)} 个板块")
        results.add_test("获取所有板块", "PASS", f"板块数: {len(sectors)}")

        if len(sectors) == 0:
            results.add_warning("数据完整性", "数据库中没有板块数据")
            logger.warning("  ⚠️  数据库中没有板块数据")
            return False

        # 测试获取单个板块
        first_sector = sectors[0]
        sector_id = first_sector["id"]
        sector = repo.get_sector_by_id(sector_id)

        if sector:
            logger.info(f"  ✓ 成功获取板块: {sector['name']}")
            results.add_test("获取单个板块", "PASS", f"板块名: {sector['name']}")
        else:
            logger.error(f"  ✗ 无法获取板块 ID: {sector_id}")
            results.add_test("获取单个板块", "FAIL")
            results.add_bug("Repository", "MEDIUM", "get_sector_by_id 返回 None", "sector_repo.py")

        # 测试获取板块股票
        stocks = repo.get_stocks_by_sector(sector_id)
        logger.info(f"  ✓ 板块 '{first_sector['name']}' 包含 {len(stocks)} 只股票")
        results.add_test("获取板块股票", "PASS", f"股票数: {len(stocks)}")

        # 检查股票代码格式
        if stocks:
            invalid_symbols = []
            for stock in stocks[:10]:  # 检查前10只
                symbol = stock["symbol"]
                if not symbol or len(symbol) != 6 or not symbol.isdigit():
                    invalid_symbols.append(symbol)

            if invalid_symbols:
                logger.error(f"  ✗ 发现无效股票代码: {invalid_symbols}")
                results.add_test("股票代码格式检查", "FAIL", f"无效代码: {invalid_symbols}")
                results.add_bug(
                    "数据质量",
                    "HIGH",
                    f"股票代码格式错误: {invalid_symbols}",
                    "stock_sector_mapping 表"
                )
            else:
                logger.info(f"  ✓ 股票代码格式正确（检查了前10只）")
                results.add_test("股票代码格式检查", "PASS")

        return True

    except Exception as e:
        logger.error(f"Repository 测试失败: {e}", exc_info=True)
        results.add_test("SectorRepository", "FAIL", str(e))
        return False


def test_market_driver():
    """测试3: CNMarketDriver 数据获取"""
    logger.info("\n" + "=" * 80)
    logger.info("测试3: CNMarketDriver 数据获取")
    logger.info("=" * 80)

    try:
        from app.drivers.cn_market_driver.driver import CNMarketDriver
        from app.common.time import get_last_market_day

        tushare_token = os.getenv("TUSHARE_TOKEN")
        if not tushare_token:
            logger.error("  ✗ TUSHARE_TOKEN 环境变量未设置")
            results.add_test("Tushare配置", "FAIL", "环境变量未设置")
            return False

        driver = CNMarketDriver(tushare_token)

        # 获取最近交易日
        last_market_day = get_last_market_day(market="CN")
        logger.info(f"  ✓ 最近交易日: {last_market_day}")
        results.add_test("获取交易日", "PASS", f"日期: {last_market_day}")

        # 测试获取单只股票数据
        test_symbols = ["000001", "600000", "000858"]  # 平安银行、浦发银行、五粮液

        for symbol in test_symbols:
            try:
                stock_data_list = driver.fetch_stock_data([symbol], last_market_day)

                if stock_data_list and len(stock_data_list) > 0:
                    stock_data = stock_data_list[0]
                    logger.info(
                        f"  ✓ {symbol} ({stock_data.name}): "
                        f"涨跌幅 {stock_data.change_pct}%, 价格 {stock_data.close}"
                    )
                    results.add_test(f"获取股票数据: {symbol}", "PASS")
                else:
                    logger.warning(f"  ⚠️  {symbol}: 无数据")
                    results.add_test(f"获取股票数据: {symbol}", "FAIL", "无数据返回")
                    results.add_warning("数据可用性", f"{symbol} 在 {last_market_day} 无数据")

            except Exception as e:
                logger.error(f"  ✗ 获取 {symbol} 数据失败: {e}")
                results.add_test(f"获取股票数据: {symbol}", "FAIL", str(e))

        # 测试批量获取
        logger.info(f"\n  测试批量获取 {len(test_symbols)} 只股票...")
        batch_data = driver.fetch_stock_data(test_symbols, last_market_day)
        logger.info(f"  ✓ 批量获取成功，返回 {len(batch_data)} 条数据")
        results.add_test("批量获取股票数据", "PASS", f"获取 {len(batch_data)}/{len(test_symbols)} 条")

        if len(batch_data) < len(test_symbols):
            results.add_warning(
                "数据完整性",
                f"批量获取数据不完整: {len(batch_data)}/{len(test_symbols)}"
            )

        return True

    except Exception as e:
        logger.error(f"MarketDriver 测试失败: {e}", exc_info=True)
        results.add_test("CNMarketDriver", "FAIL", str(e))
        return False


def test_sector_strength_calculation():
    """测试4: 板块强度计算"""
    logger.info("\n" + "=" * 80)
    logger.info("测试4: 板块强度计算")
    logger.info("=" * 80)

    try:
        from app.services.sector_strength_service import SectorStrengthService
        from app.data.repositories.sector_repo import SectorRepository

        tushare_token = os.getenv("TUSHARE_TOKEN")
        if not tushare_token:
            logger.error("  ✗ TUSHARE_TOKEN 环境变量未设置")
            return False

        service = SectorStrengthService(tushare_token)
        repo = SectorRepository()

        # 获取一个板块进行测试
        sectors = repo.list_all_sectors()
        if not sectors:
            logger.error("  ✗ 没有可用的板块")
            results.add_test("板块强度计算", "FAIL", "没有板块数据")
            return False

        test_sector = sectors[0]
        sector_id = test_sector["id"]
        sector_name = test_sector["name"]

        logger.info(f"\n  测试板块: {sector_name} (ID: {sector_id})")

        # 计算板块强度
        strength = service.calculate_sector_strength(sector_id)

        if strength:
            logger.info(f"  ✓ 板块强度计算成功")
            logger.info(f"    - 板块名称: {strength.sector_name}")
            logger.info(f"    - 股票总数: {strength.total_count}")
            logger.info(f"    - 上涨股票: {strength.up_count}")
            logger.info(f"    - 下跌股票: {strength.down_count}")
            logger.info(f"    - 上涨比例: {strength.up_ratio * 100:.1f}%")
            logger.info(f"    - 平均涨跌: {strength.avg_change_pct:.2f}%")
            logger.info(f"    - 平均量比: {strength.avg_volume_ratio:.2f}")
            logger.info(f"    - 平均换手: {strength.avg_turnover_rate:.2f}%")
            logger.info(f"    - 资金流入: {strength.total_net_money_flow:.2f}万元")
            logger.info(f"    - 强度得分: {strength.strength_score:.2f}")
            logger.info(f"    - Top股票数: {len(strength.top_stocks)}")
            logger.info(f"    - 子分类数: {len(strength.categories)}")

            results.add_test(
                "板块强度计算",
                "PASS",
                f"{sector_name}: 得分 {strength.strength_score:.2f}",
                f"股票数: {strength.total_count}, 上涨: {strength.up_count}"
            )

            # 验证数据合理性
            if strength.total_count == 0:
                results.add_bug(
                    "计算逻辑",
                    "HIGH",
                    "板块总股票数为0",
                    "sector_strength_service.py:calculate_sector_strength"
                )

            if strength.up_count + strength.down_count > strength.total_count:
                results.add_bug(
                    "计算逻辑",
                    "MEDIUM",
                    "上涨+下跌数量超过总数",
                    "sector_strength_service.py"
                )

            # 检查Top股票
            if strength.top_stocks:
                logger.info(f"\n  Top 5 股票:")
                for i, stock in enumerate(strength.top_stocks[:5], 1):
                    logger.info(
                        f"    {i}. {stock.symbol} {stock.name}: "
                        f"{stock.change_pct:+.2f}% (强度: {stock.strength_score:.2f})"
                    )
                results.add_test("Top股票提取", "PASS", f"提取 {len(strength.top_stocks)} 只")

            # 检查子分类
            if strength.categories:
                logger.info(f"\n  子分类强度 (共{len(strength.categories)}个):")
                for cat in strength.categories[:3]:
                    logger.info(
                        f"    - {cat.category_name}: 得分 {cat.strength_score:.2f}, "
                        f"涨跌 {cat.avg_change_pct:+.2f}%"
                    )
                results.add_test("子分类计算", "PASS", f"计算 {len(strength.categories)} 个分类")

            return True
        else:
            logger.error(f"  ✗ 板块强度计算失败")
            results.add_test("板块强度计算", "FAIL", "返回 None")
            results.add_bug(
                "计算服务",
                "HIGH",
                f"板块 {sector_name} 强度计算返回 None",
                "sector_strength_service.py"
            )
            return False

    except Exception as e:
        logger.error(f"板块强度计算测试失败: {e}", exc_info=True)
        results.add_test("板块强度计算", "FAIL", str(e))
        results.add_bug("计算服务", "HIGH", f"异常: {str(e)}", "sector_strength_service.py")
        return False


def test_cache_service():
    """测试5: 板块强度缓存服务"""
    logger.info("\n" + "=" * 80)
    logger.info("测试5: 板块强度缓存服务")
    logger.info("=" * 80)

    try:
        from app.services.sector_strength_cache_service import SectorStrengthCacheService
        from app.data.repositories.sector_repo import SectorRepository

        tushare_token = os.getenv("TUSHARE_TOKEN")
        if not tushare_token:
            return False

        cache_service = SectorStrengthCacheService(tushare_token)
        repo = SectorRepository()

        sectors = repo.list_all_sectors()
        if not sectors:
            return False

        test_sector = sectors[0]
        sector_id = test_sector["id"]
        test_date = date.today()

        logger.info(f"\n  测试板块: {test_sector['name']}")
        logger.info(f"  测试日期: {test_date}")

        # 测试计算并缓存
        logger.info(f"\n  执行计算并缓存...")
        cached_data = cache_service.calculate_and_cache(sector_id, test_date)

        if cached_data:
            logger.info(f"  ✓ 缓存保存成功")
            logger.info(f"    - 记录ID: {cached_data['id']}")
            logger.info(f"    - 强度得分: {cached_data['strength_score']:.2f}")
            results.add_test("缓存保存", "PASS", f"ID: {cached_data['id']}")

            # 测试从缓存读取
            logger.info(f"\n  从缓存读取...")
            retrieved_data = cache_service.get_cached_sector_strength(sector_id, test_date)

            if retrieved_data:
                logger.info(f"  ✓ 缓存读取成功")
                logger.info(f"    - 强度得分: {retrieved_data['strength_score']:.2f}")
                results.add_test("缓存读取", "PASS")

                # 验证数据一致性
                if cached_data['strength_score'] == retrieved_data['strength_score']:
                    logger.info(f"  ✓ 数据一致性验证通过")
                    results.add_test("缓存一致性", "PASS")
                else:
                    logger.error(f"  ✗ 数据不一致")
                    results.add_test("缓存一致性", "FAIL")
                    results.add_bug(
                        "缓存逻辑",
                        "HIGH",
                        "缓存数据与计算数据不一致",
                        "sector_strength_cache_service.py"
                    )
            else:
                logger.error(f"  ✗ 缓存读取失败")
                results.add_test("缓存读取", "FAIL")

            # 测试缓存新鲜度检查
            is_fresh = cache_service.is_cache_fresh(sector_id, max_age_days=1)
            logger.info(f"  ✓ 缓存新鲜度: {'新鲜' if is_fresh else '过期'}")
            results.add_test("缓存新鲜度检查", "PASS", f"新鲜: {is_fresh}")

            return True
        else:
            logger.error(f"  ✗ 缓存保存失败")
            results.add_test("缓存保存", "FAIL")
            return False

    except Exception as e:
        logger.error(f"缓存服务测试失败: {e}", exc_info=True)
        results.add_test("缓存服务", "FAIL", str(e))
        return False


def test_batch_update():
    """测试6: 批量更新所有板块"""
    logger.info("\n" + "=" * 80)
    logger.info("测试6: 批量更新所有板块（并行）")
    logger.info("=" * 80)

    try:
        from app.services.sector_strength_cache_service import SectorStrengthCacheService
        from app.data.repositories.sector_repo import SectorRepository
        import time

        tushare_token = os.getenv("TUSHARE_TOKEN")
        if not tushare_token:
            return False

        cache_service = SectorStrengthCacheService(tushare_token)
        repo = SectorRepository()

        sectors = repo.list_all_sectors()
        total_sectors = len(sectors)

        if total_sectors == 0:
            logger.warning("  ⚠️  没有板块数据，跳过批量更新测试")
            return False

        # 限制测试范围（避免测试时间过长）
        test_limit = min(5, total_sectors)
        logger.info(f"  板块总数: {total_sectors}，测试前 {test_limit} 个板块")

        def progress_callback(current, total, sector_name, elapsed):
            """进度回调"""
            logger.info(
                f"  进度: {current}/{total} ({current/total*100:.1f}%) - "
                f"{sector_name} - 耗时: {elapsed:.1f}s"
            )

        # 临时修改 list_all_sectors 返回值进行测试
        original_method = repo.list_all_sectors
        repo.list_all_sectors = lambda: sectors[:test_limit]

        start_time = time.time()
        stats = cache_service.update_all_sectors(
            calc_date=date.today(),
            progress_callback=progress_callback,
            max_workers=4  # 使用4个线程
        )
        elapsed = time.time() - start_time

        # 恢复原方法
        repo.list_all_sectors = original_method

        logger.info(f"\n  批量更新完成:")
        logger.info(f"    - 成功: {stats['success']}")
        logger.info(f"    - 失败: {stats['failed']}")
        logger.info(f"    - 总耗时: {elapsed:.2f}秒")
        logger.info(f"    - 平均每个: {elapsed/test_limit:.2f}秒")

        results.add_test(
            "批量更新",
            "PASS" if stats['failed'] == 0 else "FAIL",
            f"成功: {stats['success']}, 失败: {stats['failed']}",
            f"耗时: {elapsed:.2f}s"
        )

        if stats['failed'] > 0:
            results.add_warning("批量更新", f"{stats['failed']} 个板块更新失败")

        return stats['failed'] == 0

    except Exception as e:
        logger.error(f"批量更新测试失败: {e}", exc_info=True)
        results.add_test("批量更新", "FAIL", str(e))
        return False


def test_sync_service():
    """测试7: 题材库同步服务（仅结构测试，不实际同步）"""
    logger.info("\n" + "=" * 80)
    logger.info("测试7: 题材库同步服务（结构测试）")
    logger.info("=" * 80)

    try:
        from app.services.sector_sync_service import SectorSyncService

        tushare_token = os.getenv("TUSHARE_TOKEN")
        if not tushare_token:
            return False

        sync_service = SectorSyncService(tushare_token)

        # 测试获取概念板块（仅获取，不同步）
        logger.info(f"\n  测试获取Tushare概念板块...")
        concept_sectors = sync_service.fetch_concept_sectors()

        if concept_sectors:
            logger.info(f"  ✓ 成功获取 {len(concept_sectors)} 个概念板块")

            # 显示前5个
            logger.info(f"\n  前5个概念板块:")
            for sector in concept_sectors[:5]:
                logger.info(f"    - {sector['name']} (代码: {sector['code']})")

            results.add_test("获取概念板块", "PASS", f"数量: {len(concept_sectors)}")

            # 测试获取单个概念的股票
            test_concept = concept_sectors[0]
            logger.info(f"\n  测试获取概念股票: {test_concept['name']}")
            concept_stocks = sync_service.fetch_concept_stocks(test_concept['code'])

            if concept_stocks:
                logger.info(f"  ✓ 成功获取 {len(concept_stocks)} 只股票")

                # 显示前5只
                logger.info(f"\n  前5只股票:")
                for stock in concept_stocks[:5]:
                    logger.info(f"    - {stock['symbol']} {stock['stock_name']}")

                results.add_test("获取概念股票", "PASS", f"数量: {len(concept_stocks)}")
            else:
                logger.warning(f"  ⚠️  该概念没有股票数据")
                results.add_test("获取概念股票", "FAIL", "无数据")

            return True
        else:
            logger.error(f"  ✗ 无法获取概念板块数据")
            results.add_test("获取概念板块", "FAIL", "无数据返回")
            return False

    except Exception as e:
        logger.error(f"同步服务测试失败: {e}", exc_info=True)
        results.add_test("同步服务", "FAIL", str(e))
        return False


def test_update_script():
    """测试8: 更新脚本功能"""
    logger.info("\n" + "=" * 80)
    logger.info("测试8: 更新脚本功能（导入测试）")
    logger.info("=" * 80)

    try:
        # 测试脚本是否可以正常导入
        sys.path.insert(0, str(Path(__file__).parent.parent / "core" / "scripts"))

        import update_sector_strength

        logger.info(f"  ✓ 更新脚本导入成功")
        results.add_test("更新脚本导入", "PASS")

        # 检查关键函数是否存在
        if hasattr(update_sector_strength, 'run_daily_update'):
            logger.info(f"  ✓ run_daily_update 函数存在")
            results.add_test("更新函数检查", "PASS")
        else:
            logger.error(f"  ✗ run_daily_update 函数不存在")
            results.add_test("更新函数检查", "FAIL")
            results.add_bug(
                "脚本结构",
                "HIGH",
                "缺少 run_daily_update 函数",
                "update_sector_strength.py"
            )

        return True

    except Exception as e:
        logger.error(f"更新脚本测试失败: {e}", exc_info=True)
        results.add_test("更新脚本", "FAIL", str(e))
        return False


def generate_report():
    """生成测试报告"""
    logger.info("\n" + "=" * 80)
    logger.info("生成测试报告")
    logger.info("=" * 80)

    report_path = Path(__file__).parent.parent / "SECTOR_UPDATE_TEST_REPORT.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 题材库数据更新功能 - 测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # 测试摘要
        f.write("## 📊 测试摘要\n\n")
        f.write(f"- **总测试数**: {len(results.tests)}\n")
        f.write(f"- **✅ 通过**: {results.passed}\n")
        f.write(f"- **❌ 失败**: {results.failed}\n")
        f.write(f"- **⚠️ 警告**: {len(results.warnings)}\n")
        f.write(f"- **🐛 发现Bug**: {len(results.bugs)}\n\n")

        # 测试详情
        f.write("## 📋 测试详情\n\n")
        for test in results.tests:
            status_icon = "✅" if test["status"] == "PASS" else "❌"
            f.write(f"### {status_icon} {test['name']}\n\n")
            f.write(f"- **状态**: {test['status']}\n")
            if test['message']:
                f.write(f"- **信息**: {test['message']}\n")
            if test['details']:
                f.write(f"- **详情**: {test['details']}\n")
            f.write(f"- **时间**: {test['timestamp'].strftime('%H:%M:%S')}\n\n")

        # Bug列表
        if results.bugs:
            f.write("## 🐛 发现的Bug\n\n")
            for i, bug in enumerate(results.bugs, 1):
                f.write(f"### Bug #{i}: {bug['description']}\n\n")
                f.write(f"- **类别**: {bug['category']}\n")
                f.write(f"- **严重程度**: {bug['severity']}\n")
                f.write(f"- **位置**: `{bug['location']}`\n")
                f.write(f"- **发现时间**: {bug['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 警告列表
        if results.warnings:
            f.write("## ⚠️ 警告信息\n\n")
            for warning in results.warnings:
                f.write(f"- **{warning['category']}**: {warning['message']}\n")

        f.write("\n---\n\n")
        f.write("**测试完成**\n")

    logger.info(f"\n测试报告已生成: {report_path}")
    results.add_test("生成测试报告", "PASS", str(report_path))


def main():
    """主测试流程"""
    setup_logging(level="INFO")

    logger.info("=" * 80)
    logger.info("题材库数据更新功能 - 综合测试")
    logger.info("=" * 80)

    # 初始化数据库
    logger.info("\n初始化数据库...")
    initialize_db()

    # 执行测试
    tests = [
        ("数据库表结构", test_database_schema),
        ("SectorRepository", test_sector_repository),
        ("MarketDriver数据获取", test_market_driver),
        ("板块强度计算", test_sector_strength_calculation),
        ("缓存服务", test_cache_service),
        ("批量更新", test_batch_update),
        ("同步服务", test_sync_service),
        ("更新脚本", test_update_script),
    ]

    for name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            logger.error(f"测试 '{name}' 异常: {e}", exc_info=True)
            results.add_test(name, "FAIL", f"异常: {str(e)}")

    # 生成报告
    generate_report()

    # 打印摘要
    results.print_summary()

    # 返回退出码
    return 0 if results.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
