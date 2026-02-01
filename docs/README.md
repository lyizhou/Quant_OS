# Quant_OS 文档索引

**版本**: 1.0.0
**更新**: 2026-01-19

---

## 📚 文档分类

### 🚀 快速开始

- **[QUICKSTART.md](QUICKSTART.md)** - 5分钟快速上手指南
  - 环境配置
  - Bot 启动
  - 基础命令使用

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - 生产部署指南
  - 服务器配置
  - 进程管理（systemd/supervisor）
  - 监控和日志
  - 安全最佳实践

### 🤖 AI 功能

- **[AI_VISION.md](AI_VISION.md)** - AI 视觉识别配置
  - GLM-4V（智谱 AI）配置（推荐）
  - GPT-4V（OpenAI）配置
  - Claude 3.5（Anthropic）配置
  - 截图识别最佳实践

### 🛠️ 开发工具

- **[SUPERPOWERS_GUIDE.md](SUPERPOWERS_GUIDE.md)** - Superpowers 插件完整指南
  - 安装方法
  - 核心概念和工作流程
  - 可用技能详解
  - 最佳实践

- **[SUPERPOWERS_QUICKREF.md](SUPERPOWERS_QUICKREF.md)** - Superpowers 快速参考卡
  - 快速安装
  - 常用命令
  - 对话示例
  - 常见问题

### 📊 功能文档

- **[PORTFOLIO_DIAGNOSIS_IMPLEMENTATION.md](PORTFOLIO_DIAGNOSIS_IMPLEMENTATION.md)** - 投资组合诊断功能实现
  - 功能设计
  - 技术实现
  - 数据库 schema

- **[PORTFOLIO_DIAGNOSIS_COMPLETED.md](PORTFOLIO_DIAGNOSIS_COMPLETED.md)** - 投资组合诊断功能完成报告
  - 实现总结
  - 测试结果
  - 使用示例

### 🐛 Bug 修复记录

- **[BUGFIX_SECTOR_STRENGTH_SQL.md](BUGFIX_SECTOR_STRENGTH_SQL.md)** - 板块强度 SQL 错误修复
  - 错误分析
  - 修复方案
  - 验证步骤

### 📁 重构文档

**目录**: [refactoring/](refactoring/)

包含项目重构过程中的详细文档：
- 清理报告
- 重构总结
- 项目状态

---

## 📖 推荐阅读顺序

### 新用户

1. [QUICKSTART.md](QUICKSTART.md) - 快速开始使用 Quant_OS
2. [AI_VISION.md](AI_VISION.md) - 配置 AI 视觉识别（如果需要使用截图识别）
3. [DEPLOYMENT.md](DEPLOYMENT.md) - 部署到生产环境（如果需要）

### 开发者

1. [QUICKSTART.md](QUICKSTART.md) - 了解项目基础
2. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目架构和目录结构
3. [SUPERPOWERS_GUIDE.md](SUPERPOWERS_GUIDE.md) - 安装 Superpowers 插件
4. [SUPERPOWERS_QUICKREF.md](SUPERPOWERS_QUICKREF.md) - 快速参考卡

### 贡献者

1. 完成开发者阅读路径
2. [PORTFOLIO_DIAGNOSIS_IMPLEMENTATION.md](PORTFOLIO_DIAGNOSIS_IMPLEMENTATION.md) - 功能实现示例
3. [refactoring/](refactoring/) - 了解项目重构历史
4. 主仓库 [CLAUDE.md](../CLAUDE.md) - 开发指南

---

## 🔍 按主题查找

### Telegram Bot

- 命令使用 → [QUICKSTART.md](QUICKSTART.md)
- 部署配置 → [DEPLOYMENT.md](DEPLOYMENT.md)

### AI 视觉识别

- GLM-4V 配置 → [AI_VISION.md](AI_VISION.md)
- GPT-4V 配置 → [AI_VISION.md](AI_VISION.md)
- Claude 配置 → [AI_VISION.md](AI_VISION.md)

### 投资组合诊断

- 功能说明 → [PORTFOLIO_DIAGNOSIS_COMPLETED.md](PORTFOLIO_DIAGNOSIS_COMPLETED.md)
- 技术实现 → [PORTFOLIO_DIAGNOSIS_IMPLEMENTATION.md](PORTFOLIO_DIAGNOSIS_IMPLEMENTATION.md)

### AI 辅助开发

- Superpowers 完整指南 → [SUPERPOWERS_GUIDE.md](SUPERPOWERS_GUIDE.md)
- Superpowers 快速参考 → [SUPERPOWERS_QUICKREF.md](SUPERPOWERS_QUICKREF.md)

### 数据库

- Schema 设计 → 见主项目 `core/app/data/migrations/`
- Bug 修复 → [BUGFIX_SECTOR_STRENGTH_SQL.md](BUGFIX_SECTOR_STRENGTH_SQL.md)

---

## 📝 文档维护

### 文档规范

- 使用 Markdown 格式
- 包含清晰的标题层级
- 提供代码示例
- 标注最后更新时间

### 更新频率

- **功能文档**: 随功能更新同步更新
- **Bug 修复**: 发现问题时立即记录
- **重构文档**: 重构过程中持续更新
- **快速参考**: 按需更新

---

## 🔗 外部资源

- **主仓库 README**: [../README.md](../README.md)
- **开发指南**: [../CLAUDE.md](../CLAUDE.md)
- **Superpowers 插件**: https://github.com/obra/superpowers
- **Tushare 文档**: https://tushare.pro/document/2
- **Python Telegram Bot**: https://python-telegram-bot.readthedocs.io/

---

## 📮 反馈和贡献

如果你发现文档有误或需要补充：

1. **修复错误**: 直接提交 PR
2. **补充文档**: 遵循现有格式和风格
3. **提出建议**: 在 Issues 中讨论

---

**最后更新**: 2026-01-19
**维护者**: Quant_OS Team
