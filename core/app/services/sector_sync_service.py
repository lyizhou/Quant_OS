"""Sector Sync Service - 题材库同步服务.

从外部数据源（Tushare概念板块）同步题材数据，支持增量和差异更新。
"""

from __future__ import annotations

import json
from datetime import datetime

import tushare as ts

from app.common.logging import logger
from app.common.time import format_date
from app.data.db import get_db
from app.data.repositories.sector_repo import SectorRepository


class SectorSyncService:
    """题材库同步服务."""

    def __init__(self, tushare_token: str):
        """初始化同步服务.

        Args:
            tushare_token: Tushare API token
        """
        self.tushare_token = tushare_token
        ts.set_token(tushare_token)
        self.pro = ts.pro_api()
        self.db = get_db()
        self.sector_repo = SectorRepository()

    def fetch_concept_sectors(self) -> list[dict]:
        """从Tushare获取概念板块列表.

        Returns:
            概念板块列表
        """
        logger.info("Fetching concept sectors from Tushare...")

        try:
            # 获取概念板块列表
            df = self.pro.concept()

            if df.empty:
                logger.warning("No concept sectors found")
                return []

            sectors = []
            for _, row in df.iterrows():
                sectors.append({
                    "code": row["code"],  # 概念代码
                    "name": row["name"],  # 概念名称
                    "source": row.get("src", "ths"),  # 来源（同花顺等）
                })

            logger.info(f"Fetched {len(sectors)} concept sectors from Tushare")
            return sectors

        except Exception as e:
            logger.error(f"Failed to fetch concept sectors: {e}", exc_info=True)
            return []

    def fetch_concept_stocks(self, concept_code: str) -> list[dict]:
        """获取概念板块内的股票列表.

        Args:
            concept_code: 概念代码

        Returns:
            股票列表
        """
        try:
            # 获取概念成分股
            df = self.pro.concept_detail(id=concept_code)

            if df.empty:
                return []

            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    "symbol": row["ts_code"][:6],  # 股票代码（去掉交易所后缀）
                    "stock_name": row["name"],  # 股票名称
                    "in_date": row.get("in_date"),  # 纳入日期
                    "out_date": row.get("out_date"),  # 剔除日期
                })

            return stocks

        except Exception as e:
            logger.error(f"Failed to fetch stocks for concept {concept_code}: {e}")
            return []

    def sync_sectors_incremental(self) -> dict:
        """增量同步题材库.

        Returns:
            同步结果统计
        """
        sync_date = datetime.now().date()
        started_at = datetime.now()

        logger.info("=" * 60)
        logger.info(f"Starting incremental sector sync for {sync_date}")
        logger.info("=" * 60)

        # 创建同步日志
        sync_log_id = self._create_sync_log(sync_date, "incremental")

        try:
            # 获取外部数据源的板块列表
            external_sectors = self.fetch_concept_sectors()
            if not external_sectors:
                self._update_sync_log(
                    sync_log_id, "failed", error_message="No external sectors found"
                )
                return {"status": "failed", "error": "No external sectors found"}

            # 获取数据库中现有的板块
            existing_sectors = self.sector_repo.list_all_sectors()
            existing_sector_names = {s["name"]: s for s in existing_sectors}

            stats = {
                "sectors_added": 0,
                "sectors_updated": 0,
                "sectors_deleted": 0,
                "stocks_added": 0,
                "stocks_removed": 0,
            }

            # 处理每个外部板块
            for ext_sector in external_sectors:
                sector_name = ext_sector["name"]

                if sector_name in existing_sector_names:
                    # 板块已存在，更新股票列表
                    sector = existing_sector_names[sector_name]
                    sector_id = sector["id"]

                    logger.info(f"Updating sector: {sector_name} (ID: {sector_id})")

                    # 获取外部股票列表
                    external_stocks = self.fetch_concept_stocks(ext_sector["code"])

                    # 更新股票映射
                    stock_stats = self._update_sector_stocks(
                        sector_id, sector_name, external_stocks, sync_log_id
                    )

                    stats["stocks_added"] += stock_stats["added"]
                    stats["stocks_removed"] += stock_stats["removed"]

                    if stock_stats["added"] > 0 or stock_stats["removed"] > 0:
                        stats["sectors_updated"] += 1

                else:
                    # 新板块，创建并添加股票
                    logger.info(f"Adding new sector: {sector_name}")

                    sector_id = self.sector_repo.create_sector(
                        name=sector_name,
                        category="概念板块",
                        description=f"来源: {ext_sector.get('source', 'Tushare')}",
                    )

                    # 记录变更
                    self._log_change(
                        sync_log_id,
                        sync_date,
                        "add_sector",
                        sector_id=sector_id,
                        sector_name=sector_name,
                        new_value=json.dumps(ext_sector, ensure_ascii=False),
                    )

                    # 添加股票
                    external_stocks = self.fetch_concept_stocks(ext_sector["code"])
                    for stock in external_stocks:
                        if stock.get("out_date"):  # 跳过已剔除的股票
                            continue

                        try:
                            self.sector_repo.add_stock_to_sector(
                                sector_id=sector_id,
                                symbol=stock["symbol"],
                                stock_name=stock["stock_name"],
                            )
                            stats["stocks_added"] += 1

                            self._log_change(
                                sync_log_id,
                                sync_date,
                                "add_stock",
                                sector_id=sector_id,
                                sector_name=sector_name,
                                stock_symbol=stock["symbol"],
                                stock_name=stock["stock_name"],
                            )

                        except Exception as e:
                            logger.warning(
                                f"Failed to add stock {stock['symbol']} to sector {sector_name}: {e}"
                            )

                    stats["sectors_added"] += 1

            # 完成同步
            completed_at = datetime.now()
            duration = int((completed_at - started_at).total_seconds())

            self._update_sync_log(
                sync_log_id,
                "success",
                completed_at=completed_at,
                duration_seconds=duration,
                **stats,
            )

            logger.info("=" * 60)
            logger.info("Sector sync completed successfully")
            logger.info(f"Sectors added: {stats['sectors_added']}")
            logger.info(f"Sectors updated: {stats['sectors_updated']}")
            logger.info(f"Stocks added: {stats['stocks_added']}")
            logger.info(f"Stocks removed: {stats['stocks_removed']}")
            logger.info(f"Duration: {duration}s")
            logger.info("=" * 60)

            return {"status": "success", "stats": stats, "duration": duration}

        except Exception as e:
            logger.error(f"Sector sync failed: {e}", exc_info=True)
            self._update_sync_log(sync_log_id, "failed", error_message=str(e))
            return {"status": "failed", "error": str(e)}

    def _update_sector_stocks(
        self, sector_id: int, sector_name: str, external_stocks: list[dict], sync_log_id: int
    ) -> dict:
        """更新板块内的股票列表（增量更新）.

        Args:
            sector_id: 板块ID
            sector_name: 板块名称
            external_stocks: 外部股票列表
            sync_log_id: 同步日志ID

        Returns:
            更新统计
        """
        # 获取数据库中现有的股票
        existing_stocks = self.sector_repo.get_stocks_by_sector(sector_id)
        existing_symbols = {s["symbol"] for s in existing_stocks}

        # 外部股票（排除已剔除的）
        active_external_stocks = [s for s in external_stocks if not s.get("out_date")]
        external_symbols = {s["symbol"] for s in active_external_stocks}

        # 需要添加的股票
        symbols_to_add = external_symbols - existing_symbols

        # 需要删除的股票
        symbols_to_remove = existing_symbols - external_symbols

        stats = {"added": 0, "removed": 0}

        # 添加新股票
        for stock in active_external_stocks:
            if stock["symbol"] in symbols_to_add:
                try:
                    self.sector_repo.add_stock_to_sector(
                        sector_id=sector_id,
                        symbol=stock["symbol"],
                        stock_name=stock["stock_name"],
                    )
                    stats["added"] += 1

                    self._log_change(
                        sync_log_id,
                        datetime.now().date(),
                        "add_stock",
                        sector_id=sector_id,
                        sector_name=sector_name,
                        stock_symbol=stock["symbol"],
                        stock_name=stock["stock_name"],
                    )

                    logger.debug(f"Added {stock['symbol']} to {sector_name}")

                except Exception as e:
                    logger.warning(
                        f"Failed to add stock {stock['symbol']} to {sector_name}: {e}"
                    )

        # 删除不再属于该板块的股票
        for symbol in symbols_to_remove:
            try:
                self.sector_repo.remove_stock_from_sector(sector_id, symbol)
                stats["removed"] += 1

                stock_info = next((s for s in existing_stocks if s["symbol"] == symbol), None)
                self._log_change(
                    sync_log_id,
                    datetime.now().date(),
                    "remove_stock",
                    sector_id=sector_id,
                    sector_name=sector_name,
                    stock_symbol=symbol,
                    stock_name=stock_info["stock_name"] if stock_info else None,
                )

                logger.debug(f"Removed {symbol} from {sector_name}")

            except Exception as e:
                logger.warning(f"Failed to remove stock {symbol} from {sector_name}: {e}")

        if stats["added"] > 0 or stats["removed"] > 0:
            logger.info(
                f"Updated {sector_name}: +{stats['added']} stocks, -{stats['removed']} stocks"
            )

        return stats

    def _create_sync_log(self, sync_date, sync_type: str) -> int:
        """创建同步日志记录.

        Args:
            sync_date: 同步日期
            sync_type: 同步类型

        Returns:
            日志ID
        """
        conn = self.db.get_connection()
        result = conn.execute(
            """
            INSERT INTO sector_sync_log (sync_date, sync_type, data_source)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            [sync_date, sync_type, "tushare_concept"],
        ).fetchone()

        return result[0]

    def _update_sync_log(
        self,
        sync_log_id: int,
        status: str,
        completed_at: datetime = None,
        duration_seconds: int = None,
        error_message: str = None,
        **stats,
    ):
        """更新同步日志.

        Args:
            sync_log_id: 日志ID
            status: 状态
            completed_at: 完成时间
            duration_seconds: 耗时
            error_message: 错误信息
            **stats: 统计数据
        """
        conn = self.db.get_connection()

        update_fields = ["status = ?"]
        params = [status]

        if completed_at:
            update_fields.append("completed_at = ?")
            params.append(completed_at)

        if duration_seconds is not None:
            update_fields.append("duration_seconds = ?")
            params.append(duration_seconds)

        if error_message:
            update_fields.append("error_message = ?")
            params.append(error_message)

        for key, value in stats.items():
            update_fields.append(f"{key} = ?")
            params.append(value)

        params.append(sync_log_id)

        conn.execute(
            f"""
            UPDATE sector_sync_log
            SET {', '.join(update_fields)}
            WHERE id = ?
            """,
            params,
        )

    def _log_change(
        self,
        sync_log_id: int,
        change_date,
        change_type: str,
        sector_id: int = None,
        sector_name: str = None,
        stock_symbol: str = None,
        stock_name: str = None,
        old_value: str = None,
        new_value: str = None,
    ):
        """记录变更历史.

        Args:
            sync_log_id: 同步日志ID
            change_date: 变更日期
            change_type: 变更类型
            sector_id: 板块ID
            sector_name: 板块名称
            stock_symbol: 股票代码
            stock_name: 股票名称
            old_value: 旧值
            new_value: 新值
        """
        conn = self.db.get_connection()
        conn.execute(
            """
            INSERT INTO sector_change_history (
                sync_log_id, change_date, change_type,
                sector_id, sector_name,
                stock_symbol, stock_name,
                old_value, new_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                sync_log_id,
                change_date,
                change_type,
                sector_id,
                sector_name,
                stock_symbol,
                stock_name,
                old_value,
                new_value,
            ],
        )

    def get_sync_history(self, limit: int = 10) -> list[dict]:
        """获取同步历史记录.

        Args:
            limit: 返回记录数

        Returns:
            同步历史列表
        """
        conn = self.db.get_connection()
        results = conn.execute(
            """
            SELECT id, sync_date, sync_type, status,
                   sectors_added, sectors_updated, sectors_deleted,
                   stocks_added, stocks_removed,
                   started_at, completed_at, duration_seconds,
                   error_message
            FROM sector_sync_log
            ORDER BY started_at DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()

        history = []
        for row in results:
            history.append({
                "id": row[0],
                "sync_date": row[1],
                "sync_type": row[2],
                "status": row[3],
                "sectors_added": row[4],
                "sectors_updated": row[5],
                "sectors_deleted": row[6],
                "stocks_added": row[7],
                "stocks_removed": row[8],
                "started_at": row[9],
                "completed_at": row[10],
                "duration_seconds": row[11],
                "error_message": row[12],
            })

        return history
