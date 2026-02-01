# 🚀 生产部署实施指南

## 当前状态检查

✅ **已完成**:
- Python 环境配置
- 代码实现完成
- Telegram 配置就绪
- 依赖包已安装

⚠️ **待完成**:
- PostgreSQL 数据库安装
- 数据库初始化
- 系统测试
- 调度器部署

---

## 📋 部署步骤（Windows）

### 步骤 1: 安装 PostgreSQL

#### 方法 A: 使用安装程序（推荐）

1. **下载 PostgreSQL**
   - 访问: https://www.postgresql.org/download/windows/
   - 下载 PostgreSQL 15 或更高版本
   - 运行安装程序

2. **安装配置**
   - 端口: 5432（默认）
   - 超级用户密码: 设置一个强密码（记住它！）
   - 区域设置: 默认
   - 组件: 全部安装

3. **验证安装**
   ```powershell
   # 打开 PowerShell
   psql --version
   # 应该显示: psql (PostgreSQL) 15.x
   ```

#### 方法 B: 使用 Chocolatey

```powershell
# 以管理员身份运行 PowerShell
choco install postgresql

# 启动服务
net start postgresql-x64-15
```

---

### 步骤 2: 创建数据库

```powershell
# 打开 PowerShell，连接到 PostgreSQL
psql -U postgres

# 在 psql 提示符中执行:
CREATE DATABASE quant_os;
CREATE USER quant_user WITH PASSWORD 'YourSecurePassword123!';
GRANT ALL PRIVILEGES ON DATABASE quant_os TO quant_user;
\q
```

---

### 步骤 3: 更新 .env 文件

在项目根目录的 `.env` 文件中更新数据库配置:

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=quant_user
DB_PASSWORD=YourSecurePassword123!
DB_NAME=quant_os

# 其他配置保持不变
TG_BOT_TOKEN=7926271701...
TG_CHAT_ID=400804364
DEEPSEEK_API_KEY=your_key
TUSHARE_TOKEN=your_token
TZ=Asia/Taipei
DAILY_REPORT_TIME=08:30
US_DATA_SOURCE=yfinance
CN_DATA_SOURCE=tushare
```

---

### 步骤 4: 初始化数据库

```powershell
# 在项目根目录运行
uv run python core/scripts/init_db.py
```

**预期输出**:
```
=== Database Initialization ===
Database: localhost:5432/quant_os
✅ Database connection successful
Running migration: 0001_init.sql
✅ 0001_init.sql completed
Running migration: 0002_indexes.sql
✅ 0002_indexes.sql completed
Loading seed data...
✅ Loaded 10 mapping chains
=== Verification ===
System version: 2.0.0
Mapping chains: 10
✅ Database initialization complete!
```

---

### 步骤 5: 系统健康检查

```powershell
uv run python core/scripts/doctor.py
```

**预期输出**:
```
╔════════════════════════════════════════╗
║   Quant_OS System Health Check        ║
╚════════════════════════════════════════╝

=== Environment Check ===
✅ All required environment variables present

=== Database Check ===
Connecting to: localhost:5432/quant_os
✅ Database connection successful
✅ All required tables present: mapping_chains, narrative_signals, user_portfolio, system_config

=== Telegram Check ===
✅ Bot token valid: @YourBotName

=== API Keys Check ===
✅ DeepSeek API key present
✅ Tushare token present

=== Summary ===
✅ PASS: Environment
✅ PASS: Database
✅ PASS: Telegram
✅ PASS: API Keys

🎉 All checks passed! System is ready.
```

---

### 步骤 6: 测试真实数据报告

```powershell
uv run python core/scripts/test_mapping_report.py
```

这将:
- 从 yfinance 获取真实美股数据
- 使用数据库中的 10 条映射链条
- 生成实际的映射报告
- 在控制台显示结果

---

### 步骤 7: 测试 Telegram Bot（交互模式）

**终端 1 - 启动 Bot**:
```powershell
uv run python core/app/shell/bot.py
```

**预期输出**:
```
============================================================
Quant_OS Telegram Bot v2.0
============================================================

[配置摘要...]

Bot is running. Press Ctrl+C to stop.
```

**在 Telegram 中测试**:
1. 打开 Telegram
2. 找到你的 bot
3. 发送 `/start`
4. 点击 "🇺🇸 美股映射"
5. 等待报告生成（5-10秒）
6. 查看完整报告

---

### 步骤 8: 测试定时任务

```powershell
# 立即执行一次定时任务（不等待 8:30）
uv run python core/scripts/test_daily_job.py
```

这将:
- 生成报告
- 发送到你的 Telegram
- 验证端到端流程

检查你的 Telegram，应该收到一条带有 "🔔 测试推送" 的消息。

---

### 步骤 9: 部署调度器

#### 方法 A: 前台运行（测试用）

**终端 2 - 启动调度器**:
```powershell
uv run python core/app/jobs/scheduler.py
```

**预期输出**:
```
============================================================
Quant_OS Task Scheduler v2.0
============================================================

[配置摘要...]

✅ Database connected

Scheduled jobs (1):
  - Daily US Mapping Report (ID: daily_us_mapping)
    Next run: 2026-01-18 08:30:00+08:00

Scheduler is running. Press Ctrl+C to stop.
```

#### 方法 B: 后台运行（生产用）

**使用 NSSM（推荐）**:

1. 安装 NSSM:
```powershell
choco install nssm
```

2. 创建服务:
```powershell
# 找到 uv.exe 路径
where uv

# 创建服务（替换路径）
nssm install QuantScheduler "C:\Users\YourUser\.local\bin\uv.exe" "run python core/app/jobs/scheduler.py"
nssm set QuantScheduler AppDirectory "E:\Code\Quant_OS"
nssm set QuantScheduler DisplayName "Quant_OS Task Scheduler"
nssm set QuantScheduler Description "Automated daily US-CN mapping reports"

# 启动服务
nssm start QuantScheduler

# 查看状态
nssm status QuantScheduler
```

3. 管理服务:
```powershell
# 停止
nssm stop QuantScheduler

# 重启
nssm restart QuantScheduler

# 查看日志
nssm set QuantScheduler AppStdout "E:\Code\Quant_OS\scheduler.log"
nssm set QuantScheduler AppStderr "E:\Code\Quant_OS\scheduler_error.log"
```

---

### 步骤 10: 验证部署

#### 立即验证
- [ ] 数据库初始化成功（10 条链条）
- [ ] 健康检查全部通过
- [ ] 测试报告生成成功
- [ ] Telegram Bot 响应 /start
- [ ] 交互式报告正常工作
- [ ] 测试定时任务发送成功
- [ ] 调度器正在运行

#### 第二天验证（8:30 AM）
- [ ] 收到自动推送的日报
- [ ] 报告内容准确
- [ ] 信号分类合理
- [ ] 无错误日志

---

## 🔧 故障排查

### 问题 1: 数据库连接失败

**症状**: `connection refused` 或 `could not connect`

**解决**:
```powershell
# 检查 PostgreSQL 服务
net start postgresql-x64-15

# 测试连接
psql -U quant_user -d quant_os -h localhost

# 检查 .env 配置
type .env | findstr DB_
```

### 问题 2: Telegram Bot 无响应

**症状**: Bot 不回复消息

**解决**:
```powershell
# 验证 bot token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# 检查 bot 进程
tasklist | findstr python

# 重启 bot
# Ctrl+C 停止，然后重新运行
uv run python core/app/shell/bot.py
```

### 问题 3: 调度器未执行

**症状**: 8:30 没有收到报告

**解决**:
```powershell
# 检查时区
python -c "from app.common.time import now; print(now())"

# 检查调度器日志
type scheduler.log | findstr "Daily US mapping"

# 手动触发测试
uv run python core/scripts/test_daily_job.py
```

### 问题 4: 缺少 API Key

**症状**: `TUSHARE_TOKEN not set` 或类似错误

**解决**:
```powershell
# 检查 .env 文件
type .env

# 确保包含:
# TUSHARE_TOKEN=your_token
# DEEPSEEK_API_KEY=your_key

# 重启服务以加载新配置
```

---

## 📊 监控和维护

### 每日检查
```powershell
# 查看调度器日志
type scheduler.log | findstr "sent successfully"

# 查看错误日志
type scheduler_error.log
```

### 每周检查
- 检查信号准确性
- 更新映射链条（如需要）
- 备份数据库

### 数据库备份
```powershell
# 备份数据库
pg_dump -U quant_user -d quant_os > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -U quant_user -d quant_os < backup_20260117.sql
```

---

## ✅ 部署完成检查清单

完成以下所有项目后，部署即完成:

- [ ] PostgreSQL 已安装并运行
- [ ] 数据库已创建（quant_os）
- [ ] .env 文件已更新
- [ ] 数据库已初始化（10 条链条）
- [ ] 健康检查全部通过
- [ ] 测试报告生成成功
- [ ] Telegram Bot 可以交互
- [ ] 定时任务测试成功
- [ ] 调度器已部署（前台或后台）
- [ ] 已收到第一次 8:30 推送

---

## 🎉 成功标准

当满足以下条件时，部署成功:

1. ✅ 每天 8:30 准时收到日报
2. ✅ 报告包含真实市场数据
3. ✅ 信号分类准确可用
4. ✅ Bot 交互响应正常
5. ✅ 系统连续运行 7 天无错误

---

## 📞 需要帮助？

如果遇到问题:

1. 查看日志文件
2. 运行健康检查
3. 检查文档: `core/DEPLOYMENT.md`
4. 逐个测试组件

---

**准备好了吗？让我们从步骤 1 开始！**

请告诉我您当前的进度，我会继续指导您。
