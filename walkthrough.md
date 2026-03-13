# IELTS Speaking AI — 全阶段开发总结报告 (Phase 1-4)

历经 4 个硬核的开发阶段，我们成功构建了一个**达到商用级水准的全真 IELTS 口语模考平台**。它不仅支持原本策划的 Part 2 录音打分，更是进化成了能够和你**动态对话**的“真人考官”。

---

## 🚀 最终实现了什么？

### 1. 完整的模考状态机 (Part 1 + 2 + 3) 
你现在可以体验一场原汁原味的 10 分钟口语考试：
- **Part 1 (每日闲聊)**：固定数量的连贯追问。
- **Part 2 (个人陈述)**：1 分钟思考（支持打字记笔记），2 分钟录音独白。
- **Part 3 (深度探讨)**：基于大模型的连贯追问。

### 2. 动态追问的大模型考官 (Decoupled UX)
真正突破性的体验：你回答完一句话，系统**不让你死等转圈圈**，而是**立刻**向你展示转写文本供你复盘。在你阅读文本的两秒钟里，后端大模型 (Gemini) 正在根据你上一句话的逻辑，**当场生成**下一句追问。这种体验极其逼真、连贯。

### 3. 三层混合流利度评估 (Phase 3 巅峰功能)
不再让大模型死板地“看字给分”。我们为你接入了音频物理学层面的特征分析：
- **Whisper 词级时间戳**：精准感知每一个单词落下的时间。
- **Librosa 物理波形分析**：硬核检测“有效说话时长 (Speaking Duration)”、“总静音空白占比” 以及 **“超过1秒的尴尬长停顿次数”**。
- **综合打分**：这套物理指标被注入了 Gemini 的提示词上下文里，极大地提升了流利度评分的客观性。

### 4. Audio Examiner 沉浸式听力播报 (最新特性)
我们接入了谷歌 Gemini 迄今最前沿的 `gemini-2.5-flash-preview-tts` 模型：
- 新增 "Audio Examiner Mode" 原生语音独立开关。
- 支持地道英伦口音 (Aoede) 提供高度逼真的考官语音播报。
- 构建了 `/api/tts` 专属流式音频分发路由，绕过客户端 CORS/Token 限制，即拿即读。

### 5. 高维评分反馈与 Band 7+ 黄金范文
考试结束后，系统不仅给出多维度的精准打分（词汇、语法、流利度、发音），还会根据你的临场作答录音，自动为你生成一份运用了高级词汇与从句的 **Band 7+ 改进版范文 (Sample Answer)**，以供对照复盘。

### 6. 极致的前端面板与全景历史看板
- 暗色风格的高端磨砂玻璃 UI (Glassmorphism)。
- 考试结束后的**四维度胶囊条**展示结构。
- 加入了**全局统计大盘**：直观展示你的“总模考次数”、“最高分”以及“平均分”。
- 用 **Chart.js** 绘制的个人成长中心：折线图展示你最近 20 次模考分数的起伏，雷达图展示你各项能力的均衡程度。

### 7. 预置真实考卷题库
- 底部数据库内置了跨越 7 大高频维度（人物、事件、地点、物品等）的 **29 道全真雅思 Part 2 话题卡**，保证开箱即获得原汁原味的备考体验。

---

## 🛠 技术架构回顾

| 领域 | 选型 | 作用 |
|------|------|------|
| **前端** | 原生 HTML+JS, CSS Variables | 轻量级、无包体积压力，极强的暗黑模式 UI 表现力 |
| **后端** | FastAPI (Python) | 异步并发极高，完美适配处理长录音和实时 API 代理 |
| **数据库** | SQLite / PostgreSQL (自适应) | 本地零配置默认驱动 SQLite 便捷开发，上云时配置环境变量即可瞬间无缝拨换云端 PostgreSQL |
| **音频处理**| WebAudioContext + WebM 转 WAV | 前端解决音频重采样难题，省去后端巨额算力 |
| **ASR** | Azure Speech + 本地 faster-whisper | Azure 优先转写，失败时回退本地模型并保留词级时间戳 |
| **物理声学** | `librosa` | 抽取停顿、流利度、词/秒速率 |
| **发音底层** | Azure Speech Services | 提供最专业的音素级发音错误检测 (GOP) |
| **大模型** | Google Gemini 2.5 Flash | 主导考官追问、四维度最终评分整合、范文生成 |
| **鉴权隔离**| JSON Web Token (JWT) | 构建独家护城河与多用户记录隔离体系 |
| **部署方案** | Docker + 代码部署 | 一键发布平台，解决连接外部 API 的网络问题 |

---

## 🔐 Phase 5：多用户与鉴权隔离 (最新更新)
基于实际需求，系统引入了强制登录验证：
- 采用 **JWT Token** 构建会话维持体系，每次 API 请求前置拦截。
- 新注册用户强制校验位于服务器 `.env` 文件中的 `INVITE_CODE`，杜绝未授权访问和滥用。
- 所有生成记录（Session/录音/打分面板）均与系统分配的 `user_id` 强关联，确保 /history 单人看板的绝对隐私与隔离。

## 🐳 部署指南
此方案的推荐用法是依靠我写好的 `Dockerfile` 与配置好的 Nginx 文件，依据之前生成的 `deploy_guide.md` 推上 Google Cloud Run 或个人服务器。它会自动分配好带有 HTTPS 支持的线上链接。

✨ 所有的核心开发与衍生任务清单 (Phase 1-5) 均已悉数完美收官！

---

## 🧾 Staged 变更补充记录（未 commit）

以下为当前 Git 暂存区（staged）改动的汇总，已同步到 walkthrough 文档：

### 1) 后端配置与稳定性增强
- `backend/app/config.py`
  - 新增 Whisper 本地模型配置：`WHISPER_MODEL_PATH / WHISPER_MODEL_SIZE / WHISPER_DEVICE / WHISPER_COMPUTE_TYPE`。
  - 新增超时配置：`GEMINI_TIMEOUT_SECONDS`、`PRONUNCIATION_TIMEOUT_SECONDS`。
  - 增加 `DEBUG` 兼容解析（支持 `release/prod/dev/debug` 等字符串）。
  - SQLite 默认路径自动创建父目录，避免冷启动 `unable to open database file`。

### 2) 应用入口与健康检查一致性
- `backend/app/main.py`
  - 统一版本常量 `APP_VERSION`。
  - `/api/health` 返回 `app.version`，避免硬编码版本漂移。

### 3) 安全与输入校验
- `backend/app/routes/dev.py`
  - Dev 路由增加鉴权依赖（需登录）。
  - 增加 `DEBUG=true` 才可访问的保护，避免生产环境误用重置接口。
- `backend/app/routes/part2.py`、`backend/app/routes/exam.py`
  - 上传音频扩展名校验（仅允许 `ALLOWED_AUDIO_FORMATS`）。
  - `NextQuestionRequest.part` 收紧为 `Literal["part1","part3"]`。

### 4) 评分与外部依赖降级能力
- `backend/app/routes/part2.py`、`backend/app/routes/scoring.py`
  - Azure 发音评估增加超时控制，超时自动降级，避免接口长时间阻塞。
- `backend/app/services/scoring_service.py`
  - Gemini 调用加入 `asyncio.wait_for` 超时控制。
  - 超时时返回可解释的 fallback 评分信息，提升可用性。

### 5) ASR 架构升级（Azure + 本地 Whisper 双层回退）
- `backend/app/services/asr_service.py`
  - 从单一路径升级为分层策略：优先 Azure，失败后回退 `faster-whisper`。
  - 增加模型惰性加载与本地模型路径探测，统一输出 `{"text","words"}`。

### 6) TTS 与 E2E 冒烟脚本增强
- `backend/app/routes/scoring.py`
  - 抽离 `_generate_tts_response`，返回动态 `audio/*` MIME 类型。
- `backend/e2e_smoke.py`（新增）
  - 覆盖注册/登录、抽题、Part2 上传与评分、Full Exam 评分、历史详情校验等端到端链路。
  - `.env` 加载顺序修复，支持 `--skip-tts` 与 `E2E_SKIP_TTS`。
  - demo 音频生成与登录校验逻辑优化。

### 7) 前端体验与数据展示修正
- `frontend/app.js`
  - 增加浏览器 Web Speech 客户端转写链路，录音上传时携带 `client_transcript`。
  - 录音开始/结束与重置流程中补全识别器生命周期管理。
- `frontend/history.html`
  - 分数显示由“truthy 判断”改为显式空值判断，`0.0` 不再被误判为缺失。
  - 抽离 `formatScore/getScoreColor`，图表与列表展示一致性提升。
