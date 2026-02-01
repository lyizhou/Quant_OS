# 题材库更新工具

该工具用于从外部接口获取最新的题材和板块数据，并更新到 Quant_OS 的数据库中。

## 目录结构

- `export_all_themes.py`: 主抓取脚本，遍历所有题材并导出到 Excel。
- `get_block_stocks.py`: 底层通信脚本，负责与题材库服务器建立 Socket 连接。
- `log.txt`: 包含登录题材库服务器所需的认证指令（Hex格式）。
- `全部题材股票明细.xlsx`: 抓取结果输出文件。

## 如何使用

### 1. 自动更新（推荐）

在项目根目录下运行 `update_sector_db.py`：

```bash
# 基础用法
uv run python update_sector_db.py

# 指定包含 log.txt 的源目录进行更新（如果需要更新登录凭证）
uv run python update_sector_db.py "F:\Path\To\Source\Files"
```

该脚本会自动执行以下步骤：
1. (可选) 从源目录复制最新的 `log.txt`。
2. 运行 `export_all_themes.py` 抓取最新数据并生成 Excel。
3. 运行 `core/scripts/import_themes.py` 将 Excel 数据导入数据库。

### 2. 手动分步执行

如果需要调试或分步执行：

**第一步：抓取数据**
```bash
cd tools/theme_library
uv run python export_all_themes.py
```
这将在当前目录下生成 `全部题材股票明细.xlsx`。

**第二步：导入数据库**
```bash
cd ../..
uv run python core/scripts/import_themes.py tools/theme_library/全部题材股票明细.xlsx
```

## 注意事项

- `log.txt` 中的登录指令可能会过期。如果抓取失败，尝试更新该文件。
- 抓取过程可能需要几分钟，请耐心等待。
