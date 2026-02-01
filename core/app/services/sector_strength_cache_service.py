"""板块强度缓存服务

提供板块强度计算结果的缓存功能，避免重复调用API
"""

import json
from datetime import date, datetime
from typing import Any

from app.common.logging import logger
from app.data.db import get_db
from app.data.repositories.sector_repo import SectorRepository
from app.services.sector_strength_service import (
    CategoryStrength,
    SectorStrength,
    SectorStrengthService,
    StockStrength,
)


class SectorStrengthCacheService:
    """板块强度缓存服务"""

    def __init__(self, tushare_token: str):
        """初始化缓存服务

        Args:
            tushare_token: Tushare API token
        """
        self.tushare_token = tushare_token
        self.strength_service = SectorStrengthService(tushare_token)
        self.sector_repo = SectorRepository()
        self.db = get_db()

    def save_sector_strength(self, strength: SectorStrength, calc_date: date) -> int:
        """保存板块强度结果到数据库

        Args:
            strength: 板块强度数据
            calc_date: 计算日期

        Returns:
            记录ID
        """
        try:
            conn = self.db.get_connection()

            # 序列化Top股票
            top_stocks_json = json.dumps(
                [
                    {
                        "symbol": s.symbol,
                        "name": s.name,
                        "change_pct": s.change_pct,
                        "price": s.price,
                        "volume_ratio": s.volume_ratio,
                        "turnover_rate": s.turnover_rate,
                        "net_money_flow": s.net_money_flow,
                        "money_flow_ratio": s.money_flow_ratio,
                        "strength_score": s.strength_score,
                    }
                    for s in strength.top_stocks
                ],
                ensure_ascii=False,
            )

            # 插入主记录（使用序列生成ID）
            result = conn.execute(
                """
                INSERT INTO sector_strength_results (
                    id, sector_id, sector_name, category, category_id, category_name,
                    calc_date, total_count, up_count, down_count, up_ratio,
                    avg_change_pct, avg_volume_ratio, avg_turnover_rate,
                    total_net_money_flow, avg_money_flow_ratio,
                    strength_score, top_stocks
                ) VALUES (nextval('sector_strength_results_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [
                    strength.sector_id,
                    strength.sector_name,
                    None,  # category (主板块设为NULL)
                    None,  # category_id (主板块为空)
                    None,  # category_name (主板块为空)
                    calc_date,
                    strength.total_count,
                    strength.up_count,
                    strength.down_count,
                    strength.up_ratio,
                    strength.avg_change_pct,
                    strength.avg_volume_ratio,
                    strength.avg_turnover_rate,
                    strength.total_net_money_flow,
                    (
                        strength.total_net_money_flow / (strength.total_count * 10000) * 100
                        if strength.total_count > 0
                        else 0
                    ),  # 转换为占比
                    strength.strength_score,
                    top_stocks_json,
                ],
            ).fetchone()

            record_id = result[0]
            logger.info(
                f"Saved sector strength for {strength.sector_name} on {calc_date}, ID: {record_id}"
            )

            # 保存子分类数据
            for category in strength.categories:
                self._save_category_strength(record_id, strength.sector_id, category, calc_date)

            # 保存历史记录
            self._save_history(strength.sector_id, calc_date, strength)

            return record_id

        except Exception as e:
            logger.error(f"Failed to save sector strength: {e}", exc_info=True)
            raise

    def _save_category_strength(
        self, parent_id: int, sector_id: int, category: CategoryStrength, calc_date: date
    ):
        """保存子分类强度数据"""
        try:
            conn = self.db.get_connection()

            top_stocks_json = json.dumps(
                [
                    {
                        "symbol": s.symbol,
                        "name": s.name,
                        "change_pct": s.change_pct,
                        "strength_score": s.strength_score,
                    }
                    for s in category.top_stocks
                ],
                ensure_ascii=False,
            )

            conn.execute(
                """
                INSERT INTO sector_strength_results (
                    id, sector_id, sector_name, category, category_id, category_name,
                    calc_date, total_count, up_count, down_count, up_ratio,
                    avg_change_pct, avg_volume_ratio, avg_turnover_rate,
                    total_net_money_flow, avg_money_flow_ratio,
                    strength_score, top_stocks
                ) VALUES (nextval('sector_strength_results_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    sector_id,
                    f"{category.category_name}",
                    "subcategory",
                    category.category_id,
                    category.category_name,
                    calc_date,
                    category.total_count,
                    category.up_count,
                    category.down_count,
                    category.up_ratio,
                    category.avg_change_pct,
                    0.0,  # avg_volume_ratio (子分类不计算)
                    0.0,  # avg_turnover_rate (子分类不计算)
                    category.total_net_money_flow,
                    0.0,  # avg_money_flow_ratio (子分类不计算)
                    category.strength_score,
                    top_stocks_json,
                ],
            )
            logger.debug(f"Saved category strength for {category.category_name}")

        except Exception as e:
            logger.error(f"Failed to save category strength: {e}", exc_info=True)

    def _save_history(self, sector_id: int, calc_date: date, strength: SectorStrength):
        """保存历史数据用于趋势分析"""
        try:
            conn = self.db.get_connection()
            conn.execute(
                """
                INSERT INTO sector_strength_history (
                    id, sector_id, calc_date, strength_score,
                    avg_change_pct, up_ratio, total_net_money_flow
                ) VALUES (nextval('sector_strength_history_id_seq'), ?, ?, ?, ?, ?, ?)
                """,
                [
                    sector_id,
                    calc_date,
                    strength.strength_score,
                    strength.avg_change_pct,
                    strength.up_ratio,
                    strength.total_net_money_flow,
                ],
            )
        except Exception as e:
            logger.error(f"Failed to save history: {e}", exc_info=True)

    def get_cached_sector_strength(
        self, sector_id: int, calc_date: date | None = None
    ) -> dict[str, Any] | None:
        """从缓存获取板块强度

        Args:
            sector_id: 板块ID
            calc_date: 计算日期，None表示最新日期

        Returns:
            缓存的强度数据，不存在返回None
        """
        try:
            conn = self.db.get_connection()

            if calc_date is None:
                # 获取最新记录
                result = conn.execute(
                    """
                    SELECT * FROM sector_strength_results
                    WHERE sector_id = ? AND category IS NULL
                    ORDER BY calc_date DESC
                    LIMIT 1
                    """,
                    [sector_id],
                ).fetchone()
            else:
                result = conn.execute(
                    """
                    SELECT * FROM sector_strength_results
                    WHERE sector_id = ? AND calc_date = ? AND category IS NULL
                    LIMIT 1
                    """,
                    [sector_id, calc_date],
                ).fetchone()

            if not result:
                return None

            # 解析Top股票
            top_stocks = []
            if result[16]:  # top_stocks 字段
                try:
                    stocks_data = json.loads(result[16])
                    for stock in stocks_data:
                        top_stocks.append(
                            StockStrength(
                                symbol=stock["symbol"],
                                name=stock["name"],
                                change_pct=stock["change_pct"],
                                price=stock["price"],
                                volume_ratio=stock["volume_ratio"],
                                turnover_rate=stock["turnover_rate"],
                                net_money_flow=stock["net_money_flow"],
                                money_flow_ratio=stock["money_flow_ratio"],
                                strength_score=stock["strength_score"],
                            )
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse top_stocks JSON: {e}")

            # 获取子分类
            categories = self._get_cached_categories(sector_id, calc_date)

            return {
                "id": result[0],
                "sector_id": result[1],
                "sector_name": result[2],
                "category": result[3],
                "calc_date": result[4],
                "total_count": result[6],
                "up_count": result[7],
                "down_count": result[8],
                "up_ratio": result[9],
                "avg_change_pct": result[10],
                "avg_volume_ratio": result[11],
                "avg_turnover_rate": result[12],
                "total_net_money_flow": result[13],
                "avg_money_flow_ratio": result[14],
                "strength_score": result[15],
                "top_stocks": top_stocks,
                "categories": categories,
            }

        except Exception as e:
            logger.error(f"Failed to get cached sector strength: {e}", exc_info=True)
            return None

    def _get_cached_categories(
        self, sector_id: int, calc_date: date | None = None
    ) -> list[dict[str, Any]]:
        """获取缓存的子分类数据"""
        try:
            conn = self.db.get_connection()

            if calc_date is None:
                results = conn.execute(
                    """
                    SELECT * FROM sector_strength_results
                    WHERE sector_id = ? AND category = 'subcategory'
                    ORDER BY calc_date DESC, strength_score DESC
                    """,
                    [sector_id],
                ).fetchall()
            else:
                results = conn.execute(
                    """
                    SELECT * FROM sector_strength_results
                    WHERE sector_id = ? AND calc_date = ? AND category = 'subcategory'
                    ORDER BY strength_score DESC
                    """,
                    [sector_id, calc_date],
                ).fetchall()

            categories = []
            for row in results:
                categories.append(
                    {
                        "category_id": row[5],  # category_id
                        "category_name": row[6],  # category_name
                        "total_count": row[7],
                        "up_count": row[8],
                        "down_count": row[9],
                        "up_ratio": row[10],
                        "avg_change_pct": row[11],
                        "total_net_money_flow": row[13],
                        "strength_score": row[15],
                    }
                )

            return categories

        except Exception as e:
            logger.error(f"Failed to get cached categories: {e}", exc_info=True)
            return []

    def get_all_cached_sectors(self, calc_date: date | None = None) -> list[dict[str, Any]]:
        """获取所有缓存的板块强度

        Args:
            calc_date: 计算日期，None表示最新日期

        Returns:
            板块强度列表
        """
        try:
            conn = self.db.get_connection()

            if calc_date is None:
                # 获取每个板块的最新记录
                results = conn.execute(
                    """
                    SELECT DISTINCT ON (sector_id) *
                    FROM sector_strength_results
                    WHERE category IS NULL
                    ORDER BY sector_id, calc_date DESC
                    """
                ).fetchall()
            else:
                results = conn.execute(
                    """
                    SELECT * FROM sector_strength_results
                    WHERE calc_date = ? AND category IS NULL
                    ORDER BY strength_score DESC
                    """,
                    [calc_date],
                ).fetchall()

            sectors = []
            for row in results:
                sectors.append(
                    {
                        "id": row[0],
                        "sector_id": row[1],
                        "sector_name": row[2],
                        "category": row[3],
                        "calc_date": row[4],
                        "total_count": row[6],
                        "up_count": row[7],
                        "down_count": row[8],
                        "up_ratio": row[9],
                        "avg_change_pct": row[10],
                        "avg_volume_ratio": row[11],
                        "avg_turnover_rate": row[12],
                        "total_net_money_flow": row[13],
                        "strength_score": row[15],
                    }
                )

            # 按强度得分排序
            sectors.sort(key=lambda x: x["strength_score"], reverse=True)
            return sectors

        except Exception as e:
            logger.error(f"Failed to get all cached sectors: {e}", exc_info=True)
            return []

    def calculate_and_cache(
        self, sector_id: int, calc_date: date | None = None
    ) -> dict[str, Any] | None:
        """计算板块强度并缓存

        Args:
            sector_id: 板块ID
            calc_date: 计算日期，None表示今天

        Returns:
            缓存的强度数据
        """
        # 计算强度
        strength = self.strength_service.calculate_sector_strength(sector_id, calc_date)

        if not strength:
            return None

        # 如果没有指定日期，使用今天
        if calc_date is None:
            calc_date = date.today()

        # 保存到缓存
        cache_id = self.save_sector_strength(strength, calc_date)

        # 返回缓存数据
        return self.get_cached_sector_strength(sector_id, calc_date)

    def update_all_sectors(self, calc_date: date | None = None, progress_callback=None, max_workers: int = 8) -> dict[str, int]:
        """更新所有板块的强度数据（支持并行计算）

        Args:
            calc_date: 计算日期，None表示今天
            progress_callback: 进度回调函数，接收 (current, total, sector_name, elapsed_time)
            max_workers: 最大并行线程数，默认8

        Returns:
            统计信息 {'success': 成功数, 'failed': 失败数}
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from threading import Lock
        from app.common.time import get_last_market_day

        # 获取所有板块
        sectors = self.sector_repo.list_all_sectors()

        if not sectors:
            logger.warning("No sectors found")
            return {"success": 0, "failed": 0}

        # 优化：只在开始时获取一次交易日期，避免每个板块都重复获取
        if calc_date is None:
            calc_date = get_last_market_day(market="CN")
            logger.info(f"Using last market day: {calc_date}")

        logger.info(f"Starting parallel batch update for {len(sectors)} sectors on {calc_date} (workers: {max_workers})")

        success_count = 0
        failed_count = 0
        completed_count = 0
        start_time = time.time()

        # 使用锁保护共享变量
        lock = Lock()

        def process_sector(sector):
            """处理单个板块的函数 - 每个线程创建独立的服务实例"""
            try:
                # 为每个线程创建独立的服务实例，避免数据库连接冲突
                thread_cache_service = SectorStrengthCacheService(self.tushare_token)
                result = thread_cache_service.calculate_and_cache(sector["id"], calc_date)

                if result:
                    logger.info(f"  ✓ Success: {sector['name']} - Score: {result['strength_score']:.2f}")
                    return ("success", sector['name'])
                else:
                    logger.warning(f"  ✗ Failed: {sector['name']}")
                    return ("failed", sector['name'])

            except Exception as e:
                logger.error(f"  ✗ Error processing {sector['name']}: {e}")
                return ("failed", sector['name'])

        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_sector = {executor.submit(process_sector, sector): sector for sector in sectors}

            # 处理完成的任务
            for future in as_completed(future_to_sector):
                sector = future_to_sector[future]

                with lock:
                    completed_count += 1

                    try:
                        status, sector_name = future.result()
                        if status == "success":
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Task exception for {sector['name']}: {e}")

                    # 调用进度回调
                    if progress_callback:
                        elapsed = time.time() - start_time
                        try:
                            progress_callback(completed_count, len(sectors), sector['name'], elapsed)
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")

        logger.info(f"Parallel batch update completed: {success_count} success, {failed_count} failed")
        return {"success": success_count, "failed": failed_count}

    def is_cache_fresh(self, sector_id: int, max_age_days: int = 1) -> bool:
        """检查缓存是否新鲜

        Args:
            sector_id: 板块ID
            max_age_days: 最大缓存天数

        Returns:
            缓存是否新鲜
        """
        try:
            conn = self.db.get_connection()
            result = conn.execute(
                """
                SELECT calc_date FROM sector_strength_results
                WHERE sector_id = ? AND category IS NULL
                ORDER BY calc_date DESC
                LIMIT 1
                """,
                [sector_id],
            ).fetchone()

            if not result:
                return False

            cache_date = result[0]
            if isinstance(cache_date, str):
                cache_date = datetime.strptime(cache_date, "%Y-%m-%d").date()

            days_old = (date.today() - cache_date).days
            return days_old <= max_age_days

        except Exception as e:
            logger.error(f"Failed to check cache freshness: {e}")
            return False
