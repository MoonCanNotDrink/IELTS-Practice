# IELTS Speaking AI

一个面向 IELTS 口语训练的练习平台，覆盖完整模考、自由练习、动态追问、语音播报、转写、评分反馈与历史复盘。

它的目标不是只展示单点技术能力，而是把“练习前、练习中、练习后”的关键链路连成一个可持续使用的学习系统。

> 状态：Beta
> 最后更新：2026-03-20

## 导航

- [English README](README.en.md)
- [文档目录](docs/README.md)
- [Documentation Index (English)](docs/README.en.md)
- [项目简介（中文）](docs/项目简介.md)
- [Project Overview (English)](docs/项目简介.en.md)
- [对外文档](documentation/README.md)
- [External Documentation (English)](documentation/README.en.md)

## 从这里开始

| 我想做什么 | 入口 |
|---|---|
| 快速了解这个项目 | [项目简介](docs/项目简介.md) |
| 作为普通读者阅读公开文档 | [对外文档](documentation/README.md) |
| 开始查看用户指南 | [快速开始](documentation/user-guide/getting-started.md) |
| 查看实现计划和报告 | [文档目录](docs/README.md) |

## 核心能力

- 完整 IELTS Speaking 流程：Part 1 / Part 2 / Part 3
- 自由练习模式：支持题库选题、自定义题目、自定义作答时长
- 动态追问：基于大模型生成更接近真实考试的连续提问
- 语音考官：支持 TTS 播报，增强沉浸感
- 多维评分：结合转写、音频分析与模型能力输出反馈
- 历史记录与趋势复盘：便于长期练习与回看
- 多用户隔离：基于 JWT 的登录与数据隔离

## 快速开始

### 安装依赖

```bash
pnpm install
```

### 运行测试

```bash
pnpm test
```

### 本地运行说明

- 当前根目录 `package.json` 提供的脚本是 `pnpm test`。
- 其他本地开发步骤请参考 [AGENTS.md](AGENTS.md) 与 [docs/README.md](docs/README.md) 中的计划 / 报告文档。

## 项目结构

- `frontend/`：前端页面、交互逻辑与样式
- `backend/`：FastAPI 后端、业务路由、服务与数据模型
- `tests/`：Playwright 与相关自动化测试
- [`docs/plans/`](docs/plans/)：功能实现计划与方案文档
- [`docs/reports/`](docs/reports/)：优化报告、产品摘要与阶段总结
- [`AGENTS.md`](AGENTS.md)：项目开发规则与协作约束

## 文档入口

- [docs/README.md](docs/README.md)：文档目录
- [docs/style-guide.md](docs/style-guide.md)：文档风格指南
- [documentation/README.md](documentation/README.md)：更正式的对外发布文档入口
- [docs/plans/自由练习实现计划.md](docs/plans/自由练习实现计划.md)：自由练习功能的实现计划
- [docs/reports/自由练习界面优化报告.md](docs/reports/自由练习界面优化报告.md)：Free Practice 界面优化与可访问性报告
- [docs/reports/自由练习-产品设计摘要.md](docs/reports/自由练习-产品设计摘要.md)：Free Practice 的产品 / 设计视角摘要
- [docs/reports/全阶段开发总结.md](docs/reports/全阶段开发总结.md)：项目整体阶段性总结

## 技术栈

- 前端：原生 HTML / JavaScript / CSS
- 后端：FastAPI / Python
- 数据库：SQLite / PostgreSQL
- 语音转写：Azure Speech + faster-whisper
- 音频分析：librosa
- 大模型：Gemini
- 鉴权：JWT
- 部署：Docker

## 说明

根目录 `README.md` 用于项目入口说明。

`docs/` 目录中的文档面向协作与交付；`.sisyphus/` 中的计划、问题与决策记录保留为内部执行痕迹，不作为对外交付文档。 
