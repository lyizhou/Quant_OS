# 资金流向桑基图功能 - 使用指南

## 功能简介

资金流向桑基图功能可以直观展示A股市场当日资金在各板块间的流动情况，帮助你快速了解市场资金动向。

## 快速开始

### 1. 在Telegram中使用

#### 方法一：使用快捷命令（推荐）
```
/mf
```

#### 方法二：使用完整命令
```
/moneyflow
```

### 2. 查看结果

命令执行后，你会收到两张桑基图：

#### 简单桑基图
- 展示市场总资金流向各板块的情况
- 🟢 绿色箭头：资金流入的板块
- 🔴 红色箭头：资金流出的板块
- 显示前10个流入/流出板块

#### 详细桑基图
- 展示不同资金类型的流向
- 🟠 超大单资金（机构）
- 🟢 大单资金（大户）
- 🔴 中单资金（中户）
- 🟣 小单资金（散户）
- 显示前8个流入/流出板块

## 自动推送设置

### 启用每日自动推送

编辑 `run_telegram_bot.py`，在第92行之后添加以下代码：

```python
# 启用资金流向桑基图定时任务
try:
    from app.jobs.daily_money_flow_job import create_daily_money_flow_job
    import os

    tg_bot_token = os.getenv("TG_BOT_TOKEN")
    tg_chat_id = os.getenv("TG_CHAT_ID")

    if tg_bot_token and tg_chat_id:
        from telegram import Bot

        telegram_bot = Bot(token=tg_bot_token)
        money_flow_job = create_daily_money_flow_job(
            bot=telegram_bot,
            chat_id=tg_chat_id
        )
        money_flow_job.start()
        logger.info("✓ Money flow sankey chart scheduler initialized")
        logger.info("  - Daily push: 17:30 (after market close)")
    else:
        logger.warning("⚠ Telegram config not found, money flow auto-push disabled")
except Exception as e:
    logger.warning(f"⚠ Failed to initialize money flow scheduler: {e}")
```

### 推送时间

- **默认时间**: 每个交易日 17:30（收盘后2.5小时）
- **时区**: Asia/Shanghai

### 修改推送时间

编辑 `core/app/jobs/daily_money_flow_job.py`，修改第115-121行：

```python
# 修改为你想要的时间，例如 16:00
self.scheduler.add_job(
    self.send_daily_money_flow,
    trigger="cron",
    hour=16,      # 修改小时
    minute=0,     # 修改分钟
    timezone="Asia/Shanghai",
    id="daily_money_flow",
    name="每日资金流向桑基图",
    replace_existing=True,
)
```

## 配置要求

### 必需配置

在 `.env` 文件中配置以下环境变量：

```bash
# Telegram Bot配置
TG_BOT_TOKEN=your_telegram_bot_token
TG_CHAT_ID=your_telegram_chat_id

# Tushare配置（必需）
TUSHARE_TOKEN=your_tushare_token
```

### Tushare权限要求

资金流向数据需要Tushare积分权限：

| 接口 | 所需积分 | 说明 |
|------|---------|------|
| `moneyflow` | 120分 | 个股资金流向数据 |
| `index_classify` | 2000分 | 行业分类数据 |
| `concept` | 0分 | 概念板块数据（备用） |

**如果积分不足**：
- 系统会自动降级到概念板块方案
- 数据可能不够全面，但仍可使用

**如何获取积分**：
1. 访问 [Tushare积分商城](https://tushare.pro/document/1?doc_id=13)
2. 通过充值或贡献获取积分
3. 推荐至少获取120分以使用基础功能

## 常见问题

### Q1: 命令执行失败，提示权限不足

**原因**: Tushare账户积分不足

**解决方案**:
1. 检查你的Tushare账户积分
2. 如果积分不足，考虑充值或使用备用方案
3. 系统会自动尝试使用概念板块数据

### Q2: 生成时间过长（超过60秒）

**原因**:
- 网络连接较慢
- Tushare API响应慢
- 板块数量较多

**解决方案**:
1. 检查网络连接
2. 稍后重试
3. 考虑减少板块数量（修改 `top_n` 参数）

### Q3: 非交易日无法生成

**原因**: 非交易日没有资金流向数据

**解决方案**:
- 等待下一个交易日
- 系统会自动获取最后一个交易日的数据

### Q4: 图表显示不完整

**原因**:
- 部分板块数据缺失
- API返回数据不完整

**解决方案**:
1. 使用 `/refresh` 命令更新数据
2. 稍后重试
3. 检查Tushare API状态

## 高级用法

### 编程调用

如果你想在代码中使用这个功能：

```python
from app.services.sankey_chart_service import SankeyChartService
from datetime import datetime

# 创建服务
service = SankeyChartService()

# 生成简单桑基图
simple_path = service.generate_money_flow_sankey(
    date=datetime(2026, 1, 23),  # 指定日期
    top_n=10,                     # 显示前10个板块
    output_path="my_chart.png"    # 自定义输出路径
)

# 生成详细桑基图
detailed_path = service.generate_detailed_sankey(
    date=None,                    # None = 最后一个交易日
    top_n=8,                      # 显示前8个板块
)

print(f"图表已保存到: {simple_path}")
```

### 自定义板块数量

修改 `core/app/services/sankey_chart_service.py` 中的默认参数：

```python
def generate_money_flow_sankey(
    self,
    date: datetime | None = None,
    top_n: int = 15,  # 修改为15个板块
    output_path: str | None = None,
) -> str:
    ...
```

### 修改图表样式

在 `_create_sankey_figure()` 方法中修改：

```python
# 修改颜色
node_colors = ["#1f77b4"]  # 市场总资金节点颜色
node_colors.append("#2ca02c")  # 流入板块颜色
node_colors.append("#d62728")  # 流出板块颜色

# 修改图表尺寸
fig.write_image(output_path, width=1600, height=1000, scale=2)

# 修改字体
fig.update_layout(
    font=dict(size=14, family="Microsoft YaHei, Arial"),
)
```

## 数据说明

### 资金类型定义

| 类型 | 定义 | 代表投资者 |
|------|------|-----------|
| 超大单 | 单笔成交 ≥ 100万元 | 机构投资者 |
| 大单 | 50万元 ≤ 单笔成交 < 100万元 | 大户投资者 |
| 中单 | 10万元 ≤ 单笔成交 < 50万元 | 中户投资者 |
| 小单 | 单笔成交 < 10万元 | 散户投资者 |

### 主力资金

主力资金 = 超大单 + 大单

通常认为主力资金代表机构和大户的操作方向。

### 净流入计算

净流入 = 买入金额 - 卖出金额

- 正值：资金流入
- 负值：资金流出

## 性能优化建议

### 1. 减少API调用

```python
# 在 money_flow_service.py 中修改
stock_codes = stock_codes[:30]  # 减少到30只股票
```

### 2. 使用缓存

```python
# 添加简单的缓存机制
from functools import lru_cache
from datetime import date

@lru_cache(maxsize=10)
def get_cached_money_flow(trade_date: date):
    return service.get_sector_money_flow(date=trade_date)
```

### 3. 异步处理

```python
# 使用异步获取数据
import asyncio

async def fetch_sector_data(sector):
    # 异步获取数据
    pass

# 并行处理多个板块
results = await asyncio.gather(*[
    fetch_sector_data(s) for s in sectors
])
```

## 故障排查

### 查看日志

日志文件位置：
- 控制台输出
- 使用 `logger.info()` 查看详细信息

### 测试功能

运行测试脚本：

```bash
# 基础测试（不需要API）
uv run python test_money_flow_simple.py

# 完整测试（需要API）
uv run python test_money_flow_sankey.py
```

### 检查配置

```bash
# 检查环境变量
python -c "import os; print('TUSHARE_TOKEN:', bool(os.getenv('TUSHARE_TOKEN')))"
python -c "import os; print('TG_BOT_TOKEN:', bool(os.getenv('TG_BOT_TOKEN')))"
```

## 相关命令

| 命令 | 说明 |
|------|------|
| `/mf` | 生成资金流向桑基图（快捷） |
| `/moneyflow` | 生成资金流向桑基图（完整） |
| `/refresh` | 刷新所有数据 |
| `/status` | 查看数据更新状态 |
| `/help` | 查看帮助信息 |

## 更新日志

### v1.0.0 (2026-01-23)
- ✅ 初始版本发布
- ✅ 支持简单和详细两种桑基图
- ✅ 支持手动触发和自动推送
- ✅ 完善的错误处理和用户提示
- ✅ 支持行业分类和概念板块两种数据源

## 反馈与支持

如果遇到问题或有改进建议：

1. 查看日志文件
2. 运行测试脚本诊断
3. 检查Tushare API状态
4. 提交Issue到项目仓库

---

**最后更新**: 2026-01-23
**版本**: v1.0.0
