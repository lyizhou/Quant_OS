"""数据更新状态跟踪服务

提供数据更新状态的记录、查询和统计功能。
"""

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.common.logging import logger
from app.data.db import get_db


class DataUpdateStatusService:
    """数据更新状态服务"""

    # 更新类型常量
    STOCK_DAILY = "stock_daily"  # 每日股票数据
    THEME_DATA = "theme_data"  # 题材库数据
    SECTOR_STRENGTH = "sector_strength"  # 板块强度计算
    PORTFOLIO_PRICES = "portfolio_prices"  # 持仓价格更新
    STOCK_CACHE = "stock_cache"  # 股票缓存更新
    SECTOR_SYNC = "sector_sync"  # 板块数据同步

    # 状态常量
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_RUNNING = "running"
    STATUS_PARTIAL = "partial"
    STATUS_PENDING = "pending"

    def __init__(self):
        """初始化服务"""
        self.db = get_db()

    @contextmanager
    def track_update(
        self,
        update_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """跟踪数据更新的上下文管理器

        使用示例:
            with status_service.track_update('stock_daily', {'source': 'tushare'}) as tracker:
                # 执行更新操作
                result = update_stocks()
                tracker.set_records(processed=100, success=98, failed=2)

        Args:
            update_type: 更新类型
            metadata: 额外元数据

        Yields:
            UpdateTracker: 更新跟踪器
        """
        tracker = UpdateTracker(self, update_type, metadata)
        tracker.start()

        try:
            yield tracker
            if tracker.status == self.STATUS_RUNNING:
                tracker.complete(self.STATUS_SUCCESS)
        except Exception as e:
            logger.error(f"Update {update_type} failed: {e}", exc_info=True)
            tracker.complete(self.STATUS_FAILED, error_message=str(e))
            raise

    def record_update(
        self,
        update_type: str,
        status: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
        records_processed: int = 0,
        records_success: int = 0,
        records_failed: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """记录更新状态

        Args:
            update_type: 更新类型
            status: 状态
            start_time: 开始时间
            end_time: 结束时间
            duration_seconds: 执行时长（秒）
            records_processed: 处理记录数
            records_success: 成功记录数
            records_failed: 失败记录数
            error_message: 错误信息
            metadata: 额外元数据

        Returns:
            记录ID
        """
        try:
            conn = self.db.get_connection()

            # 序列化metadata
            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

            result = conn.execute(
                """
                INSERT INTO data_update_status (
                    update_type, status, start_time, end_time, duration_seconds,
                    records_processed, records_success, records_failed,
                    error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [
                    update_type,
                    status,
                    start_time,
                    end_time,
                    duration_seconds,
                    records_processed,
                    records_success,
                    records_failed,
                    error_message,
                    metadata_json,
                ],
            ).fetchone()

            record_id = result[0]
            logger.info(f"Recorded update status: {update_type} - {status} (ID: {record_id})")
            return record_id

        except Exception as e:
            logger.error(f"Failed to record update status: {e}", exc_info=True)
            raise

    def get_latest_status(self, update_type: str) -> Optional[Dict[str, Any]]:
        """获取指定类型的最新更新状态

        Args:
            update_type: 更新类型

        Returns:
            状态信息字典，不存在返回None
        """
        try:
            conn = self.db.get_connection()

            result = conn.execute(
                """
                SELECT * FROM data_update_status
                WHERE update_type = ?
                ORDER BY start_time DESC
                LIMIT 1
                """,
                [update_type],
            ).fetchone()

            if not result:
                return None

            return self._row_to_dict(result)

        except Exception as e:
            logger.error(f"Failed to get latest status: {e}", exc_info=True)
            return None

    def get_all_latest_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有更新类型的最新状态

        Returns:
            {update_type: status_info} 字典
        """
        try:
            conn = self.db.get_connection()

            results = conn.execute(
                """
                SELECT * FROM v_latest_update_status
                ORDER BY update_type
                """
            ).fetchall()

            status_dict = {}
            for row in results:
                data = self._row_to_dict(row)
                status_dict[data["update_type"]] = data

            return status_dict

        except Exception as e:
            logger.error(f"Failed to get all latest status: {e}", exc_info=True)
            return {}

    def get_status_history(
        self, update_type: str, days: int = 7, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取更新状态历史记录

        Args:
            update_type: 更新类型
            days: 查询最近N天的记录
            limit: 最大记录数

        Returns:
            状态记录列表
        """
        try:
            conn = self.db.get_connection()

            cutoff_date = datetime.now() - timedelta(days=days)

            results = conn.execute(
                """
                SELECT * FROM data_update_status
                WHERE update_type = ? AND start_time >= ?
                ORDER BY start_time DESC
                LIMIT ?
                """,
                [update_type, cutoff_date, limit],
            ).fetchall()

            return [self._row_to_dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get status history: {e}", exc_info=True)
            return []

    def get_update_statistics(self, update_type: str, days: int = 7) -> Dict[str, Any]:
        """获取更新统计信息

        Args:
            update_type: 更新类型
            days: 统计最近N天的数据

        Returns:
            统计信息字典
        """
        try:
            conn = self.db.get_connection()

            cutoff_date = datetime.now() - timedelta(days=days)

            result = conn.execute(
                """
                SELECT
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_runs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    SUM(records_processed) as total_records,
                    SUM(records_success) as total_success,
                    SUM(records_failed) as total_failed
                FROM data_update_status
                WHERE update_type = ? AND start_time >= ?
                """,
                [update_type, cutoff_date],
            ).fetchone()

            if not result:
                return {}

            return {
                "update_type": update_type,
                "period_days": days,
                "total_runs": result[0] or 0,
                "success_runs": result[1] or 0,
                "failed_runs": result[2] or 0,
                "success_rate": (result[1] or 0) / (result[0] or 1) * 100,
                "avg_duration": result[3],
                "min_duration": result[4],
                "max_duration": result[5],
                "total_records": result[6] or 0,
                "total_success": result[7] or 0,
                "total_failed": result[8] or 0,
            }

        except Exception as e:
            logger.error(f"Failed to get update statistics: {e}", exc_info=True)
            return {}

    def is_update_fresh(self, update_type: str, max_age_hours: int = 24) -> bool:
        """检查更新是否新鲜

        Args:
            update_type: 更新类型
            max_age_hours: 最大年龄（小时）

        Returns:
            是否新鲜
        """
        latest = self.get_latest_status(update_type)

        if not latest:
            return False

        if latest["status"] != self.STATUS_SUCCESS:
            return False

        # 检查时间
        start_time = latest["start_time"]
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        age = datetime.now() - start_time
        return age.total_seconds() / 3600 <= max_age_hours

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        # 数据库列索引:
        # 0: id, 1: update_type, 2: status, 3: start_time, 4: end_time,
        # 5: duration_seconds, 6: records_processed, 7: records_success,
        # 8: records_failed, 9: error_message, 10: metadata, 11: created_at

        metadata = None
        if len(row) > 10 and row[10]:  # metadata字段在索引10
            try:
                metadata = json.loads(row[10])
            except Exception as e:
                logger.warning(f"Failed to parse metadata JSON: {e}")

        return {
            "id": row[0],
            "update_type": row[1],
            "status": row[2],
            "start_time": row[3],
            "end_time": row[4],
            "duration_seconds": row[5],
            "records_processed": row[6],
            "records_success": row[7],
            "records_failed": row[8],
            "error_message": row[9] if len(row) > 9 else None,
            "metadata": metadata,
            "created_at": row[11] if len(row) > 11 else None,
        }


class UpdateTracker:
    """更新跟踪器 - 用于track_update上下文管理器"""

    def __init__(
        self,
        service: DataUpdateStatusService,
        update_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """初始化跟踪器

        Args:
            service: 数据更新状态服务
            update_type: 更新类型
            metadata: 额外元数据
        """
        self.service = service
        self.update_type = update_type
        self.metadata = metadata or {}
        self.start_time: Optional[datetime] = None
        self.status = DataUpdateStatusService.STATUS_RUNNING
        self.records_processed = 0
        self.records_success = 0
        self.records_failed = 0
        self.error_message: Optional[str] = None

    def start(self):
        """开始跟踪"""
        self.start_time = datetime.now()
        logger.info(f"Started tracking update: {self.update_type}")

    def set_records(self, processed: int = 0, success: int = 0, failed: int = 0):
        """设置处理记录数

        Args:
            processed: 处理总数
            success: 成功数
            failed: 失败数
        """
        self.records_processed = processed
        self.records_success = success
        self.records_failed = failed

    def add_records(self, processed: int = 0, success: int = 0, failed: int = 0):
        """累加处理记录数

        Args:
            processed: 处理总数
            success: 成功数
            failed: 失败数
        """
        self.records_processed += processed
        self.records_success += success
        self.records_failed += failed

    def complete(self, status: str, error_message: Optional[str] = None):
        """完成跟踪

        Args:
            status: 最终状态
            error_message: 错误信息（如果失败）
        """
        if self.start_time is None:
            logger.warning("Tracker not started, skipping completion")
            return

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        self.status = status
        self.error_message = error_message

        # 记录到数据库
        self.service.record_update(
            update_type=self.update_type,
            status=status,
            start_time=self.start_time,
            end_time=end_time,
            duration_seconds=duration,
            records_processed=self.records_processed,
            records_success=self.records_success,
            records_failed=self.records_failed,
            error_message=error_message,
            metadata=self.metadata,
        )

        logger.info(
            f"Completed tracking update: {self.update_type} - {status} "
            f"(duration: {duration:.2f}s, processed: {self.records_processed})"
        )
