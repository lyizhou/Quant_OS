"""Sector Repository - 板块数据仓库."""

from typing import Any, Optional

from app.common.logging import logger
from app.data.db import get_db
from app.data.repositories.base import BaseRepository


class SectorRepository(BaseRepository):
    """板块数据仓库."""

    def __init__(self):
        """初始化仓库."""
        super().__init__(get_db())

    def _normalize_symbol(self, symbol: str | float | int) -> str:
        """标准化股票代码，确保是正确的6位字符串格式.

        Args:
            symbol: 股票代码（可能是字符串、浮点数或整数）

        Returns:
            标准化后的6位股票代码字符串

        Examples:
            1.0 -> "000001"
            100.0 -> "000100"
            600000.0 -> "600000"
            "000001" -> "000001"
        """
        if not symbol:
            return ""

        symbol_str = str(symbol)

        # 如果是浮点数格式（包含小数点），移除小数部分
        if "." in symbol_str:
            symbol_str = symbol_str.split(".")[0]

        # 如果是纯数字字符串，确保6位前导零
        if symbol_str.isdigit():
            symbol_str = symbol_str.zfill(6)

        return symbol_str

    def create_sector(
        self, name: str, category: Optional[str] = None, description: Optional[str] = None
    ) -> int:
        """创建板块.

        Args:
            name: 板块名称
            category: 板块分类
            description: 板块描述

        Returns:
            板块ID
        """
        conn = self.db.get_connection()
        result = conn.execute(
            """
            INSERT INTO sectors (name, category, description)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            [name, category, description],
        ).fetchone()

        sector_id = result[0]
        logger.info(f"Created sector: {name} (ID: {sector_id})")
        return sector_id

    def get_sector_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """根据名称获取板块.

        Args:
            name: 板块名称

        Returns:
            板块信息字典，不存在返回 None
        """
        conn = self.db.get_connection()
        result = conn.execute(
            """
            SELECT id, name, category, description, created_at, updated_at
            FROM sectors
            WHERE name = ?
            """,
            [name],
        ).fetchone()

        if not result:
            return None

        return {
            "id": result[0],
            "name": result[1],
            "category": result[2],
            "description": result[3],
            "created_at": result[4],
            "updated_at": result[5],
        }

    def search_sectors(self, keyword: str) -> list[dict[str, Any]]:
        """模糊搜索板块.

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的板块列表
        """
        conn = self.db.get_connection()
        search_pattern = f"%{keyword}%"
        results = conn.execute(
            """
            SELECT id, name, category, description, created_at, updated_at
            FROM sectors
            WHERE name LIKE ? OR category LIKE ? OR description LIKE ?
            ORDER BY
                CASE
                    WHEN name = ? THEN 1
                    WHEN name LIKE ? THEN 2
                    ELSE 3
                END,
                created_at DESC
            """,
            [search_pattern, search_pattern, search_pattern, keyword, search_pattern],
        ).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "created_at": row[4],
                "updated_at": row[5],
            }
            for row in results
        ]

    def get_sector_by_id(self, sector_id: int) -> Optional[dict[str, Any]]:
        """根据ID获取板块.

        Args:
            sector_id: 板块ID

        Returns:
            板块信息字典，不存在返回 None
        """
        conn = self.db.get_connection()
        result = conn.execute(
            """
            SELECT id, name, category, description, created_at, updated_at
            FROM sectors
            WHERE id = ?
            """,
            [sector_id],
        ).fetchone()

        if not result:
            return None

        return {
            "id": result[0],
            "name": result[1],
            "category": result[2],
            "description": result[3],
            "created_at": result[4],
            "updated_at": result[5],
        }

    def list_all_sectors(self) -> list[dict[str, Any]]:
        """获取所有板块列表.

        Returns:
            板块列表
        """
        conn = self.db.get_connection()
        results = conn.execute(
            """
            SELECT id, name, category, description, created_at, updated_at
            FROM sectors
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "created_at": row[4],
                "updated_at": row[5],
            }
            for row in results
        ]

    def create_category(
        self, sector_id: int, name: str, description: Optional[str] = None, sort_order: int = 0
    ) -> int:
        """创建板块子分类.

        Args:
            sector_id: 板块ID
            name: 子分类名称
            description: 子分类描述
            sort_order: 排序

        Returns:
            子分类ID
        """
        conn = self.db.get_connection()
        result = conn.execute(
            """
            INSERT INTO sector_categories (sector_id, name, description, sort_order)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            [sector_id, name, description, sort_order],
        ).fetchone()

        category_id = result[0]
        logger.info(f"Created category: {name} (ID: {category_id}) in sector {sector_id}")
        return category_id

    def get_categories_by_sector(self, sector_id: int) -> list[dict[str, Any]]:
        """获取板块的所有子分类.

        Args:
            sector_id: 板块ID

        Returns:
            子分类列表
        """
        conn = self.db.get_connection()
        results = conn.execute(
            """
            SELECT id, sector_id, name, description, sort_order, created_at
            FROM sector_categories
            WHERE sector_id = ?
            ORDER BY sort_order, created_at
            """,
            [sector_id],
        ).fetchall()

        return [
            {
                "id": row[0],
                "sector_id": row[1],
                "name": row[2],
                "description": row[3],
                "sort_order": row[4],
                "created_at": row[5],
            }
            for row in results
        ]

    def add_stock_to_sector(
        self,
        symbol: str,
        stock_name: str,
        sector_id: int,
        category_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> int:
        """添加股票到板块.

        Args:
            symbol: 股票代码
            stock_name: 股票名称
            sector_id: 板块ID
            category_id: 子分类ID（可选）
            notes: 备注

        Returns:
            映射ID
        """
        # 清理股票代码，确保是正确的字符串格式
        symbol = self._normalize_symbol(symbol)

        # 检查是否已存在
        conn = self.db.get_connection()
        existing = conn.execute(
            """
            SELECT id FROM stock_sector_mapping
            WHERE symbol = ? AND sector_id = ? AND (category_id = ? OR (category_id IS NULL AND ? IS NULL))
            """,
            [symbol, sector_id, category_id, category_id],
        ).fetchone()

        if existing:
            logger.debug(f"Stock {symbol} already in sector {sector_id}, category {category_id}")
            return existing[0]

        result = conn.execute(
            """
            INSERT INTO stock_sector_mapping (symbol, stock_name, sector_id, category_id, notes)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            [symbol, stock_name, sector_id, category_id, notes],
        ).fetchone()

        mapping_id = result[0]
        logger.info(f"Added stock {symbol} ({stock_name}) to sector {sector_id}")
        return mapping_id

    def get_stocks_by_sector(self, sector_id: int) -> list[dict[str, Any]]:
        """获取板块的所有股票.

        Args:
            sector_id: 板块ID

        Returns:
            股票列表（含子分类信息）
        """
        conn = self.db.get_connection()
        results = conn.execute(
            """
            SELECT
                m.id, m.symbol, m.stock_name, m.sector_id,
                m.category_id, c.name as category_name,
                m.notes, m.created_at
            FROM stock_sector_mapping m
            LEFT JOIN sector_categories c ON m.category_id = c.id
            WHERE m.sector_id = ?
            ORDER BY c.sort_order, m.created_at
            """,
            [sector_id],
        ).fetchall()

        def clean_symbol(symbol):
            """清理股票代码，移除浮点数格式的 .0 后缀"""
            if not symbol:
                return ""

            symbol_str = str(symbol)

            # 如果是浮点数格式（如 "2354.0"），转换为整数字符串
            if '.' in symbol_str and symbol_str.replace('.', '').isdigit():
                # 移除 .0 后缀，保留前导零
                symbol_str = symbol_str.split('.')[0]

            # 确保6位股票代码有前导零
            if symbol_str.isdigit() and len(symbol_str) < 6:
                symbol_str = symbol_str.zfill(6)

            return symbol_str

        return [
            {
                "id": row[0],
                "symbol": clean_symbol(row[1]),
                "stock_name": row[2],
                "sector_id": row[3],
                "category_id": row[4],
                "category_name": row[5],
                "notes": row[6],
                "created_at": row[7],
            }
            for row in results
        ]

    def get_sectors_by_stock(self, symbol: str) -> list[dict[str, Any]]:
        """获取股票所属的所有板块.

        Args:
            symbol: 股票代码

        Returns:
            板块列表
        """
        conn = self.db.get_connection()
        results = conn.execute(
            """
            SELECT
                s.id, s.name, s.category, s.description,
                c.id as category_id, c.name as category_name
            FROM stock_sector_mapping m
            JOIN sectors s ON m.sector_id = s.id
            LEFT JOIN sector_categories c ON m.category_id = c.id
            WHERE m.symbol = ?
            ORDER BY s.created_at DESC
            """,
            [symbol],
        ).fetchall()

        return [
            {
                "sector_id": row[0],
                "sector_name": row[1],
                "sector_category": row[2],
                "sector_description": row[3],
                "category_id": row[4],
                "category_name": row[5],
            }
            for row in results
        ]

    def delete_sector(self, sector_id: int) -> bool:
        """删除板块（级联删除子分类和映射）.

        Args:
            sector_id: 板块ID

        Returns:
            是否成功
        """
        conn = self.db.get_connection()

        # 先删除股票映射（需要先获取所有子分类ID）
        categories = self.get_categories_by_sector(sector_id)
        category_ids = [cat["id"] for cat in categories]

        # 删除所有相关股票映射
        for cat_id in category_ids:
            conn.execute(
                "DELETE FROM stock_sector_mapping WHERE category_id = ?",
                [cat_id]
            )

        # 删除所有子分类
        conn.execute(
            "DELETE FROM sector_categories WHERE sector_id = ?",
            [sector_id]
        )

        # 最后删除板块
        conn.execute("DELETE FROM sectors WHERE id = ?", [sector_id])

        logger.info(f"Deleted sector {sector_id} with {len(category_ids)} categories")
        return True

    def remove_stock_from_sector(self, symbol: str, sector_id: int) -> bool:
        """从板块中移除股票.

        Args:
            symbol: 股票代码
            sector_id: 板块ID

        Returns:
            是否成功
        """
        conn = self.db.get_connection()
        conn.execute(
            "DELETE FROM stock_sector_mapping WHERE symbol = ? AND sector_id = ?",
            [symbol, sector_id],
        )
        logger.info(f"Removed stock {symbol} from sector {sector_id}")
        return True
