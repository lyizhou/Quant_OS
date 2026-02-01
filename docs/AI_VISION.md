# 配置AI视觉服务 - 持仓图片识别

## 问题说明

DeepSeek API **不支持图片识别功能**。因此，我们已经更新代码支持以下AI视觉服务：

1. **OpenAI GPT-4 Vision** (推荐)
2. **Anthropic Claude 3 Vision**

## 快速配置

### 方案1：使用OpenAI GPT-4 Vision（推荐）

#### 1. 获取API Key

访问：https://platform.openai.com/api-keys

1. 注册/登录OpenAI账号
2. 点击 "Create new secret key"
3. 复制生成的API Key（格式：`sk-proj-...`）

#### 2. 配置.env文件

编辑 `.env` 文件，添加：

```bash
# AI Vision Service
AI_VISION_PROVIDER=openai

# OpenAI API Key
OPENAI_API_KEY=sk-proj-your_actual_key_here
```

#### 3. 重启Bot

```bash
# 停止当前bot（如果在运行）
# 按 Ctrl+C 或运行：
pkill -f "run_telegram_bot.py"

# 重新启动
uv run python run_telegram_bot.py
```

#### 4. 测试

在Telegram中上传持仓截图，应该可以正常识别了！

### 方案2：使用Claude 3 Vision

#### 1. 获取API Key

访问：https://console.anthropic.com/

1. 注册/登录Anthropic账号
2. 创建API Key
3. 复制生成的Key

#### 2. 配置.env文件

```bash
# AI Vision Service
AI_VISION_PROVIDER=claude

# Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_key_here
```

#### 3. 重启Bot

同上

## 成本对比

### OpenAI GPT-4 Vision
- **模型**: gpt-4o
- **成本**: 约 $0.01-0.03/次识别
- **优点**: 识别准确、速度快、文档完善
- **缺点**: 需要付费账号

### Claude 3 Vision
- **模型**: claude-3-sonnet-20240229
- **成本**: 约 $0.01-0.02/次识别
- **优点**: 识别准确、理解能力强
- **缺点**: 需要付费账号

## 常见问题

### Q1: 我没有OpenAI或Claude账号怎么办？

**选项A：注册OpenAI账号**
- 访问 https://platform.openai.com/
- 注册并充值（最低$5）
- 创建API Key

**选项B：使用本地OCR（免费但准确度较低）**
- 我可以帮你实现基于PaddleOCR的本地识别
- 完全免费，但需要额外配置

**选项C：手动输入持仓**
- 我可以添加手动输入命令
- 格式：`/add 000001 1000 12.50`

### Q2: API Key配置后还是报错？

检查：
1. API Key是否正确复制（没有多余空格）
2. `.env`文件是否保存
3. Bot是否重启
4. API Key是否有余额

### Q3: 识别不准确怎么办？

建议：
1. 使用高清截图
2. 确保文字清晰可见
3. 避免截图中有遮挡
4. 使用标准券商界面

### Q4: 可以切换回DeepSeek吗？

DeepSeek不支持图片识别，无法用于此功能。但DeepSeek仍然用于其他文本分析功能。

## 测试配置

运行以下命令测试API配置：

```bash
# 测试OpenAI
uv run python -c "
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
response = httpx.post(
    'https://api.openai.com/v1/chat/completions',
    headers={'Authorization': f'Bearer {api_key}'},
    json={
        'model': 'gpt-4o',
        'messages': [{'role': 'user', 'content': 'test'}],
        'max_tokens': 10
    },
    timeout=10
)
print(f'Status: {response.status_code}')
if response.status_code == 200:
    print('✅ OpenAI API配置成功！')
else:
    print(f'❌ 错误: {response.text}')
"
```

## 下一步

配置完成后：

1. 重启Bot
2. 在Telegram中发送 `/start`
3. 上传持仓截图
4. 等待识别结果（5-10秒）
5. 使用 `/portfolio` 查看持仓

## 需要帮助？

如果你：
- 没有OpenAI/Claude账号
- 想使用免费的本地OCR
- 想添加手动输入功能
- 遇到其他问题

请告诉我，我会帮你实现相应的解决方案！
