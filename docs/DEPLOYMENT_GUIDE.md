# Quant_OS v2.0.0 部署指南

完整的部署和测试指南，帮助您快速启动 Quant_OS API 服务。

---

## 目录

1. [环境准备](#环境准备)
2. [安装依赖](#安装依赖)
3. [配置环境变量](#配置环境变量)
4. [初始化数据库](#初始化数据库)
5. [启动 API 服务](#启动-api-服务)
6. [测试 API](#测试-api)
7. [OpenClaw 集成](#openclaw-集成)
8. [生产环境部署](#生产环境部署)
9. [故障排除](#故障排除)

---

## 环境准备

### 系统要求

- **Python**: 3.12+ (推荐) 或 3.9+
- **操作系统**: Windows / macOS / Linux
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘空间**: 最低 500MB

### 安装 Python

**Windows:**
```powershell
# 从 python.org 下载安装包
# 或使用 winget
winget install Python.Python.3.12
```

**macOS:**
```bash
brew install python@3.12
```

**Linux:**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
```

### 安装 uv (推荐)

uv 是一个快速的 Python 包管理器：

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 安装依赖

### 方法 1: 使用 uv (推荐)

```bash
cd Quant_OS
uv sync
```

如果遇到文件锁定问题：
```bash
# 删除 .venv 目录重新安装
rm -rf .venv
uv sync
```

### 方法 2: 使用 pip

```bash
cd Quant_OS
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装依赖
pip install -e .
```

### 验证安装

```bash
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import loguru; print('Loguru installed')"
python -c "import duckdb; print('DuckDB:', duckdb.__version__)"
```

---

## 配置环境变量

### 1. 复制配置模板

```bash
cp .env.example .env
```

### 2. 编辑 .env 文件

```bash
# API 配置 (必需)
QUANT_OS_API_KEY=your_secure_api_key_here  # 生成一个安全的随机密钥
QUANT_OS_API_HOST=0.0.0.0
QUANT_OS_API_PORT=8000

# 市场数据 (必需)
TUSHARE_TOKEN=your_tushare_token  # 从 https://tushare.pro/ 获取

# AI 视觉识别 (必需 - 三选一)
ZHIPU_API_KEY=your_glm4v_api_key  # 推荐：https://open.bigmodel.cn/
# OPENAI_API_KEY=your_openai_api_key
# ANTHROPIC_API_KEY=your_anthropic_key

# 新闻搜索 (可选)
PERPLEXITY_API_KEY=your_perplexity_key

# 数据库
DB_PATH=core/data/db/quant_os.duckdb

# 日志
LOG_LEVEL=INFO
```

### 3. 生成 API 密钥

**Python 方式:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**OpenSSL 方式:**
```bash
openssl rand -base64 32
```

### 4. 获取 API 密钥

#### Tushare Token
1. 访问 https://tushare.pro/
2. 注册账号
3. 在个人中心获取 Token
4. 免费版即可满足基本需求

#### 智谱 AI (GLM-4V) - 推荐
1. 访问 https://open.bigmodel.cn/
2. 注册并创建 API Key
3. 免费额度足够个人使用

#### OpenAI (GPT-4V)
1. 访问 https://platform.openai.com/
2. 创建 API Key
3. 需要付费使用

#### Anthropic (Claude)
1. 访问 https://console.anthropic.com/
2. 创建 API Key
3. 需要付费使用

---

## 初始化数据库

### 运行初始化脚本

```bash
python core/scripts/init_db.py
```

**预期输出:**
```
✓ Database initialized at: core/data/db/quant_os.duckdb
✓ Created table: user_portfolio
✓ Created table: sectors
✓ Created table: stock_sector_mapping
✓ Ran migration: 0001_initial_schema.sql
✓ Ran migration: 0002_add_sectors.sql
...
Database initialization complete!
```

### 验证数据库

```bash
python -c "
from pathlib import Path
db_path = Path('core/data/db/quant_os.duckdb')
print(f'Database exists: {db_path.exists()}')
print(f'Database size: {db_path.stat().st_size / 1024:.2f} KB')
"
```

---

## 启动 API 服务

### 方法 1: 使用 uv (推荐)

```bash
uv run quant-os-api
```

### 方法 2: 直接运行

```bash
python core/app/api/main.py
```

### 方法 3: 使用 uvicorn

```bash
uvicorn core.app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**预期输出:**
```
2026-02-01 14:30:00.000 | INFO     | Starting Quant_OS API v2.0.0...
2026-02-01 14:30:00.100 | INFO     | ✓ Database initialized
2026-02-01 14:30:00.200 | INFO     | ✓ Quant_OS API started successfully
2026-02-01 14:30:00.300 | INFO     |   - API Documentation: http://localhost:8000/docs
2026-02-01 14:30:00.400 | INFO     |   - Health Check: http://localhost:8000/api/health
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 后台运行

**Linux/macOS:**
```bash
nohup python core/app/api/main.py > api.log 2>&1 &
```

**Windows:**
```powershell
Start-Process python -ArgumentList "core/app/api/main.py" -WindowStyle Hidden
```

---

## 测试 API

### 1. 健康检查

```bash
curl http://localhost:8000/api/health
```

**预期响应:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "timestamp": "2026-02-01T14:30:00.000000"
}
```

### 2. 查看 API 文档

在浏览器中打开:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. 测试认证

```bash
# 无认证 - 应该返回 401
curl http://localhost:8000/api/portfolio

# 有认证 - 应该返回 200
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/api/portfolio
```

### 4. 测试投资组合端点

**添加持仓:**
```bash
curl -X POST http://localhost:8000/api/portfolio \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001",
    "stock_name": "平安银行",
    "quantity": 100,
    "cost_price": 15.50
  }'
```

**查询持仓:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/api/portfolio
```

### 5. 测试市场数据端点

**获取股票行情:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/api/market/quote?code=000001"
```

**获取技术分析:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/api/market/technical?code=000001"
```

### 6. 测试新闻搜索

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/api/news?code=000001&days=7&max_results=5"
```

### 7. 运行自动化测试

```bash
python test_basic_functionality.py
```

---

## OpenClaw 集成

详细的 OpenClaw 集成指南请参考: [docs/OPENCLAW_SETUP.md](OPENCLAW_SETUP.md)

### 快速开始

1. **安装 OpenClaw:**
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

2. **复制技能文件:**
```bash
cp -r docs/openclaw_skills/* ~/.openclaw/workspace/skills/
```

3. **配置环境变量:**
```bash
export QUANT_OS_API_URL="http://localhost:8000"
export QUANT_OS_API_KEY="your_api_key_here"
```

4. **启动 OpenClaw:**
```bash
openclaw start
```

---

## 生产环境部署

### 使用 Docker (推荐)

创建 `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY core/ core/
COPY docs/ docs/

RUN pip install -e .

EXPOSE 8000

CMD ["python", "core/app/api/main.py"]
```

构建和运行:
```bash
docker build -t quant-os:2.0.0 .
docker run -d -p 8000:8000 --env-file .env quant-os:2.0.0
```

### 使用 systemd (Linux)

创建 `/etc/systemd/system/quant-os.service`:
```ini
[Unit]
Description=Quant_OS API Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Quant_OS
Environment="PATH=/path/to/Quant_OS/.venv/bin"
ExecStart=/path/to/Quant_OS/.venv/bin/python core/app/api/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable quant-os
sudo systemctl start quant-os
sudo systemctl status quant-os
```

### 使用 Nginx 反向代理

创建 `/etc/nginx/sites-available/quant-os`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

启用配置:
```bash
sudo ln -s /etc/nginx/sites-available/quant-os /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 故障排除

### 问题 1: 依赖安装失败

**症状:** `uv sync` 或 `pip install` 失败

**解决方案:**
```bash
# 清理缓存
rm -rf .venv
rm -rf ~/.cache/uv

# 重新安装
uv sync

# 或使用 pip
python -m pip install --upgrade pip
pip install -e .
```

### 问题 2: 数据库初始化失败

**症状:** `Database locked` 或 `Permission denied`

**解决方案:**
```bash
# 检查数据库文件权限
ls -la core/data/db/

# 删除锁文件
rm -f core/data/db/quant_os.duckdb.wal

# 重新初始化
python core/scripts/init_db.py
```

### 问题 3: API 启动失败

**症状:** `Address already in use` 或 `Port 8000 is already allocated`

**解决方案:**
```bash
# 查找占用端口的进程
# Linux/macOS:
lsof -i :8000
# Windows:
netstat -ano | findstr :8000

# 杀死进程
# Linux/macOS:
kill -9 <PID>
# Windows:
taskkill /PID <PID> /F

# 或使用不同端口
export QUANT_OS_API_PORT=8001
python core/app/api/main.py
```

### 问题 4: 认证失败

**症状:** `401 Unauthorized` 或 `Invalid API key`

**解决方案:**
```bash
# 检查 .env 文件
cat .env | grep QUANT_OS_API_KEY

# 确保 API key 没有多余空格或引号
# 正确: QUANT_OS_API_KEY=abc123
# 错误: QUANT_OS_API_KEY="abc123"
# 错误: QUANT_OS_API_KEY= abc123

# 重新生成 API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 问题 5: Tushare 数据获取失败

**症状:** `Invalid token` 或 `Rate limit exceeded`

**解决方案:**
```bash
# 验证 token
python -c "
import tushare as ts
ts.set_token('YOUR_TOKEN')
pro = ts.pro_api()
print(pro.daily(ts_code='000001.SZ', start_date='20260101', end_date='20260131'))
"

# 检查积分和权限
# 访问 https://tushare.pro/user/token

# 等待 1 分钟后重试（避免频率限制）
```

### 问题 6: 类型提示错误

**症状:** `TypeError: unsupported operand type(s) for |`

**解决方案:**
```bash
# 检查 Python 版本
python --version

# 如果 < 3.10，使用 typing.Optional
# 已在 core/app/common/logging.py 中修复

# 或升级 Python
python3.12 -m venv .venv
```

---

## 性能优化

### 1. 数据库优化

```python
# 在 core/app/data/db.py 中添加
db.execute("PRAGMA threads=4")
db.execute("PRAGMA memory_limit='2GB'")
```

### 2. API 缓存

```python
# 使用 Redis 缓存市场数据
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_stock_quote(code: str):
    # 缓存 5 分钟
    pass
```

### 3. 并发处理

```bash
# 使用多个 worker
uvicorn core.app.api.main:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## 监控和日志

### 查看日志

```bash
# 实时查看日志
tail -f api.log

# 搜索错误
grep ERROR api.log

# 查看最近 100 行
tail -n 100 api.log
```

### 日志级别

在 `.env` 中设置:
```bash
LOG_LEVEL=DEBUG  # 开发环境
LOG_LEVEL=INFO   # 生产环境
LOG_LEVEL=ERROR  # 仅错误
```

---

## 安全建议

1. **使用强 API 密钥**: 至少 32 字符的随机字符串
2. **启用 HTTPS**: 生产环境必须使用 SSL/TLS
3. **限制访问**: 使用防火墙限制 API 访问
4. **定期更新**: 及时更新依赖包
5. **备份数据**: 定期备份 DuckDB 数据库文件

---

## 下一步

- 阅读 [API 文档](API.md) 了解所有端点
- 查看 [OpenClaw 设置指南](OPENCLAW_SETUP.md) 进行多平台集成
- 参考 [快速开始指南](QUICKSTART.md) 了解基本用法

---

**部署成功！🎉**

如有问题，请查看:
- [GitHub Issues](https://github.com/yourusername/Quant_OS/issues)
- [文档目录](README.md)
