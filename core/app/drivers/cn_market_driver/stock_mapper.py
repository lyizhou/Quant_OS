"""Stock Name to Code Mapper - 股票名称到代码的映射工具."""

from functools import lru_cache

import tushare as ts

from app.common.logging import logger


class StockNameMapper:
    """股票名称到代码的映射器（使用 Tushare）."""

    def __init__(self, token: str | None = None):
        """初始化映射器.

        Args:
            token: Tushare API token
        """
        self.token = token
        self._stock_map: dict[str, str] | None = None
        self._code_to_name: dict[str, str] | None = None

        if token:
            ts.set_token(token)
            self.pro = ts.pro_api()
        else:
            self.pro = None

    def _normalize_code(self, code: str | float | int) -> str:
        """标准化股票代码为6位字符串格式.

        Args:
            code: 股票代码（可能是字符串、浮点数或整数）

        Returns:
            标准化后的6位股票代码字符串

        Examples:
            1.0 -> "000001"
            "603667" -> "603667"
            603667 -> "603667"
        """
        if not code:
            return ""

        code_str = str(code)

        # 移除浮点数的小数部分
        if "." in code_str:
            code_str = code_str.split(".")[0]

        # 确保6位前导零
        if code_str.isdigit():
            code_str = code_str.zfill(6)

        return code_str

    @lru_cache(maxsize=1)
    def _load_stock_map(self) -> tuple[dict[str, str], dict[str, str]]:
        """加载股票名称到代码的映射（带缓存）.

        Returns:
            (name_to_code, code_to_name) 两个字典
        """
        if not self.pro:
            logger.warning("Tushare not initialized, cannot load stock map")
            return {}, {}

        try:
            logger.info("Loading stock name to code mapping from Tushare...")

            # 获取所有上市状态的股票
            df = self.pro.stock_basic(
                exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,market"
            )

            if df.empty:
                logger.warning("No stock data returned from Tushare")
                return {}, {}

            # 构建两个映射字典
            name_to_code = {}
            code_to_name = {}

            for _, row in df.iterrows():
                ts_code = row["ts_code"]  # 如 "603667.SH"
                symbol = row["symbol"]  # 如 "603667"
                name = row["name"]  # 如 "五洲新春"

                # 确保 symbol 是字符串格式（防止 Tushare 返回浮点数）
                symbol = str(symbol).split(".")[0] if "." in str(symbol) else str(symbol)

                # 确保6位前导零
                if symbol.isdigit():
                    symbol = symbol.zfill(6)

                # 名称 -> 6位代码
                name_to_code[name] = symbol

                # 6位代码 -> 名称
                code_to_name[symbol] = name

            logger.info(f"Loaded {len(name_to_code)} stock mappings from Tushare")
            return name_to_code, code_to_name

        except Exception as e:
            logger.error(f"Failed to load stock map from Tushare: {e}")
            return {}, {}

    def get_code_by_name(self, name: str) -> str | None:
        """根据股票名称获取6位代码.

        Args:
            name: 股票名称（如 "五洲新春"）

        Returns:
            6位股票代码（如 "603667"），找不到返回 None
        """
        if not name:
            return None

        # 加载映射（首次调用会从 Tushare 获取，后续使用缓存）
        name_to_code, _ = self._load_stock_map()

        # 精确匹配
        code = name_to_code.get(name.strip())
        if code:
            # 确保返回的是规范的6位字符串
            code = self._normalize_code(code)
            logger.debug(f"Found code for '{name}': {code}")
            return code

        # 模糊匹配（去除空格、括号等）
        normalized_name = name.strip().replace(" ", "").replace("（", "").replace("）", "")
        for stock_name, stock_code in name_to_code.items():
            normalized_stock_name = (
                stock_name.strip().replace(" ", "").replace("（", "").replace("）", "")
            )
            if normalized_name == normalized_stock_name:
                # 确保返回的是规范的6位字符串
                stock_code = self._normalize_code(stock_code)
                logger.debug(f"Found code for '{name}' (fuzzy match): {stock_code}")
                return stock_code

        logger.warning(f"No code found for stock name: '{name}'")
        return None

    def search_by_name(self, keyword: str, limit: int = 10) -> list[dict]:
        """根据关键词模糊搜索股票.

        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            匹配的股票列表，格式: [{"code": "600000", "name": "浦发银行"}, ...]
        """
        if not keyword:
            return []

        # 加载映射
        name_to_code, code_to_name = self._load_stock_map()

        results = []
        keyword_lower = keyword.lower().strip()

        # 1. 精确匹配
        for name, code in name_to_code.items():
            if keyword_lower in name.lower():
                results.append({"code": code, "name": name})
                if len(results) >= limit:
                    return results

        # 2. 如果精确匹配结果不足，尝试代码前缀匹配
        if len(results) < limit:
            for code, name in code_to_name.items():
                if code.startswith(keyword[:6]):  # 支持输入部分代码
                    # 避免重复
                    if not any(r["code"] == code for r in results):
                        results.append({"code": code, "name": name})
                    if len(results) >= limit:
                        break

        logger.info(f"Search '{keyword}' found {len(results)} results")
        return results

    def get_name_by_code(self, code: str) -> str | None:
        """根据6位代码获取股票名称.

        Args:
            code: 6位股票代码（如 "603667"）

        Returns:
            股票名称（如 "五洲新春"），找不到返回 None
        """
        if not code:
            return None

        # 加载映射
        _, code_to_name = self._load_stock_map()

        # 去除可能的交易所后缀
        clean_code = code.split(".")[0] if "." in code else code

        name = code_to_name.get(clean_code)
        if name:
            logger.debug(f"Found name for '{code}': {name}")
        else:
            logger.warning(f"No name found for stock code: '{code}'")

        return name

    def validate_and_fix_code(
        self, code: str | None, name: str, market_value: float | None = None
    ) -> str | None:
        """验证并修正股票代码.

        Args:
            code: LLM 提取的代码（可能为空或错误）
            name: 股票名称（必须提供）
            market_value: 市值（用于检测是否误识别）

        Returns:
            修正后的6位代码，找不到返回 None
        """
        # 1. 检查代码是否有效
        is_valid_code = (
            code
            and isinstance(code, str)
            and code.isdigit()
            and len(code) == 6
            and self._is_valid_stock_code_prefix(code)
        )

        # 2. 检查是否误识别为市值
        if code and market_value:
            # 如果代码等于市值的整数部分，说明识别错误
            if str(int(market_value)) == code:
                logger.warning(
                    f"Code '{code}' matches market value {market_value}, likely misidentified"
                )
                is_valid_code = False

        # 3. 如果代码无效，通过名称反查
        if not is_valid_code:
            if not name:
                logger.error("Both code and name are invalid, cannot fix")
                return None

            logger.info(f"Invalid code '{code}', attempting to fix via name '{name}'")
            fixed_code = self.get_code_by_name(name)

            if fixed_code:
                logger.info(f"✅ Fixed code via name '{name}': {code} -> {fixed_code}")
                return fixed_code
            else:
                logger.error(f"❌ Cannot find code for name '{name}'")
                return None

        # 4. 代码有效，直接返回
        return code

    def _is_valid_stock_code_prefix(self, code: str) -> bool:
        """检查股票代码前缀是否有效.

        Args:
            code: 6位股票代码

        Returns:
            是否有效
        """
        if not code or len(code) != 6:
            return False

        # 上海主板：600xxx-605xxx
        if code.startswith(("600", "601", "603", "605")):
            return True

        # 深圳主板：000xxx-002xxx
        if code.startswith(("000", "001", "002")):
            return True

        # 创业板：300xxx
        if code.startswith("300"):
            return True

        # 科创板：688xxx
        if code.startswith("688"):
            return True

        # 北交所：430xxx, 830xxx
        if code.startswith(("430", "830")):
            return True

        return False


# 全局单例（可选）
_mapper_instance: StockNameMapper | None = None


def get_stock_mapper(token: str | None = None) -> StockNameMapper:
    """获取全局 StockNameMapper 单例.

    Args:
        token: Tushare API token

    Returns:
        StockNameMapper 实例
    """
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = StockNameMapper(token)
    return _mapper_instance
