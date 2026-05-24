# MADF — Multi-Agent Discussion Framework

> 一个基于 Deep Agent 的企业级圆桌讨论平台——AI 角色由 Skill 驱动，围绕用户提出的问题进行去中心化讨论，流式呈现，用户可随时参与，打破信息差。

---

## 一、项目约束

| 维度 | 决策 |
|------|------|
| 团队 | 单人开发 |
| 产品定位 | 企业级多智能体圆桌讨论平台 |
| 目标用户 | 学生群体，50+ 并发 |
| 前端 | React + Monaco Editor，界面必须精致,使用（ui-ux-pro-max技能来做） |
| 后端 | FastAPI（Python 3.12+） |
| 数据库 | PostgreSQL |
| 消息队列 | Redis Pub/Sub（后续可切 RabbitMQ，接口预抽象） |
| Agent 框架 | deepagents(源码驱动开发) |
| 模型 | 云端大模型 API（参数钩子在 `.env` 中配置，支持多 provider） |
| 部署 | Docker Compose → 后续上服务器 |
| 联网搜索 | Tavily API（key 在 `.env` 中配置） |

---

## 二、功能边界

### 一期必须做

| 功能 | 做到什么程度 |
|------|------------|
| A. 讨论创建 | 用户选主题 + 选参与 Agent + 设定讨论时长，系统追踪时间，到时自动结束 |
| B. 去中心化发言 | Agent 收到上下文 → 非流式输出决策 JSON `{decision, confidence}` → orchestrator 收集本轮全部决策 → 比较确信度 → 最高者获得发言权 → 流式输出发言内容 → 全员沉默时随机选一个强制发言 |
| C. 流式输出 SSE | 按事件类型推送（agent_think / agent_speak_start / agent_speak_chunk / agent_speak_end / host_intro / host_summary / round_start / discussion_end / user_intervened / heartbeat），前端独立气泡 typewriter 效果 |
| D. 用户介入发言 | 文字输入框 + 发送按钮 → HTTP POST 提交 → orchestrator 注入下一轮上下文，Enter 快捷键，丝滑交互 |
| E. 主持人开场/摘要 | 各一次独立 LLM 调用，开场在讨论开始时，摘要在讨论时长到时 |
| F. 讨论历史回放 | SSE 重连追赶（分级策略：<20条逐条推/20-200批量/200+只推摘要+最近20条），讨论结束后全量 SQL 加载，多 Tab 按 client_id 去重，orchestrator 崩溃写 error 事件 |
| G. 角色 Skill 生成 | 复用 nuwa-source 女娲管线（Phase 0-5），用户输入人名/主题 → 联网调研（Tavily 5s 超时）→ 生成完整 SKILL.md + references/ 目录，并发生成支持（每个生成任务独立 Agent 实例），生成过程展示进度 |
| H. 角色 Skill 管理 | 文件树 + Monaco Editor 展示完整 skill 目录（SKILL.md + references/*.md），支持创建/查看/编辑/删除，公开画廊共享（浏览、只读、复制到我的），文件系统 + PostgreSQL 元数据双重管理 |
| I. 角色选择 | 列出用户自己的角色 + 画廊公开角色，支持搜索/筛选（按名称、标签），多选参与讨论 |
| J. 注册/登录 | 用户名 + 密码 + 手机号，JWT token，OAuth 第三方登录留钩子 |
| K. 用户数据绑定 | 所有核心表 owner_id（架构约束，非独立功能） |
| L. 业务审计 | orchestrator/业务服务统一埋点 → PostgreSQL `audit_events` 表；主后端通过 `/api/v1/admin/audit/*` 查询，审计后台通过 `audit_backend` 的 `/api/v1/audit/*` 读取 |
| M. Docker Compose 一键部署 | `docker-compose up` 启动全部服务（Nginx + 主/审计 FastAPI + PostgreSQL + Redis + 主/审计 React） |

### 明确不做什么

- 系统级分布式链路追踪（OpenTelemetry/Jaeger）——一期不做
- OAuth 第三方登录——留钩子，一期不做
- 语音/图片/文件输入——一期不做
- @指定 Agent 回复——一期不做
- 角色团队协作编辑——一期不做
- 事实核查/讨论纠偏——不做
- System Prompt 约束 Agent 行为——不做（靠 Skill 驱动角色模仿）
- 线程池隔离——LLM 调用是 async HTTP，不阻塞事件循环，一期不做
- RabbitMQ——Redis Pub/Sub 当前够用，接口预抽象后续切换
- 高级熔断（半开探测、多 provider failover）——简单熔断够用
- 数据库分区/分库分表/读写分离——数据量没到，一期不做
- 消息队列削峰——一期不需要
- CDN——内部系统，Nginx 直接返回静态资源够用

---

## 三、技术栈总览

| 层 | 选型 | 理由 |
|---|-----|------|
| 后端 | FastAPI + Python 3.12 | 单人最熟，async 生态完整 |
| 前端 | React + Monaco Editor | 单人最熟，Monaco 即 VS Code 内核 |
| 关系型数据库 | PostgreSQL | 企业级标准，全文搜索/JSONB/部分索引 |
| 缓存/消息 | Redis Pub/Sub | 轻量，当前够用 |
| Agent 框架 | deepagents（LangGraph） | Skill/Harness 机制，多 Agent 实例共存 |
| 大模型 | 云端 API（OpenAI 兼容协议） | `ChatOpenAI`，不本地跑模型 |
| 部署 | Docker Compose | 一键拉起，后续上服务器加 Nginx |

---

## 四、应用架构

### 架构模式

多模块单体：FastAPI 单应用 + `agent_engine` 作为独立 Python package 逻辑解耦。

```
madf-new/
├── agent_engine/                    # 独立 Python package（逻辑解耦）
│   ├── skill_gen/                   # 角色 Skill 生成（复用 nuwa-source）
│   │   ├── __init__.py
│   │   ├── agent.py                 # 移植自 nvwa_agent/agent.py
│   │   ├── run.py                   # 移植自 nvwa_agent/run.py
│   │   └── nuwa-skill/              # 移植自 nuwa-agent-skill/nuwa-skill/
│   │
│   ├── discussion/                  # 圆桌讨论引擎
│   │   ├── __init__.py
│   │   ├── factory.py               # create_roundtable_agent(skill_path) → CompiledStateGraph
│   │   ├── orchestrator.py          # 去中心化调度（收集决策 → 比较确信度 → 决定发言）
│   │   ├── stream_protocols.py      # Agent 对外的流式接口定义
│   │   └── circuit_breaker.py       # 简单熔断（同 provider 连续 3 次失败 → 本讨论禁用）
│   │
│   └── llm.py                       # 云端大模型调用（钩子可配置，从 .env 读）
│
├── backend/                         # FastAPI 应用
│   ├── main.py                      # 应用入口，注册路由、中间件、生命周期
│   ├── config.py                    # 配置（从 .env / Settings 读取）
│   ├── deps.py                      # 依赖注入（get_db, get_current_user）
│   │
│   ├── services/
│   │   ├── user/                    # 用户模块
│   │   │   ├── router.py            # 路由 + 参数校验（Pydantic schema）
│   │   │   ├── service.py           # 业务逻辑（注册/登录/JWT）
│   │   │   ├── repository.py        # 数据库操作（users 表）
│   │   │   └── schemas.py           # Request/Response Pydantic 模型
│   │   │
│   │   ├── character/               # 角色模块
│   │   │   ├── router.py
│   │   │   ├── service.py           # 业务逻辑（CRUD、画廊共享、权限）
│   │   │   ├── repository.py        # 数据库操作（skills 表）
│   │   │   ├── generation_service.py # deepagent 角色生成后台任务
│   │   │   ├── schemas.py
│   │   │   └── file_manager.py      # 文件系统操作（读写 skill 目录）
│   │   │
│   │   ├── discussion/              # 讨论模块
│   │   │   ├── router.py
│   │   │   ├── service.py           # 编排讨论生命周期
│   │   │   ├── repository.py        # 数据库操作（discussions + messages 表）
│   │   │   └── schemas.py
│   │   │
│   │   ├── realtime/                # 实时通信模块
│   │   │   ├── router.py            # SSE 端点（GET /discussions/{id}/stream）
│   │   │   ├── sse_manager.py       # 连接管理、去重、心跳、追赶策略
│   │   │   └── schemas.py           # SSE 事件类型定义
│   │   │
│   │   ├── admin/                   # 主系统管理接口（供审计后台代理调用）
│   │   │   ├── router.py            # /api/v1/admin/*
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   └── schemas.py
│   │   │
│   │   └── audit/                   # 审计模块
│   │       └── repository.py        # audit_events 写入/查询 + Redis Pub/Sub 旁路推送
│   │
│   ├── models/                      # SQLAlchemy ORM 模型（数据库实体）
│   │   ├── base.py                  # 通用 Mixin（id, created_at, updated_at, deleted_at）
│   │   ├── user.py
│   │   ├── skill.py
│   │   ├── discussion.py
│   │   ├── discussion_agent.py
│   │   ├── discussion_message.py
│   │   └── audit_event.py
│   │
│   ├── middleware/                   # FastAPI 中间件
│   │   ├── admin_auth.py            # 管理后台服务 JWT 验证；普通用户 JWT 在 deps.py
│   │   └── cors.py
│   │
│   ├── core/                        # 核心基础设施
│   │   ├── exceptions.py            # 统一异常类
│   │   ├── exception_handlers.py    # FastAPI exception_handlers
│   │   └── responses.py             # 统一响应 Result[T]、PageResult[T]
│   │
│   └── alembic/                     # 数据库迁移
│
├── skills/                          # 角色 Skill 文件存储（volume 挂载）
│   └── {owner_id}/
│       └── {skill-name-perspective}/
│           ├── SKILL.md
│           └── references/
│               └── research/
│                   ├── 01-writings.md
│                   ├── 02-conversations.md
│                   ├── 03-expression-dna.md
│                   ├── 04-external-views.md
│                   ├── 05-decisions.md
│                   └── 06-timeline.md
│
├── nuwa-source/                     # 女娲 Skill 原始代码（参考复用）
│   ├── nvwa_agent/                  # Skill 蒸馏 Agent
│   └── nuwa-agent-skill/            # 女娲 Skill 定义 + 示例角色
│
├── audit-frontend/                  # 审计/管理后台 React 应用（独立登录态）
├── audit_backend/                   # 审计/管理后台 FastAPI 应用（管理员认证 + 代理）
│   ├── services/auth/               # /api/v1/audit/auth/*
│   ├── services/events/             # /api/v1/audit/events*
│   ├── services/realtime/           # /api/v1/audit/sse/stream
│   ├── services/settings/           # /api/v1/audit/settings/*
│   ├── services/stats/              # /api/v1/audit/stats/*
│   ├── services/export/             # 审计导出预留模块
│   ├── services/integrity/          # 完整性规则预留模块
│   ├── services/retention/          # 保留策略预留模块
│   └── services/admin_proxy/        # /api/v1/admin/* → 主后端 /api/v1/admin/*
├── docker-compose.yml
├── .env                             # 环境变量（LLM API key、Tavily key 等）
└── AGENTS.md                        # 项目唯一说明源
```

### 模块依赖关系

```
discussion ──→ character  ──→ skill_gen (生成角色时)
discussion ──→ realtime   （发布 SSE 事件）
discussion ──→ audit      （记录事件）
character  ──→ audit      （记录操作）
user       ──→ audit      （记录操作）
所有人 ──→ user          （认证）
所有人 ──→ audit         （记录操作）
```

循环依赖检查：无循环。user 在最底层（被所有人依赖，不依赖任何人），audit/realtime 是横切基础设施。

### 跨模块调用铁律

- **方案一**：直接注入对方 Service（FastAPI 依赖注入，通过构造函数参数）
- **禁止**：直接 import 其他模块的 repository / models / file_manager / ORM 实体
- **禁止**：模块 A 直接访问模块 B 的数据库表——只能通过 B 的 Service 接口

### 角色 Skill 生成架构（deepagent 驱动）

生成流程由 `generation_service.py` 统一管理，**全部 5 个阶段由 deepagent 内部的 nuwa-skill 自主执行**，外部代码只负责：创建 Agent → 给 prompt → 调 `agent.astream()` → 复制输出文件。

```
POST /api/v1/characters/generate
  │
  ├─ CharacterService.generate_skill()
  │   ├─ 创建 Skill 目录 + PG 元数据 (status=generating)
  │   └─ asyncio.create_task(run_skill_generation())
  │
  └─ run_skill_generation() [background]
      ├─ 创建 work_root（拷贝 nuwa_source 到 .gen_work/）
      ├─ create_nvwa_agent(root_dir=work_root)
      │   └─ 内部调用 deepagents.create_deep_agent()
      │       加载 nuwa-skill，配置 12 个子 Agent、Tavily 搜索
      │
      ├─ agent.astream(prompt)  ← 逐事件推送进度
      │   │
      │   ├─ 主流程事件 (level="main")：阶段 0-5
      │   ├─ 子 Agent 派发 (level="sub")：从 tool_calls 中提取 task.subagent_type
      │   ├─ 工具调用 (level="tool")：搜索 query、文件读写、工具返回摘要
      │   └─ 完成/失败 (level="done"/"error")
      │
      ├─ 复制 work_root/skill-distill/ → skills/{owner_id}/{skill_name}/
      ├─ 更新 PG: status=ready, source_count=N
      └─ 推送完成事件
```

**SSE 端点**：`GET /api/v1/characters/{id}/generation-progress`

前端 `EventSource` 连接后接收四层事件：
- `level: "main"` — 主流程进度条
- `level: "sub"` — 子 Agent 卡片逐一出现（12 个，中文标签如 📚调研子智能体）
- `level: "tool"` — 工具调用详情（搜索 query、返回结果摘要）
- `level: "done"/"error"` — 完成（含文件清单）或失败

**子 Agent 可见性**：`astream()` 只能看到主 Agent 的图节点事件。子 Agent 通过 `task` 工具调用，其 `subagent_type` 和 `description` 可从 AIMessage 的 `tool_calls` 中实时提取并推送。子 Agent 内部的搜索/推理过程运行在隔离上下文中，不可见；但其产出文件（`references/research/01-06.md`）包含全部搜索结果和 URL。

**文件映射**：
```
work_root/.gen_work/skill-distill/{skill_name}/  ← Agent 写入
    ↓ shutil.copytree
skills/{owner_id}/{skill_name}/SKILL.md          ← 最终产物
skills/{owner_id}/{skill_name}/references/research/01-06.md
```

### 圆桌讨论引擎架构（deepagent 驱动）

讨论引擎由 `agent_engine/discussion/` 和 `backend/services/discussion/` 两层组成。

```
POST /api/v1/discussions
  │
  ├─ DiscussionService.create_discussion()
  │   ├─ 校验角色 Skill 可用性
  │   ├─ 创建 Discussion + DiscussionAgent PG 记录
  │   ├─ 创建 Orchestrator 实例（传入 skill 路径 + 回调）
  │   └─ asyncio.create_task(_run_orchestrator())
  │
  └─ _run_orchestrator() [background]
      │
      ├─ Orchestrator.run()
      │   ├─ 1. create_roundtable_agent(skill_path) × N
      │   │   └─ 内部调用 deepagents.create_deep_agent()
      │   │       加载角色 SKILL.md（SkillsMiddleware）
      │   │       Agent 通过 read_file 工具主动读取完整 Skill
      │   │
      │   ├─ 2. 主持人开场：_call_host_llm() 独立 LLM 调用
      │   │
      │   ├─ 3. 轮次循环 (while time.time() - start < duration):
      │   │   ├─ 每 Agent 调 agent.ainvoke() 非流式 → 输出
      │   │   │   {"decision":"speak"|"wait","confidence":0.76,"reasoning":"..."}
      │   │   ├─ 收集决策 → 比较 confidence → 最高者发言
      │   │   ├─ 全员沉默 → random.choice() 强制发言
      │   │   └─ 发言人调 agent.astream_events(version="v2") 真流式逐 token 发言
      │   │
      │   └─ 4. 主持人总结：_call_host_llm() 独立 LLM 调用
      │
      ├─ 每轮事件 → on_event 回调：
      │   ├─ Redis Pub/Sub → SSE 推前端
      │   ├─ PG discussion_messages 持久化发言
      │   └─ PG audit_events 业务审计
      │
      └─ 讨论结束 → PG status=completed
```

**身份约束**：系统提示词以"你就是 {skill_name} 本人"开头。think/speak 提示词均强调"你就是你，从你的经历和信念出发"。禁用"作为AI"、"如果我是XX角色"等跳出身份的表达。

**关键文件**：
- `agent_engine/discussion/factory.py` — `create_roundtable_agent(skill_path)` → CompiledStateGraph
- `agent_engine/discussion/orchestrator.py` — `Orchestrator` 类，去中心化调度 + 确信度仲裁
- `backend/services/discussion/service.py` — 讨论生命周期管理 + Redis + Audit 集成
- `backend/services/realtime/router.py` — `GET /discussions/{id}/stream` SSE 端点

### 角色描述引用语
- `CharacterService._to_response` 自动从 `SKILL.md` 中提取 `>` 开头的 blockquote 行作为引用语
- 若有引用语则用它替换 description 字段（取第一条），`_extract_quotes` 最多返回 5 条
- `CharacterResponse.quotes` 列表同时返回全部引用语，`-perspective` 后缀在 `_to_response` 中统一剥离

### 角色 Skill 文件读取

- `skills.file_path` 是角色文件目录的唯一可信来源，格式通常为 `{owner_id}/{skill-name-perspective}`。
- 查看/编辑技能内容链路：`GET /api/v1/characters/{id}` → `GET /api/v1/characters/{id}/files` → `GET /api/v1/characters/{id}/files?path=SKILL.md`。
- 后端读取实际路径：`SKILLS_ROOT / skill.file_path / rel_path`，不要在新代码里重新用 `owner_id + name` 拼接路径。
- 文件访问必须先做权限判断：公开角色可读；私有角色只有 owner 可读；写入只允许 owner。
- 文件缺失要返回明确的 `SKILL_NOT_FOUND`，例如 `Skill files missing on disk: {skill.file_path}`，前端编辑器显示“无法读取技能文件”，不能静默空白。
- `SkillFileManager` 路径校验使用 `Path.resolve()` + `relative_to()`，禁止用字符串 `startswith()` 判断目录归属。

### 人物推荐与主题生成
- `GET /api/v1/characters/recommendations` — LLM 生成 6 位推荐人物（排除已有角色），静态池 46 人作 fallback
- `GET /api/v1/discussions/generate-topic` — LLM 生成讨论主题（~30字），timeout=8s
- 两项均用 `ChatOpenAI(temperature=0.9-1.0)` 直调，不走 deepagent 图

---

### 前端应用架构

**路由代码分割**：使用 react-router v7 `lazy` API 按路由分割代码。9 个页面各自独立 chunk（3-11KB），vendor 共享 chunk（349KB gzip 114KB）。`Layout.tsx` 包裹 `<Suspense fallback={<PageFallback />}>` 避免懒加载时白屏。

```
首次加载 Login → index.html + vendor.js (114KB gzip) + Login.js (1.7KB gzip)
切换页面      → 按需下载目标页面 chunk (1-4KB gzip)，共享 vendor 已缓存
```

**数据缓存**：使用 `@tanstack/react-query` v5 统一管理服务端状态。

- **App.tsx**：`QueryClientProvider` 包裹全局，默认 `staleTime: 30s`、`gcTime: 5min`、`refetchOnWindowFocus: false`
- **查询缓存**：`useQuery({ queryKey, queryFn })` 替代 `useState + useEffect + fetch`。相同 `queryKey` 的请求跨页面共享缓存——切换到已访问过的页面瞬间显示缓存数据，后台静默重新验证
- **变更缓存失效**：`useMutation` 成功后调用 `queryClient.invalidateQueries`，自动刷新相关列表。例如：创建讨论后 Discussions 列表自动更新，画廊复制后 Characters 列表自动刷新
- **缓存 key 体系**：`["characters"]`、`["discussions"]`、`["gallery"]`、`["character", id]`、`["characterFiles", id]`、`["discussion", id]`
- **sessionStorage 缓存**：推荐人物、AI 生成主题等非关键数据用 `sessionStorage` 缓存，刷新页面保留，关闭标签页清空

**关键页面**：

| 页面 | chunk | 特性 |
|------|-------|------|
| GenerateSkill | ~5KB | LLM 人物推荐（6 个），toggle 开关，`sessionStorage` 缓存，换一个 |
| NewDiscussion | ~9KB | 主题+时长同行布局，AI 生成主题（换一个），参与者下拉多选，自定义时长输入 |
| Layout | vendor | 左侧 MADF 图标可点击跳转首页，`<Suspense>` 包裹懒加载页面 |
| Characters | ~5KB | 描述字段由 SKILL.md `>` 引用语替换，`-perspective` 后缀已剥离 |
| Gallery | ~5KB | 同上，描述字段由引用语替换 |
| DiscussionRoom | ~15KB | displayName 去 `-perspective` 后缀，Markdown 渲染 bold/blockquote |

**登录态与路由守卫**：

- 主系统 token key：`localStorage.token`。
- 主系统未登录访问 `/`、`/characters`、`/gallery`、`/discussions` 等业务路由时，`frontend/src/app/components/Layout.tsx` 必须自动跳转到 `/login?redirect={原路径}`。
- 主系统登录成功后，`frontend/src/app/pages/Login.tsx` 读取 `redirect` 参数并 `replace` 回原目标页。
- 只手动点击“退出登录”才进入登录页是不够的；无 token 的首次访问必须自动拦截。
- 主系统 axios 401 拦截保留在 `frontend/src/app/api/client.ts`，用于 token 过期/非法时清理 token 并跳转主系统登录页。

**关键文件**：
- `frontend/src/app/App.tsx` — QueryClient 配置
- `frontend/src/app/routes.tsx` — 路由级 `lazy()` 代码分割
- `frontend/src/app/components/Layout.tsx` — `<Suspense>` 包裹 `<Outlet />`，并负责主系统登录态守卫
- `frontend/src/app/api/client.ts` — axios 实例，BASE=`/api/v1`，401 拦截跳转

---

## 五、代码组织规范

### 分层职责边界

| 层 | 目录命名 | 可以做什么 | 不能做什么 |
|---|---------|----------|----------|
| Router | `router.py` | 接收请求参数并校验（Pydantic schema），调用 Service，HTTP 异常转换 | 不写业务逻辑，不直接操作数据库 |
| Service | `service.py` | 业务规则校验，编排调用流程，事务管理，通过接口调其他模块 Service | 不直接写 SQL，不直接操作文件系统 |
| Repository | `repository.py` | 数据库 CRUD，分页查询，SQL 执行 | 不包含业务判断（如"公开角色才能被搜索"——判断在 Service 层） |
| Models | `models/*.py` | SQLAlchemy ORM 实体定义 | 不直接返回给客户端 |
| Schemas | `schemas.py` | Pydantic Request/Response 模型定义 | — |
| File Manager | `file_manager.py` | 文件系统操作（仅 character 模块）| — |

### 命名约定

| 概念 | 命名 | 示例 |
|------|------|------|
| 数据库实体 | 无前缀 | `User`, `Skill`, `Discussion`, `DiscussionMessage` |
| 请求体 | `XxxCreate` / `XxxUpdate` | `CharacterCreate`, `CharacterUpdate` |
| 响应体 | `XxxResponse` | `CharacterResponse`, `CharacterListResponse` |
| SSE 事件 | `XxxEvent` | `AgentThinkEvent`, `AgentSpeakChunkEvent` |
| 统一响应 | `Result[T]` | `Result[CharacterResponse]` |
| 分页响应 | `PageResult[T]` | `PageResult[CharacterResponse]` |

### 铁律

- **数据库实体绝不直接返回给客户端**。Service 层负责 `Entity → Response` 转换
- **models/ 只在 repository/ 层被引用**。Router 和 Service 不 import ORM 模型
- **通用字段**（id, created_at, updated_at, deleted_at）继承自 `BaseMixin`

---

## 六、外部依赖调用设计

### LLM API 调用

| 调用类型 | 超时 | 熔断 | 说明 |
|---------|------|------|------|
| Agent 决策 JSON（非流式）| 10s | 同 provider 连续失败 3 次 → 本讨论禁用该 provider | `ChatOpenAI(timeout=10)` |
| Agent 发言（流式 token）| 10s 无 token 即断流 | 同上 | `stream: timeout=10`，token 间隔超时触发 `CancelledError` |
| 角色生成全流程 | 60s 整体 | 分阶段超时：搜索 5s/阶段，提炼 15s，验证 15s | — |

- 多 provider 支持：通过 `.env` 配置多个 key，`httpx.AsyncClient` 的 `pool_limits` 限制每个 provider 的最大并发连接数
- 不做线程池隔离（LLM 调用是 async HTTP，不阻塞事件循环）
- 不做高级熔断（半开探测、多 provider 自动 failover）——一期简单熔断够用

### Tavily 联网搜索

- 超时：5s
- API key：`.env` 中 `TAVILY_API_KEY`，支持多 key 逗号分隔（轮询负载均衡）
- 仅角色生成时使用

### SSE 流式响应

- 协议：SSE（单向够用、自动重连、代理友好），一个讨论一个 SSE 连接
- Agent 决策 JSON：`agent.ainvoke()`（非流式，需要完整 JSON）
- Agent 发言：`agent.astream_events(version="v2")` — 监听 `on_chat_model_stream` 事件实现真 token 级流式
- 前端气泡：同发言人同轮追加到同一气泡（不重复创建），typewriter 效果
- 心跳：每 30s 发送 `event: heartbeat`
- Nginx 配置（上服务器后）：`proxy_buffering off; proxy_cache off; chunked_transfer_encoding on;`
- 多 Tab 去重：同一 user + 同一 discussion，新 `client_id` 进入时旧 SSE Task 自动取消

### 重连追赶策略

```
SSE 重连请求: GET /api/v1/discussions/{id}/stream?client_id=xxx&after=timestamp

后端：
  ├─ SELECT count(*) WHERE created_at > after
  ├─ 追赶量 ≤ 20 条 → 逐条 SSE 推送
  ├─ 追赶量 20-200 条 → 批量推送（一次 event 含 20 条）
  └─ 追赶量 > 200 条 → 只推摘要 + 最近 20 条 + 提示查看完整记录
```

断点用 `created_at` 时间戳（不用 id——并发插入顺序和 Redis 推送顺序可能不一致）。

### 文件系统操作

- 技能文件读多写少，使用方案 B 起步 → 后续演进到 C：
  - 当前：PG 元数据 + 直接文件读写
  - 缓存层接口预留（`SkillFileCache` 抽象类），默认实现是直接读文件
  - 后续切换 Redis 实现，不改业务代码
- 文件读写通过 `asyncio.to_thread()` 丢线程池，不阻塞事件循环
- 禁止数据库 BLOB 存文件内容

---

## 七、部署架构

### Docker Compose 拓扑

当前仓库存在两种部署形态，调试时必须先确认正在使用哪一种：

| 形态 | 容器 | 入口 | 说明 |
|------|------|------|------|
| 当前旧拆分部署 | `madf-frontend`、`madf-backend`、`madf-audit-frontend`、`madf-audit-backend`、`madf-postgres`、`madf-redis` | 主系统 `http://localhost/`，审计系统 `http://localhost:81/audit` | 现有本机数据主要在这些原有容器/volume 中；热调试时不要误以为只有 compose 单容器 |
| 新版 compose 单容器 | `madf` + `postgres` + `redis` | 主系统 `http://localhost/`，审计系统 `http://localhost/audit` | `Dockerfile` 内用 supervisord 同时跑 Nginx、主后端、审计后端 |

旧拆分部署注意事项：
- `madf-backend` 使用 `DB_HOST=postgres`、`REDIS_HOST=redis`，必须与 `madf-postgres`、`madf-redis` 在同一个 `madf-new_default` Docker network，并保留 `postgres`/`redis` 别名。
- `madf-frontend` 的 Nginx 代理 `http://backend:8000`；如果后端容器重启导致 IP 变化，需重启 `madf-frontend` 刷新 DNS 解析。
- `madf-audit-frontend` 旧部署监听宿主机 `81` 端口，Nginx 代理 `/api/` 到 `audit-backend:8001`；新版单容器通过 `/audit/api/` 代理。
- 审计前端 API base 会根据 `window.location.port === "81"` 自适应：旧拆分用 `/api/v1`，新版单容器用 `/audit/api/v1`。

```
┌─────────┐     ┌──────────┐     ┌──────────────┐
│  Nginx  │────▶│ FastAPI  │────▶│  PostgreSQL  │
│  :80    │     │  :8000   │     │  :5432       │
└─────────┘     │          │     └──────────────┘
      │         │ agent_   │
      │         │ engine   │     ┌──────────────┐
      ▼         └────┬─────┘────▶│    Redis     │
┌─────────┐         │            │    :6379     │
│  React  │◀────────┘            └──────────────┘
│ 静态文件│         │
└─────────┘         ▼
             ┌──────────────┐
             │  skills/     │
             │  (volume)    │
             └──────────────┘
```

### 组件职责

| 组件 | 部署形态 | 职责 | 数据持久化 |
|------|---------|------|-----------|
| Nginx | Docker 容器 | 静态资源（React dist/）、反向代理、后续开启 SSE 缓冲关闭 | 无状态 |
| FastAPI | Docker 容器 | 路由、业务逻辑、orchestrator、SSE、`agent_engine` 同进程 | 无状态（数据在 PG + FS） |
| React | Nginx 静态托管 | 前端界面 | 无状态 |
| PostgreSQL | Docker 容器 | 用户、角色元数据、讨论、消息、审计事件 | volume: `pg_data/` |
| Redis | Docker 容器 | Pub/Sub 实时事件通道 | 不需要持久化 |

### Volume 挂载

| volume | 路径 | 用途 | 丢了会怎样 |
|--------|------|------|-----------|
| `pg_data/` | PG 数据目录 | 用户、角色、讨论、审计全部数据 | **所有数据丢失** |
| `skills/` | 角色 Skill 文件 | 完整 skill 目录（SKILL.md + references/） | 角色不可用，讨论无法创建 |
| `logs/` | 应用日志 | JSON 格式日志 | 排查历史丢失 |

### 请求链路

**链路一：注册/登录**
```
浏览器 → Nginx(:80) → FastAPI(:8000)
  → Router 校验 → Service → Repository → PG users 表
  → 返回 JWT token
```

**链路二：创建讨论 + 实时观看**
```
1. POST /api/v1/discussions → DiscussionService:
   ├─ 查 CharacterService 加载角色 Skill（读 FS + PG 元数据）
   ├─ 创建 Discussion + DiscussionAgent ORM 记录
   └─ 创建 Orchestrator asyncio.Task

2. 浏览器打开 SSE: GET /discussions/{id}/stream
   → RealtimeRouter → SSEManager 注册连接 → 订阅 Redis channel

3. Orchestrator 后台运行:
   ├─ 主持人开场（LLM 流式）
   ├─ 每轮: 各 Agent 调 LLM → 收集决策 JSON → 比较确信度 → 最高者流式发言
   ├─ 每次事件: 写 PG + 推 Redis → SSE → 前端气泡
   ├─ 写 audit_events
   └─ 到时: 主持人总结 → 标记 discussion.status='completed'
```

**链路三：生成角色 Skill**
```
POST /api/v1/characters/generate → CharacterService:
  ├─ 创建 skill 目录 skills/{user_id}/{skill-name}/
  ├─ 写 PG 元数据 (status='generating')
  └─ 启动 SkillGenService asyncio.Task

SkillGenService:
  Phase 0: 入口分流 → Phase 1: 6 个调研 Agent 并行搜索（Tavily 5s 超时）
  → Phase 2: 提炼框架 → Phase 3: 构建 SKILL.md
  → Phase 4: 3 个验证 Agent 并行 → Phase 5: 2 个优化 Agent 并行
  → 写入 SKILL.md + references/research/*.md → 更新 PG (status='ready')
```

### 安全

- 密码：bcrypt hash 存储，不存明文
- JWT：无状态 token，带过期时间
- 敏感配置（LLM API key、Tavily key、JWT secret）：全部在 `.env` 中，不提交到 git
- SQL 注入：通过 SQLAlchemy ORM 参数化查询，禁止字符串拼接 SQL

---

## 八、数据模型

### 数据库选型

| 存储类型 | 产品 | 用途 |
|---------|------|------|
| 关系型数据库 | PostgreSQL | 全部业务数据 |
| 缓存/消息 | Redis | Pub/Sub 实时事件 + 后续 Skill 缓存 |
| 文件存储 | 本地文件系统（volume 挂载）| 角色 Skill 文件（SKILL.md + references/） |

### 核心实体关系（主系统 6 张业务表）

```
User ──┬── Skill         (1:N，一个用户有多个角色)
       ├── Discussion    (1:N，一个用户创建多场讨论)
       └── AuditEvent    (1:N)

Skill ──── DiscussionAgent (1:N，一个角色可被多场讨论使用)

Discussion ──┬── DiscussionAgent  (1:N)
             ├── DiscussionMessage (1:N，🔴 高增长表）
             └── AuditEvent       (1:N)

DiscussionMessage 的 message_type 枚举:
  host_intro | host_summary | agent_think | agent_speak | user_intervene
```

### 核心实体清单

| 功能域 | 数据对象 | 增长等级 | 说明 |
|-------|---------|---------|------|
| 用户域 | User | 🟢 | 用户基本信息（id, username, password_hash, phone） |
| 角色域 | Skill | 🟢 | 角色元数据索引——桥接 PG 和 FS（id, owner_id, name, description, file_path, tags, is_public, status, source_count, model_count） |
| 讨论域 | Discussion | 🟢 | 一场圆桌讨论（id, owner_id, topic, duration, status, started_at, ended_at） |
| 讨论域 | DiscussionAgent | 🟢 | 讨论参与者（discussion_id, skill_id） |
| 讨论域 | DiscussionMessage | 🔴 | 讨论消息（discussion_id, round_number, agent_id, agent_name, message_type, content, confidence） |
| 审计域 | AuditEvent | 🟡 | 业务审计事件（discussion_id, user_id, event_type, payload JSONB, level） |

审计后台另有 4 张本地管理表：`audit_admin_users`、`audit_access_log`、`audit_integrity_rules`、`audit_retention_policies`。`audit_backend.models.AuditEvent` 是主系统 `audit_events` 的只读镜像，不写入。

---

## 九、数据库设计规范

### 通用字段（每张表必须有）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID v4 | 当前所有主系统 ORM 实体统一继承 `BaseMixin`，包括 `discussion_messages` |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | 创建时间，ORM 自动维护 |
| updated_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | 更新时间，ORM 自动维护（SQLAlchemy `onupdate=utcnow`），业务代码不手写 |
| deleted_at | TIMESTAMPTZ DEFAULT NULL | 软删除标记；Repository 查询必须显式带 `deleted_at IS NULL` |

### 核心规范

| 规范项 | 决策 | 说明 |
|-------|------|------|
| 主键策略 | UUID v4 | 当前代码未实现 UUID v7 |
| NULL 处理 | 核心业务字段 NOT NULL + 默认值；可选字段（phone, confidence）允许 NULL | NULL 有语义价值——代表"未设置/不存在" |
| 枚举字段 | VARCHAR + CHECK 约束 | 比 ENUM 类型更易演进，新增枚举值不锁表 |
| 数据库外键 | 建 FOREIGN KEY | 单库场景数据一致性有保障 |
| 外键删除策略 | 讨论 → 消息 CASCADE；讨论参与角色 → skill RESTRICT；消息 agent_id → skill SET NULL；audit user/discussion → SET NULL；其他未声明 ondelete 的 FK 由数据库默认约束处理 | — |
| 字符集 | UTF-8 | 建库时 `ENCODING 'UTF8'` |
| 金额/精度 | 不适用（系统无金额字段） | — |

### 索引规范

| 规范 | 决策 |
|------|------|
| 等值 + 排序复合索引列顺序 | 等值在前，排序/范围在后——`(discussion_id, created_at DESC)` |
| 软删除字段 | 唯一索引用**部分索引** `WHERE deleted_at IS NULL`；普通查询索引当前按模型实际定义为准 |
| 排序列 | 排序列必须进组合索引，和等值列一起构成完整覆盖 |
| 大文本字段（content, description） | **禁止建普通 B-Tree 索引**。全文搜索需求后续用 tsvector 或 Elasticsearch |
| 唯一约束 | 必须在数据库层（不靠应用层并发判断），软删除场景用部分唯一索引 `WHERE deleted_at IS NULL` |
| 多对多方向索引 | `discussion_agent` 表：`skill_id` 上建单独索引（支持"按角色查讨论"） |
| 单表索引数量 | 一期不设硬性上限，数据量上来后审计慢查询日志调优 |

### 核心索引清单

| 表 | 索引 | 覆盖查询 |
|----|------|---------|
| users | `idx_users_username_unique UNIQUE (username) WHERE deleted_at IS NULL` | 注册查重 |
| users | `idx_users_phone_unique UNIQUE (phone) WHERE deleted_at IS NULL` | 手机号查重 |
| skills | `idx_skills_owner_created (owner_id, created_at)` | 用户角色列表 |
| skills | `(is_public, created_at) WHERE is_public = true AND deleted_at IS NULL` | 画廊公开角色 |
| skills | `idx_skills_owner_name_unique UNIQUE (owner_id, name) WHERE deleted_at IS NULL` | 同一用户角色名不重复 |
| discussions | `idx_discussions_user_created (owner_id, created_at)` | 用户讨论列表 |
| discussion_agents | `idx_da_discussion (discussion_id)` | 查讨论的参与角色 |
| discussion_agents | `idx_da_skill (skill_id)` | 按角色查讨论 |
| discussion_messages | `idx_dm_discussion_round_created (discussion_id, round_number, created_at)` | 讨论消息按轮次查（最高频查询） |
| audit_events | `idx_ae_discussion_created (discussion_id, created_at)` | 按讨论查审计事件 |
| audit_events | `idx_ae_user_created (user_id, created_at)` | 按用户查审计事件 |

### 大表增长预判

| 🔴 高增长 | 增长速度 | 应对策略 |
|----------|---------|---------|
| DiscussionMessage | 每场约 300 条（5 Agent × 30 轮 × 每轮 2 条：think + speak），1000 场 = 30 万条 | 复合索引 `(discussion_id, round_number, created_at)` 已建；后续破千万考虑按时间 RANGE PARTITION |

| 🟡 中等增长 | 应对 |
|------------|------|
| AuditEvent | 每场 50-100 条，同 discussion_id 索引，后续考虑定期归档 |

| 🟢 低增长 | 应对 |
|----------|------|
| User / Skill / Discussion / DiscussionAgent | 标准索引足够，不需要分区 |

### 分页规范

| 场景 | 分页方式 | pageSize 默认 | pageSize 最大 | 约定 |
|------|---------|-------------|-------------|------|
| 讨论消息（实时+回放） | 游标（after=created_at） | 50 | 100 | 无 total，只有 hasMore |
| 画廊公开角色 | 游标（after=created_at） | 20 | 50 | — |
| 用户角色列表 | 传统 OFFSET（page + pageSize） | 20 | 100 | 返回 total + hasMore |
| 用户讨论列表 | 传统 OFFSET | 20 | 50 | total 只查第一页 |
| 审计事件 | 游标（after=created_at） | 50 | 100 | — |

---

## 十、接口规范

### URL 路径风格

```
所有 API 前缀: /api/v1/

RESTful 资源:
  GET    /api/v1/characters            # 列表（有分页）
  POST   /api/v1/characters            # 创建
  GET    /api/v1/characters/{id}       # 详情
  PUT    /api/v1/characters/{id}       # 全量更新
  DELETE /api/v1/characters/{id}       # 软删除

非 CRUD 操作（动词后缀，用下划线）:
  POST   /api/v1/characters/{id}/generate     # 触发角色生成
  POST   /api/v1/characters/{id}/copy          # 复制到我的
  POST   /api/v1/discussions/{id}/intervene    # 用户介入发言
  GET    /api/v1/admin/audit/events            # 主后端管理侧审计事件查询
  GET    /api/v1/audit/events                  # 审计后端审计事件查询（audit_backend）
  GET    /api/v1/characters/recommendations    # 人物推荐（LLM 生成，排除已有角色）
  GET    /api/v1/discussions/generate-topic    # AI 生成讨论主题

SSE 端点:
  GET    /api/v1/discussions/{id}/stream       # 讨论实时流
  GET    /api/v1/characters/{id}/generation-progress  # 角色生成进度
```

### 统一响应结构

```json
// 成功
{
  "code": 200,
  "message": "success",
  "data": { ... }
}

// 分页
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "has_more": true
  }
}

// 错误
{
  "code": 4001,
  "message": "Discussion not found",
  "data": null
}
```

- `code`：业务状态码（非 HTTP 状态码）
- `message`：给人看的提示，出错时帮助排查
- `data`：实际数据
- HTTP 层面按标准语义：200/201/400/401/403/404/500
- 统一响应类：`Result[T]`，分页响应类：`PageResult[T]`

### 空值返回

按字段语义区分：

| 字段类型 | 策略 | 示例 |
|---------|------|------|
| 始终适用的字段 | 永远返回，空值时返回 `null` | `phone`、`description`——字段天然属于此对象 |
| 条件适用的字段 | `exclude_none`，不适用时字段不存在 | `confidence`——仅 Agent 思考消息有，用户消息不该有 |

实现：Pydantic `model_dump(exclude_none=True)` 配合 schema 设计时条件字段用 `Optional[X] = None`。

### 错误码分段

| 范围 | 模块 |
|------|------|
| 1000-1999 | 通用（1001 参数校验、1002 认证失败、1003 权限不足、1999 系统异常） |
| 2000-2999 | 用户模块 |
| 3000-3999 | 角色模块 |
| 4000-4999 | 讨论模块 |
| 5000-5999 | 审计模块 |

### SSE 事件类型

```
event: agent_think
data: {"agent_id": "...", "agent_name": "Steve Jobs", "round": 3, "decision": "speak", "confidence": 0.87}

event: agent_speak_start
data: {"agent_id": "...", "agent_name": "Steve Jobs", "round": 3}

event: agent_speak_chunk
data: {"agent_id": "...", "content": "I think..."}

event: agent_speak_end
data: {"agent_id": "..."}

event: host_intro
data: {"content": "Welcome to today's..."}

event: host_summary
data: {"content": "In summary..."}

event: round_start
data: {"round": 3}

event: discussion_end
data: {"summary": "..."}

event: user_intervened
data: {"user_id": "...", "content": "..."}

event: heartbeat
data: {}
```

### 角色生成进度 SSE 事件类型

```
生成进度流: GET /api/v1/characters/{id}/generation-progress

SSE data JSON 格式: {"level": "...", "message": "...", "extra": {...}}

level 类型:
  "idle"   — 未开始
  "main"   — 主流程阶段（阶段 0-5、复制文件等）
  "sub"    — 子 Agent 被派发时触发
  "tool"   — 工具调用（搜索 query、文件读写、工具返回摘要）
  "done"   — 生成完成（含文件清单）
  "error"  — 生成失败

示例事件流:
data: {"level":"main","message":"阶段 0/5：正在创建 Deep Agent 实例…"}
data: {"level":"main","message":"阶段 1/5：调度 6 个并行调研子智能体，通过 Tavily 联网搜索…"}
data: {"level":"sub","message":"📚 调研子智能体：搜集著作与系统性长文","extra":{"agent":"researcher-writings","seq":1}}
data: {"level":"sub","message":"🎙️ 调研子智能体：搜集对话与深度访谈","extra":{"agent":"researcher-conversations","seq":2}}
data: {"level":"tool","message":"联网搜索 (Tavily)：Steve Jobs Stanford speech","extra":{"tool":"internet_search","query":"...","seq":3}}
data: {"level":"done","message":"生成完成，共 7 个文件","extra":{"file_count":7,"subagents_spawned":12,"files":["SKILL.md (12,470 字节)",…]}}
```

---

## 十一、业务流程关键设计

### 去中心化发言流程（每轮）

```
1. Orchestrator 广播当前上下文给所有参与 Agent
2. 每个 Agent 调用 LLM（非流式）→ 输出决策 JSON:
   {"decision": "speak|wait", "confidence": 0.87}
3. Orchestrator 收集所有决策:
   ├─ 有人选择 speak → 最高确信度者获得发言权 → agent.astream_events(v2) 真流式发言（逐 token）
   └─ 全员选择 wait → 随机选一个 Agent 强制发言（打破僵局）
4. 发言内容写 PG → 推 Redis → SSE → 前端气泡 typewriter
5. 写 audit_events
6. 进入下一轮
```

### 用户介入发言流程

```
1. 用户在前端输入框输入文字 → Enter 或点击发送
2. HTTP POST /api/v1/discussions/{id}/intervene → {"content": "..."}
3. Orchestrator 收到 → 写入 DiscussionMessage (message_type='user_intervene')
4. 广播 SSE event: user_intervened
5. 将用户发言注入各 Agent 下一轮上下文: "观众说：xxx，请考虑此观点"
```

### 讨论结束流程

```
1. duration 到期 → Orchestrator 停止新轮次
2. 主持人 Agent 收到"请对以上讨论做总结" → `_call_host_llm()` 独立 LLM 调用输出摘要
3. 写 DiscussionMessage (message_type='host_summary')
4. 标记 discussion.status = 'completed' + ended_at = NOW()
5. 关闭 Redis channel
6. 推送 SSE event: discussion_end
```

---

## 十二、业务审计

### 基础设施

- 存储：PostgreSQL `audit_events` 表（event_type + payload JSONB + user_id + discussion_id）
- 服务：`AuditRepository.record(discussion_id, user_id, event_type, payload, level="P2")`
- 接口：主后端 `GET /api/v1/admin/audit/events` / `GET /api/v1/admin/audit/operations`；审计后台 `GET /api/v1/audit/events` / `GET /api/v1/audit/events/context/{discussion_id}`。
- 集成方式：各模块 Service 层直接注入 `AuditRepository`（同 session，事务一致）

### 审计事件分级

| 级别 | 含义 | 触发条件 |
|------|------|---------|
| **P0** | 必须审计 | 安全事件、资源消耗（LLM/Tavily 调用）|
| **P1** | 应该审计 | 数据变更、生命周期事件、跨用户操作 |
| **P2** | 可以审计 | 数据修改、内容变更 |

### 审计事件目录

**用户模块**：
| 事件 | 级别 | payload |
|------|------|---------|
| `user.register` | P1 | username, phone |
| `user.login` | P0 | username |
| `user.login_failed` | P0 | username, reason（user_not_found / wrong_password） |

**角色模块**：
| 事件 | 级别 | payload |
|------|------|---------|
| `skill.generate` | P0 | skill_id, query, skill_name |
| `skill.generate_complete` | P1 | skill_id, file_count, subagents_spawned |
| `skill.generate_error` | P1 | skill_id, error |
| `skill.create` | P2 | skill_id, skill_name, is_public |
| `skill.update` | P2 | skill_id, skill_name, changed_fields |
| `skill.delete` | P1 | skill_id, skill_name |
| `skill.copy` | P1 | src_skill_id, src_owner_id, dst_skill_id |
| `skill.file_write` | P2 | skill_id, file_path |

**讨论模块**：
| 事件 | 级别 | payload |
|------|------|---------|
| `discussion.create` | P1 | topic, duration, character_ids |
| `discussion.error` | P1 | error |
| host_intro / host_summary | — | 通过 orchestrator event handler 自动进入 |
| round_start / agent_speak_chunk | — | 同上 |
| `agent_think` | ⚠️ | 数据归属在 discussion_messages 表，不进入 audit_events |

**讨论运行时事件**（通过 orchestrator `on_event` 回调自动进入）：
host_intro, host_intro_start, round_start, agent_think, agent_speak_chunk, host_summary_start, host_summary, discussion_end

### 不审计的操作

- 只读查询（GET list/detail/gallery/files/me/messages）——无数据变更，无安全风险
- 高频中间状态（生成进度 SSE events、心跳）——纯展示层，无业务审计价值
- agent_think 决策数据——归属 discussion_messages 表（message_type="agent_think"），用于讨论回放和分析

### 集成规则

- 每个模块的 Service 层独立注入 `AuditRepository`，不依赖其他模块
- Router 层只管参数校验和调用 Service，不直接操作 AuditRepository
- 审计写入与业务操作共享同一个 DB session——成功则一起提交，失败则一起回滚
- `user_id` 在写入时已知则传入，未知（如登录失败时用户不存在）则传 None

---


## 十二-A、管理后台（企业级运维控制台）

### 架构拓扑

管理后台是旁路半独立架构，通过审计后端代理主系统 API：

```
管理员浏览器 (81端口) → audit-frontend (React)
    ↓ 管理 API 请求
审计后端 (8001端口, FastAPI)
    ↓ 签发服务 JWT (ADMIN_JWT_SECRET, 5min, jti 防重放)
    ↓ httpx 转发
主系统 (8000端口, FastAPI)
    ↓ backend/middleware/admin_auth.py 验证服务 JWT
    ↓ 执行管理操作 + 记审计事件
```

访问入口按部署形态区分：
- 旧拆分部署：`http://localhost:81/audit`，登录页 `http://localhost:81/audit/login`。
- 新版单容器部署：`http://localhost/audit`，登录页 `http://localhost/audit/login`。

审计系统登录态必须与主系统隔离：
- 审计 token key：`localStorage.audit_token`；管理员信息 key：`localStorage.audit_admin`。
- 主系统 token key：`localStorage.token`，不得用于审计系统。
- 审计系统未登录访问 `/audit`、`/audit/users`、`/audit/discussions`、`/audit/health` 等页面时，`audit-frontend/src/app/components/Layout.tsx` 必须跳转到审计登录页 `/audit/login?redirect={审计内路径}`。
- 审计登录成功后，`audit-frontend/src/app/pages/AdminLogin.tsx` 读取 `redirect` 参数并回到原审计页面。
- 审计 API 401 拦截在 `audit-frontend/src/app/api/client.ts`，只能清理 `audit_token`/`audit_admin` 并跳转 `/audit/login`，不能跳主系统 `/login`。

### 核心组件

| 组件 | 路径 | 职责 |
|------|------|------|
| 管理前端 | `audit-frontend/` | 11 个页面的管理后台（浅色主题，与主系统一致） |
| 审计后端 | `audit_backend/` | 审计查询 + 管理员认证 + 代理网关 |
| 管理 API | `backend/services/admin/` | 管理接口集合，服务 JWT 鉴权 |
| 服务间认证 | `backend/middleware/admin_auth.py` | 验证服务 JWT + jti 防重放 |
| 代理网关 | `audit_backend/services/admin_proxy/` | 签发 JWT + httpx 转发 |
| 审计 API base | `audit-frontend/src/app/api/base.ts` | 旧拆分部署 `/api/v1`；新版单容器 `/audit/api/v1` |
| 数据库 | `audit_events` 表 + `audit_admin_users` 等 5 张审计表 | 独立 level 列（P0/P1/P2）|

### 功能页面

| 页面 | 路由 | 关键数据 |
|------|------|---------|
| 仪表盘 | `/` | 统计卡片、健康灯、token 趋势、最近 P0 异常 |
| 用户管理 | `/users` | 列表/详情/禁用/改密码/改用户名 |
| 讨论监控 | `/discussions` | SSE 旁听、消息历史、删除 |
| 审计与追溯 | `/audit` | 时间线视图、筛选、Payload 展开 |
| 系统健康 | `/health` | 组件状态、异常详情、系统负载 |
| 管理员 | `/admins` | 审计员 CRUD |
| 设置 | `/settings` | 端口配置+重启、告警阈值、保留策略 |

### 管理 API 清单（当前 41 个，`/api/v1/admin/*`）

- 用户管理 9：列表、创建、详情、状态、用户名、密码、手机号、token 用量、删除
- 讨论监控 6：列表、详情、SSE、消息、删除、token 用量
- 角色管理 4：列表、详情、可见性、删除
- 画廊管理 2：列表、下架
- 审计与追溯 4：事件列表/详情、操作列表/详情
- 系统健康 5：概览、错误列表/详情、负载、孤儿讨论
- 统计总览 3：概览、token 统计、token 趋势
- 管理员管理 4：列表、创建、更新、删除
- 设置 4：读取/更新设置、重启、保留策略更新

### 审计事件 level 系统

level 是 `audit_events` 表的独立列（迁移 `7883e7a9b2c1` 添加）。
`AuditRepository.record()` 增加 `level` 参数（默认 P2），新事件必须显式传入。

| 新增事件 | level |
|---------|------|
| system.error | P0 |
| system.db_pool_error | P0 |
| system.redis_pubsub_error | P1 |
| user.status_changed | P0 |
| user.username_changed | P0 |
| user.password_reset | P0 |
| discussion.deleted_by_admin | P1 |
| skill.visibility_changed | P1 |
| character.deleted_by_admin | P1 |
| gallery.unlisted | P1 |

### 健康检查

`GET /api/v1/health` — 存活检查（保持轻量，Docker healthcheck 用）
`GET /api/v1/health/detailed` — 深度检查（DB SELECT 1 + Redis PING + LLM API 可达性）

### Agent 超时保护

`agent_engine/discussion/orchestrator.py` 三个 LLM 调用点全部加超时：
- `_agent_think_fast`: 15s 超时 → 降级为 wait
- `_agent_speak_stream`: 10s 无 token → 跳过本轮发言
- `_call_host_llm_stream`: 10s 无 token → 降级为短摘要


## 十三、AI 行为指令

### 写代码时

- 采用 TDD：先写测试 → 测试失败 → 写最简实现 → 测试通过 → 重构（如有必要）
- 用最简单直接的方式实现功能，不做过度抽象，不引入设计模式（除非用户明确要求可扩展）
- 所有外部调用（LLM API、Tavily、Redis）必须设置超时
- 配置项外化到 `.env` 或配置文件，不硬编码
- 发现潜在问题时主动提醒用户
- **禁止**：不引入技术栈之外的依赖（需要新库时，先说明理由，等用户确认后再加）
- **禁止**：不猜测业务逻辑——不确定时提问，不自创规则
- **禁止**：不擅自重构已有代码

### 改代码时

- 先理解相关模块的设计意图再动手
- 改动前说明影响范围
- 不破坏已有接口契约
- 改完后确保已有测试通过
- **禁止**：不顺手修改无关模块——让它改 A，它不改 B

### 不确定时

- 架构选择：给出 2-3 个方案对比，优缺点说清楚，由用户拍板（不给推荐结论）
- 规范没覆盖的情况：不自创规则，先问用户怎么处理，然后决定是否补充到 AGENTS.md
- 遇到可能影响架构边界的改动：先说明影响范围，等用户确认后再动手

### 代码风格

- 默认不写注释。只在 WHY 非显而易见时加一行短注释
- 不写多段 docstring 或多行注释块
- 避免安全漏洞：命令注入、XSS、SQL 注入
- 不加功能特性、不重构、不引入抽象——超出任务范围的都不做

---

## 十四、演进触发条件

| 阶段 | 触发条件 | 改动 |
|------|---------|------|
| **当前** | — | 单进程 FastAPI + `agent_engine` 同进程 + Redis Pub/Sub + PG 单库 |
| **阶段 1** | 并发讨论 > 80 场 | gunicorn 多 worker + PgBouncer 连接池 |
| **阶段 2** | Agent 需独立部署 / 多租户隔离 | Agent Service 独立进程 + RabbitMQ 替代 Redis Pub/Sub |
| **阶段 3** | SaaS 多租户 | 按 tenant 分库 + 完整监控（Prometheus + Grafana） |

**核心原则**：触发条件不到，不提前演进。每个"暂不做"都标注触发条件，不是因为看不见，而是因为现在做了没收益。

---

## 十六、测试规范

### 核心原则

测试必须是发布门禁，不是开发过程中的临时脚本。任何测试都要满足三个条件：可一键运行、失败能阻断发布、断言能验证业务结果。

HTTP 200 不等于功能正确。关键链路必须验证 API 响应、数据库状态、审计事件、前端展示中的至少两个层面；审计、安全、权限、token 用量等高风险链路必须做跨层交叉验证。

### 核心链路（按风险优先级）

| # | 链路 | 风险类型 | 最低测试要求 |
|---|------|---------|-------------|
| 1 | **讨论生命周期**（创建 -> orchestrator -> 发言 -> 结束） | 并发、数据一致性、SSE 断线 | 真实 PG+Redis 集成测试；验证消息、状态、审计事件 |
| 2 | **审计事件写入与查询** | 静默失败、身份丢失、追责失败 | 操作后查询审计事件；验证真实 user_id/admin_id、event_type、level、payload |
| 3 | **用户认证与权限**（注册 -> 登录 -> JWT -> 鉴权） | 越权、重放、默认密钥 | 集成测试覆盖 401/403、过期/非法 token、权限边界 |
| 4 | **角色 CRUD + 文件系统** | 文件系统异常、路径穿越、权限越界 | 集成测试 + 文件管理单测；验证路径穿越不落盘 |
| 5 | **Skill 生成管线**（deepagent + Tavily + LLM） | 外部依赖失败、超时、输出质量 | 默认 mock 外部服务；保留可手动运行的真实 LLM 冒烟测试 |
| 6 | **Admin/Audit 前端工作台** | 指标误报、Invalid Date、操作不可达 | 组件/页面测试 + Playwright E2E；验证交互、格式、状态颜色、错误态 |

### 测试分层

| 层 | 范围 | 依赖 | 要求 |
|----|------|------|------|
| **L1 单元测试** | Pydantic schema、纯函数、文件路径校验、错误码映射、工具函数 | 不连接 DB/Redis/LLM | 不允许导入会初始化真实 engine 的 `backend.main` |
| **L2 服务测试** | 有明确业务分支的 Service | mock Repository、Audit、外部 API | 只测业务规则，不测 SQL 细节 |
| **L3 API 集成测试** | Router -> Service -> Repository -> DB 完整链路 | 真实 PG+Redis，通过迁移初始化 | 每个测试生成唯一数据，不依赖历史库状态 |
| **L4 E2E 测试** | 登录、角色、讨论、审计后台核心流程 | 浏览器 + 已启动服务 | 必须用断言失败退出，不能只打印结果 |
| **L5 外部服务冒烟** | 真实 LLM/Tavily/deepagent 输出质量 | 真实 key，手动或 nightly | 不进入默认 PR 阻塞套件，除非成本和稳定性可控 |

### 可运行性要求

所有测试入口必须清晰、可复现。新增或修改测试时，同时保证以下命令至少有一个稳定可用：

```bash
# 后端单元测试：不依赖容器
python -m pytest tests/ -m "not integration and not e2e"

# 后端集成测试：依赖 PG + Redis + alembic upgrade head
python -m pytest tests/ -m integration

# 主前端测试
cd frontend && npm run test

# 审计前端测试
cd audit-frontend && npm run test
```

如果某个测试需要特殊环境，必须用 `pytest.mark.integration`、`pytest.mark.e2e`、`pytest.mark.external` 或清晰命名隔离，不能让默认单测收集阶段失败。

### 测试隔离

- 测试收集阶段不能初始化真实数据库连接、Redis 连接、LLM client 或后台任务。
- `conftest.py` 只能放轻量 fixture；需要 FastAPI app 时延迟导入，避免所有测试被 DB 依赖拖死。
- 集成测试使用唯一用户名、唯一 discussion topic、唯一 skill/character 名称；禁止固定复用 `int_test_user` 这类全局账号作为断言基础。
- 每个集成测试必须能单独运行、重复运行、乱序运行。
- 需要依赖已有数据时，应在测试内显式创建，并在断言中使用创建结果的 id。
- mock 只能隔离外部不稳定依赖，不能 mock 掉当前要验证的业务规则。

### CI 门禁

CI 不能靠大量 `--ignore` 或 `-k "not ..."` 掩盖失败。允许拆 job，但必须保留以下门禁：

1. Python lint：`ruff check backend/ agent_engine/ audit_backend/`
2. Python unit：不需要 PG/Redis，必须快速通过
3. Python integration：启动 PG/Redis，执行 Alembic，覆盖注册、登录、角色、讨论、审计
4. 主前端：typecheck + vitest
5. 审计前端：typecheck + vitest
6. Docker smoke：验证主 SPA、审计 SPA、主 API、审计 API 都通过反向代理可访问

如果某个核心测试暂时不能进 CI，必须在 PR/提交说明里写明原因、替代验证方式和恢复条件。

### 前端测试标准

前端测试不能只搜关键词。至少验证：

- 表单输入、按钮可点击、loading/disabled 状态正确
- API 成功、失败、空数据、未登录四类状态
- 日期不是 `Invalid Date`
- 数字、token 用量、百分比、分页计数格式正确
- 状态颜色和文案一致，例如 healthy/unhealthy、enabled/disabled
- 路由跳转、鉴权重定向、localStorage/session 状态变化

Playwright 脚本必须改成真正测试：失败时抛异常或 `expect` 失败，不能只把结果打印到 stdout。截图只能作为调试产物，不能替代断言。

### 覆盖率目标

覆盖率用于发现盲区，不用来替代业务断言。最低目标：

| 模块 | 目标 |
|------|------|
| `backend/core/` | 90%+ |
| `backend/services/*/schemas.py` | 95%+ |
| `backend/services/*/service.py` | 80%+，高风险分支必须覆盖 |
| `backend/services/*/repository.py` | 通过集成测试覆盖主要查询、排序、分页、权限过滤 |
| `backend/middleware/` | 80%+ |
| `agent_engine/discussion/` | 覆盖超时、降级、异常审计、消息归属 |
| `frontend/src/app/api/` | 80%+ |
| `frontend/src/app/store/` | 80%+ |
| `audit-frontend/src/app/` | 核心页面和 API client 必须有测试 |

### 不写单测的范围

- **第三方框架内部**：FastAPI、SQLAlchemy、deepagents、React Query 等由其自身测试覆盖。
- **纯 ORM SQL 生成细节**：不 mock repository 来假测 SQL，使用集成测试验证排序、分页、过滤、权限边界。
- **真实 LLM 输出质量**：默认不进入 PR 阻塞套件，使用 mock/fixture 验证解析、超时、降级、审计。

### 测试命名

```python
def test_should_[期望结果]_when_[条件]():
    ...
```

文件命名：

- pytest 可自动收集的测试必须命名为 `test_*.py`
- 手动脚本必须放到 `scripts/` 或显式标注，不能伪装成测试文件
- 前端测试使用 `*.test.ts(x)` 或 `*.spec.ts(x)`

### 禁止项

| 禁止 | 原因 |
|------|------|
| 只检查 HTTP 状态码 | 字段映射、权限泄漏、审计丢失都会漏检 |
| 测试失败后用 `--ignore`、`-k not` 长期绕过 | CI 通过会失去发布门禁意义 |
| 固定复用历史账号/历史数据 | 导致顺序依赖和重复运行失败 |
| 模块顶层启动浏览器、连接 DB、调用 LLM | pytest 收集阶段会失败或变慢 |
| 前端测试只检查页面包含某个中文词 | 不能证明交互、格式、状态正确 |
| 修 Bug 只跑单条测试 | 无法发现回归 |

### 正确的测试流程：模拟管理员一日工作

测试代码按真实业务流程组织，每一步产生可验证的断言，前一步的产出（user_id、discussion_id）作为后一步的输入：

1. **登录看大屏**：真实账号登录 -> 健康组件状态全部正常 -> 统计卡片数字 > 0 -> 日期非 Invalid Date
2. **禁用用户闭环**：查用户列表 -> 禁用 -> API 返回 status=disabled -> 直查 DB 确认 deleted_at 非空 -> 审计事件含真实 admin_id
3. **全链路回放**：注册 -> 创建讨论 -> 等待结束 -> 审计事件完整链（create -> speak -> end）-> 讨论 token 用量 > 0
4. **跨层交叉验证**：每个高风险业务操作验证 API 响应、数据库变更、审计事件记录、前端 UI 展示

### 已知风险点

1. `_run_orchestrator` 异常分支需要验证：崩溃场景必须写入审计事件并更新 discussion 状态。
2. `agent_speak_chunk` 写入 `discussion_messages` 的归属需要验证：不能重复、串讨论或丢 round_number。
3. 并发讨论时 `_active_orchestrators` 字典需要并发安全验证。
4. SQL 查询排序、分页、权限过滤必须用集成测试验证。
5. Admin API 不能依赖默认密钥和固定 localhost；测试应支持 ASGI 或可配置 base URL。
6. 前端 localStorage、鉴权跳转、审计后台图表/日期格式必须纳入自动测试。

### 回归套件

任何 Bug 修复后必须运行相关单测 + 对应集成测试；发布前必须运行全部 CI 门禁。不通过 = 不发布。

新增功能必须同时新增测试。无法新增测试时，必须说明原因、人工验证步骤和后续补测任务。


## 十七、操作清单

### 当前状态

| 指标 | 值 |
|------|-----|
| API 端点 | 23 个 |
| 数据库表 | 6 张 |
| 审计事件 | 全模块 P0/P1/P2 |
| 集成测试 | 27/27 pass |
| 单元测试 | 96/96 pass |
| Docker 容器 | 旧拆分部署 6 个（主前端/主后端/审计前端/审计后端/PG/Redis）；新版 compose 为 `madf` + PG + Redis |
| 前端页面 | 9 个（登录/首页/角色列表/角色详情/讨论列表/讨论室/画廊/生成角色/新建讨论） |
| 前端数据缓存 | @tanstack/react-query，staleTime 30s，gcTime 5min |
| 前端代码分割 | react-router lazy，9 个页面独立 chunk（3-15KB） |

### 启动命令

```bash
# 开发模式
cd backend && uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev

# 生产模式
docker compose up -d
bash start.sh

# 旧拆分容器调试（本机历史数据常在这组容器里）
docker start madf-postgres madf-redis madf-backend madf-frontend madf-audit-backend madf-audit-frontend
docker network connect --alias postgres madf-new_default madf-postgres || true
docker network connect --alias redis madf-new_default madf-redis || true
```

### 部署前检查

- [x] `.env` 文件已配置：LLM API key + Tavily key + JWT secret + PG/Redis 连接信息
- [x] `skills/` 目录 volume 已挂载
- [x] `pg_data/` volume 已挂载
- [x] Nginx 配置：`proxy_buffering off`（SSE 必经之路）
- [x] JWT_SECRET 已随机生成（非默认值）
- [x] Docker 镜像最新版已构建

### 开发前检查

- [x] 虚拟环境 Python 3.12+
- [x] `pip install git+https://github.com/langchain-ai/deepagents.git#subdirectory=libs/deepagents`
- [x] Alembic 迁移已执行
- [x] PostgreSQL + Redis 通过 Docker 运行
