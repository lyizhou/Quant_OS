# 资金流向桑基图功能 - 快速参考

## 一分钟快速上手

### 1. 在Telegram中使用
```
/mf
```

### 2. 你会收到两张图
- **简单桑基图**: 市场资金 → 各板块
- **详细桑基图**: 市场资金 → 资金类型 → 各板块

### 3. 图表说明
- 🟢 绿色 = 资金流入
- 🔴 红色 = 资金流出
- 🟠 超大单 = 机构
- 🟢 大单 = 大户
- 🔴 中单 = 中户
- 🟣 小单 = 散户

## 配置要求

### 必需
```bash
# .env 文件
TG_BOT_TOKEN=your_token
TG_CHAT_ID=your_chat_id
TUSHARE_TOKEN=your_tushare_token
```

### Tushare积分
- **最低**: 0分（使用概念板块）
- **推荐**: 120分（完整功能）
- **最佳**: 2000分（行业分类）

## 启用自动推送

在 `run_telegram_bot.py` 第92行后添加：

```python
# 启用资金流向桑基图定时任务
try:
    from app.jobs.daily_money_flow_job import create_daily_money_flow_job
    import os
    from telegram import Bot

    tg_bot_token = os.getenv("TG_BOT_TOKEN")
    tg_chat_id = os.getenv("TG_CHAT_ID")

    if tg_bot_token and tg_chat_id:
        telegram_bot = Bot(token=tg_bot_token)
        money_flow_job = create_daily_money_flow_job(
            bot=telegram_bot,
            chat_id=tg_chat_id
        )
        money_flow_job.start()
        logger.info("✓ Money flow sankey chart scheduler initialized")
except Exception as e:
    logger.warning(f"⚠ Failed to initialize money flow scheduler: {e}")
```

**推送时间**: 每个交易日 17:30

## 常见问题

### Q: 权限不足怎么办？
A: 系统会自动降级到概念板块方案，仍可使用

### Q: 生成时间太长？
A: 正常需要30-60秒，请耐心等待

### Q: 非交易日能用吗？
A: 会自动获取最后一个交易日的数据

### Q: 如何测试？
```bash
uv run python test_money_flow_simple.py
```

## 相关命令

| 命令 | 说明 |
|------|------|
| `/mf` | 资金流向桑基图 |
| `/refresh` | 刷新数据 |
| `/help` | 帮助 |

## 文件位置

```
core/app/services/
├── money_flow_service.py      # 数据服务
└── sankey_chart_service.py    # 图表生成

core/app/jobs/
└── daily_money_flow_job.py    # 定时任务

drivers/telegram_bot/
└── bot_server_v2.py           # Bot命令

data/charts/
├── money_flow_sankey_*.png    # 简单图
└── money_flow_detailed_sankey_*.png  # 详细图
```

## 技术栈

- **数据**: Tushare API
- **可视化**: Plotly
- **导出**: Kaleido
- **定时**: APScheduler
- **推送**: python-telegram-bot

---

**版本**: v1.0.0 | **日期**: 2026-01-23
