"""Test suite for stock symbol normalization fixes."""

import pytest

from app.data.repositories.sector_repo import SectorRepository
from app.drivers.cn_market_driver.stock_mapper import StockNameMapper


class TestSymbolNormalization:
    """测试股票代码标准化功能."""

    def test_sector_repo_normalize_symbol(self):
        """测试 SectorRepository._normalize_symbol() 方法."""
        repo = SectorRepository()

        # 测试浮点数格式
        assert repo._normalize_symbol("1.0") == "000001"
        assert repo._normalize_symbol("100.0") == "000100"
        assert repo._normalize_symbol("600000.0") == "600000"

        # 测试整数格式
        assert repo._normalize_symbol(1) == "000001"
        assert repo._normalize_symbol(100) == "000100"
        assert repo._normalize_symbol(600000) == "600000"

        # 测试字符串格式
        assert repo._normalize_symbol("000001") == "000001"
        assert repo._normalize_symbol("600000") == "600000"
        assert repo._normalize_symbol("1") == "000001"
        assert repo._normalize_symbol("100") == "000100"

        # 测试边界情况
        assert repo._normalize_symbol("") == ""
        assert repo._normalize_symbol(None) == ""

    def test_stock_mapper_normalize_code(self):
        """测试 StockNameMapper._normalize_code() 方法."""
        mapper = StockNameMapper()

        # 测试浮点数格式
        assert mapper._normalize_code("1.0") == "000001"
        assert mapper._normalize_code("100.0") == "000100"
        assert mapper._normalize_code("600000.0") == "600000"

        # 测试整数格式
        assert mapper._normalize_code(1) == "000001"
        assert mapper._normalize_code(100) == "000100"
        assert mapper._normalize_code(600000) == "600000"

        # 测试字符串格式
        assert mapper._normalize_code("000001") == "000001"
        assert mapper._normalize_code("600000") == "600000"

        # 测试边界情况
        assert mapper._normalize_code("") == ""
        assert mapper._normalize_code(None) == ""

    def test_common_float_symbols(self):
        """测试常见的浮点数格式股票代码."""
        repo = SectorRepository()

        # 深圳主板常见代码
        test_cases = [
            ("1.0", "000001"),      # 平安银行
            ("2.0", "000002"),      # 万科A
            ("100.0", "000100"),    # TCL科技
            ("333.0", "000333"),    # 美的集团
            ("858.0", "000858"),    # 五粮液

            # 上海主板常见代码
            ("600000.0", "600000"), # 浦发银行
            ("600036.0", "600036"), # 招商银行
            ("600519.0", "600519"), # 贵州茅台

            # 创业板
            ("300059.0", "300059"), # 东方财富
            ("300750.0", "300750"), # 宁德时代

            # 科创板
            ("688111.0", "688111"), # 金山办公
        ]

        for float_symbol, expected in test_cases:
            result = repo._normalize_symbol(float_symbol)
            assert result == expected, f"Failed for {float_symbol}: got {result}, expected {expected}"

    def test_preserve_valid_symbols(self):
        """测试已经是正确格式的代码不会被改变."""
        repo = SectorRepository()

        valid_symbols = [
            "000001",
            "000002",
            "000100",
            "600000",
            "600519",
            "300059",
            "688111",
        ]

        for symbol in valid_symbols:
            result = repo._normalize_symbol(symbol)
            assert result == symbol, f"Valid symbol {symbol} was changed to {result}"


class TestSymbolValidation:
    """测试股票代码验证功能."""

    def test_valid_symbols(self):
        """测试有效的股票代码."""
        from scripts.validate_stock_symbols import validate_symbol_format

        valid_symbols = [
            "000001",  # 深圳主板
            "000002",
            "002594",  # 中小板
            "300059",  # 创业板
            "600000",  # 上海主板
            "601398",
            "603288",
            "688111",  # 科创板
        ]

        for symbol in valid_symbols:
            is_valid, error = validate_symbol_format(symbol)
            assert is_valid, f"Valid symbol {symbol} failed validation: {error}"

    def test_invalid_symbols(self):
        """测试无效的股票代码."""
        from scripts.validate_stock_symbols import validate_symbol_format

        invalid_symbols = [
            ("1.0", "decimal point"),
            ("100.0", "decimal point"),
            ("1", "length"),
            ("12345", "length"),
            ("1234567", "length"),
            ("abcdef", "non-digit"),
            ("999999", "invalid prefix"),
        ]

        for symbol, reason in invalid_symbols:
            is_valid, error = validate_symbol_format(symbol)
            assert not is_valid, f"Invalid symbol {symbol} passed validation (reason: {reason})"


class TestDataIntegrity:
    """测试数据完整性."""

    def test_add_stock_with_float_symbol(self):
        """测试使用浮点数格式添加股票，应该自动标准化."""
        # 这个测试需要数据库连接，实际运行时需要 mock
        # 这里仅作为示例

        # repo = SectorRepository()
        # sector_id = repo.create_sector("测试板块", "测试分类")
        #
        # # 使用浮点数格式添加股票
        # mapping_id = repo.add_stock_to_sector(
        #     symbol="1.0",  # 浮点数格式
        #     stock_name="平安银行",
        #     sector_id=sector_id,
        # )
        #
        # # 读取回来验证
        # stocks = repo.get_stocks_by_sector(sector_id)
        # assert len(stocks) == 1
        # assert stocks[0]["symbol"] == "000001"  # 应该被标准化为正确格式

        pass  # 需要实际数据库环境才能运行


class TestCleanSymbolFunction:
    """测试修复脚本中的 clean_symbol 函数."""

    def test_clean_symbol(self):
        """测试 fix_float_symbols.py 中的 clean_symbol 函数."""
        from scripts.fix_float_symbols import clean_symbol

        # 测试浮点数格式
        assert clean_symbol(1.0) == "000001"
        assert clean_symbol(100.0) == "000100"
        assert clean_symbol(600000.0) == "600000"

        # 测试字符串格式
        assert clean_symbol("1.0") == "000001"
        assert clean_symbol("100.0") == "000100"
        assert clean_symbol("600000.0") == "600000"

        # 测试整数
        assert clean_symbol(1) == "000001"
        assert clean_symbol(100) == "000100"

        # 测试已经正确的格式
        assert clean_symbol("000001") == "000001"
        assert clean_symbol("600000") == "600000"

        # 测试空值
        assert clean_symbol("") == ""
        assert clean_symbol(None) == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
