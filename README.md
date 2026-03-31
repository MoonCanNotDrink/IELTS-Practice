# IELTS Practice

中文 • [English](README.en.md)

状态：Beta

一个面向 IELTS 口语与写作练习的全栈项目，结合 FastAPI 后端与原生前端，使用大模型与语音服务为考生提供模考流程、即时反馈与历史复盘。

什么值得看（20 行内）：快速演示完整考试流、AI 评分与语音考官体验，适合作为个人作品集的技术与产品示例。

## 它能做什么

- 提供完整的 IELTS Speaking 模考流程（Part 1 / Part 2 / Part 3）与写作练习（Task 1 / Task 2）
- 基于大模型的多维评分与反馈，结合转写和音频分析给出具体改进点
- 语音考官与 TTS / 转写集成，支持动态追问与更真实的口语练习体验
- 历史记录与进度回顾，支持多用户隔离（JWT）以便长期练习追踪

## 技术栈（精简）

- 前端：vanilla HTML, JavaScript, CSS
- 后端：FastAPI, Python
- AI / 语音：Gemini（评分与反馈）, Azure Speech（TTS/转写）, faster-whisper（本地转写）, librosa（音频分析）
- 基础设施：SQLite / PostgreSQL（可选）, Docker（容器化）, Cloud Run（部署示例）

## 快速开始

完整开发与部署说明请参见 docs/dev-guide.md。

最小三步（用于开发环境）：

```bash
corepack pnpm install        # 安装前端与测试依赖
# 配置环境变量，参见 docs/dev-guide.md
corepack pnpm test           # 运行测试
# 按 docs/dev-guide.md 中的步骤启动后端与前端
```

## 项目结构（顶层）

- frontend/ — 静态页面与浏览器端交互
- backend/ — FastAPI 应用与业务逻辑
- tests/ — 自动化测试（Playwright / 单元测试）
- docs/ — 开发指南与对外文档（详见 docs/dev-guide.md）

## 重要链接

- 开发指南（包含运行、配置与部署）: docs/dev-guide.md
- 文档索引: docs/README.md
- 项目协作规范: AGENTS.md

---

更新说明: 本 README 精简为面向访问者与作品集展示的首页，详细开发与部署步骤已移至 docs/dev-guide.md。
