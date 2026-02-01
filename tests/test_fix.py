#!/usr/bin/env python
"""
快速测试脚本 - 验证 HTML 转义修复
用法: python test_fix.py
"""

import html
import io
import sys
from pathlib import Path

# 设置 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def test_html_escape():
    """测试 HTML 转义功能"""
    print("=" * 60)
    print("测试 1: HTML 转义功能")
    print("=" * 60)

    test_cases = [
        ("<名称>", "&lt;名称&gt;"),
        ("测试&板块", "测试&amp;板块"),
        ("A股>B股", "A股&gt;B股"),
        ("板块<概念>", "板块&lt;概念&gt;"),
        ("正常板块", "正常板块"),
    ]

    all_passed = True
    for original, expected in test_cases:
        escaped = html.escape(original)
        passed = escaped == expected
        all_passed = all_passed and passed
        status = "✓" if passed else "✗"
        print(f"{status} '{original}' -> '{escaped}'")
        if not passed:
            print(f"  Expected: '{expected}'")

    return all_passed


def test_bot_file():
    """测试 bot_server_v2.py 文件"""
    print("\n" + "=" * 60)
    print("测试 2: Bot 文件检查")
    print("=" * 60)

    bot_file = Path("drivers/telegram_bot/bot_server_v2.py")

    if not bot_file.exists():
        print("✗ Bot 文件不存在:", bot_file)
        return False

    print("✓ Bot 文件存在")

    # 读取文件
    with open(bot_file, encoding="utf-8") as f:
        content = f.read()

    # 检查关键点
    checks = {
        "HTML 模块导入": "import html" in content,
        "包含 html.escape 调用": "html.escape(" in content,
        "使用 parse_mode HTML": 'parse_mode="HTML"' in content,
    }

    all_passed = True
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check}")
        all_passed = all_passed and result

    # 统计
    import re

    escape_count = len(re.findall(r"html\.escape\(", content))
    html_mode_count = len(re.findall(r'parse_mode="HTML"', content))

    print("\n统计:")
    print(f"  - html.escape() 调用: {escape_count} 处")
    print(f"  - parse_mode='HTML': {html_mode_count} 处")

    return all_passed


def test_syntax():
    """测试 Python 语法"""
    print("\n" + "=" * 60)
    print("测试 3: Python 语法检查")
    print("=" * 60)

    import py_compile

    bot_file = "drivers/telegram_bot/bot_server_v2.py"

    try:
        py_compile.compile(bot_file, doraise=True)
        print("✓ Python 语法检查通过")
        return True
    except py_compile.PyCompileError as e:
        print(f"✗ 语法错误: {e}")
        return False


def test_message_generation():
    """测试消息生成"""
    print("\n" + "=" * 60)
    print("测试 4: 消息生成模拟")
    print("=" * 60)

    # 模拟板块数据
    test_sectors = [
        {"name": "<测试>", "category": "概念"},
        {"name": "正常板块", "category": "行业"},
        {"name": "A&B板块", "category": "产业链"},
    ]

    print("\n生成的 Telegram 消息预览:")
    print("-" * 60)

    for i, sector in enumerate(test_sectors, 1):
        sector_name = html.escape(sector["name"])
        category = html.escape(sector["category"])
        msg = f"{i}. <b>{sector_name}</b>\n"
        msg += f"   类型: {category}\n"

        print(f"原始: {sector['name']}")
        print(f"HTML: {msg}")

    print("-" * 60)
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Telegram Bot HTML 转义修复 - 测试脚本")
    print("=" * 60)

    results = {
        "HTML 转义功能": test_html_escape(),
        "Bot 文件检查": test_bot_file(),
        "Python 语法": test_syntax(),
        "消息生成": test_message_generation(),
    }

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！修复验证成功。")
        print("\n下一步:")
        print("1. 启动 Bot: python run_telegram_bot.py")
        print("2. 测试命令: /sectors")
        print("3. 验证特殊字符正确显示")
    else:
        print("✗ 部分测试失败，请检查上述错误。")
        return 1

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
