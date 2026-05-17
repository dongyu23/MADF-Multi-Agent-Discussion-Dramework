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
| L. 业务审计 | orchestrator 统一埋点 → PostgreSQL `audit_events` 表，`GET /api/v1/discussions/{id}/audit` 查询接口 |
| M. Docker Compose 一键部署 | `docker-compose up` 启动全部服务（Nginx + FastAPI + PostgreSQL + Redis + React） |

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

多模块单体：FastAPI 单应用 + agent-engine 作为独立 Python package 逻辑解耦。

```
madf-new/
├── agent-engine/                    # 独立 Python package（逻辑解耦）
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
│   │   └── audit/                   # 审计模块
│   │       ├── router.py            # 审计查询接口
│   │       ├── service.py           # 统一事件记录
│   │       ├── repository.py        # 数据库操作（audit_events 表）
│   │       └── schemas.py
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
│   │   ├── auth.py                  # JWT 验证
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
├── docker-compose.yml
├── .env                             # 环境变量（LLM API key、Tavily key 等）
└── CLAUDE.md                        # 本文件
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

**关键文件**：
- `frontend/src/app/App.tsx` — QueryClient 配置
- `frontend/src/app/routes.tsx` — 路由级 `lazy()` 代码分割
- `frontend/src/app/components/Layout.tsx` — `<Suspense>` 包裹 `<Outlet />`
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

```
┌─────────┐     ┌──────────┐     ┌──────────────┐
│  Nginx  │────▶│ FastAPI  │────▶│  PostgreSQL  │
│  :80    │     │  :8000   │     │  :5432       │
└─────────┘     │          │     └──────────────┘
      │         │ agent-   │
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
| FastAPI | Docker 容器 | 路由、业务逻辑、orchestrator、SSE、agent-engine 同进程 | 无状态（数据在 PG + FS） |
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

### 核心实体关系（6 张表）

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
| 讨论域 | DiscussionAgent | 🟢 | 讨论参与者（discussion_id, skill_id, role_type） |
| 讨论域 | DiscussionMessage | 🔴 | 讨论消息（discussion_id, round_number, agent_id, agent_name, message_type, content, confidence） |
| 审计域 | AuditEvent | 🟡 | 业务审计事件（discussion_id, user_id, event_type, payload JSONB） |

---

## 九、数据库设计规范

### 通用字段（每张表必须有）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID v4（高写入表 discussion_messages 用 UUID v7） | 主键 |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | 创建时间，ORM 自动维护 |
| updated_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | 更新时间，ORM 自动维护（SQLAlchemy `onupdate=now()`），业务代码不手写 |
| deleted_at | TIMESTAMPTZ DEFAULT NULL | 软删除标记，所有查询默认带 `WHERE deleted_at IS NULL`，ORM 层统一拦截 |

### 核心规范

| 规范项 | 决策 | 说明 |
|-------|------|------|
| 主键策略 | UUID v4（discussion_messages 用 UUID v7） | UUID v7 时间有序，B-Tree 索引写入性能好 |
| NULL 处理 | 核心业务字段 NOT NULL + 默认值；可选字段（phone, confidence）允许 NULL | NULL 有语义价值——代表"未设置/不存在" |
| 枚举字段 | VARCHAR + CHECK 约束 | 比 ENUM 类型更易演进，新增枚举值不锁表 |
| 数据库外键 | 建 FOREIGN KEY | 单库场景数据一致性有保障 |
| 外键删除策略 | 讨论 → 消息 CASCADE；用户删角色 → RESTRICT（有讨论引用则禁止删）；用户删号 → 角色 CASCADE | — |
| 字符集 | UTF-8 | 建库时 `ENCODING 'UTF8'` |
| 金额/精度 | 不适用（系统无金额字段） | — |

### 索引规范

| 规范 | 决策 |
|------|------|
| 等值 + 排序复合索引列顺序 | 等值在前，排序/范围在后——`(discussion_id, created_at DESC)` |
| 软删除字段 | 用**部分索引** `WHERE deleted_at IS NULL`，不放进组合索引列 |
| 排序列 | 排序列必须进组合索引，和等值列一起构成完整覆盖 |
| 大文本字段（content, description） | **禁止建普通 B-Tree 索引**。全文搜索需求后续用 tsvector 或 Elasticsearch |
| 唯一约束 | 必须在数据库层（不靠应用层并发判断），软删除场景用部分唯一索引 `WHERE deleted_at IS NULL` |
| 多对多方向索引 | `discussion_agent` 表：`skill_id` 上建单独索引（支持"按角色查讨论"） |
| 单表索引数量 | 一期不设硬性上限，数据量上来后审计慢查询日志调优 |

### 核心索引清单

| 表 | 索引 | 覆盖查询 |
|----|------|---------|
| users | `UNIQUE (username) WHERE deleted_at IS NULL` | 注册查重 |
| users | `UNIQUE (phone) WHERE deleted_at IS NULL` | 手机号查重 |
| skills | `(owner_id, created_at) WHERE deleted_at IS NULL` | 用户角色列表 |
| skills | `(is_public, created_at) WHERE is_public = true AND deleted_at IS NULL` | 画廊公开角色 |
| skills | `UNIQUE (owner_id, name) WHERE deleted_at IS NULL` | 同一用户角色名不重复 |
| discussions | `(user_id, created_at) WHERE deleted_at IS NULL` | 用户讨论列表 |
| discussion_agents | `(discussion_id)` | 查讨论的参与角色 |
| discussion_agents | `(skill_id)` | 按角色查讨论 |
| discussion_messages | `(discussion_id, round_number, created_at) WHERE deleted_at IS NULL` | 讨论消息按轮次查（最高频查询） |
| audit_events | `(discussion_id, created_at) WHERE deleted_at IS NULL` | 审计事件查询 |

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
  GET    /api/v1/discussions/{id}/audit        # 审计事件查询
  GET    /api/v1/characters/recommendations    # 人物推荐（LLM 生成，排除已有角色）
  GET    /api/v1/discussions/generate-topic    # AI 生成讨论主题

SSE 端点:
  GET    /api/v1/discussions/{id}/stream       # 讨论实时流
  GET    /api/v1/characters/{id}/generation_progress  # 角色生成进度
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
- 服务：`AuditService.record(event_type, payload, discussion_id=None, user_id=None)`
- 接口：`GET /api/v1/discussions/{discussion_id}/audit`（支持 after、event_type 筛选）
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
- 规范没覆盖的情况：不自创规则，先问用户怎么处理，然后决定是否补充到 CLAUDE.md
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
| **当前** | — | 单进程 FastAPI + agent-engine 同进程 + Redis Pub/Sub + PG 单库 |
| **阶段 1** | 并发讨论 > 80 场 | gunicorn 多 worker + PgBouncer 连接池 |
| **阶段 2** | Agent 需独立部署 / 多租户隔离 | Agent Service 独立进程 + RabbitMQ 替代 Redis Pub/Sub |
| **阶段 3** | SaaS 多租户 | 按 tenant 分库 + 完整监控（Prometheus + Grafana） |

**核心原则**：触发条件不到，不提前演进。每个"暂不做"都标注触发条件，不是因为看不见，而是因为现在做了没收益。

---

## 十六、测试规范

### 核心链路（按风险优先级）

| # | 链路 | 风险类型 | 测试策略 |
|---|------|---------|---------|
| 1 | **讨论生命周期** (创建→orchestrator→发言→结束) | 并发、数据一致性、SSE 断线 | 集成测试，启动真实 PG+Redis |
| 2 | **Skill 生成管线** (deepagent + Tavily + LLM) | 外部依赖失败、超时、输出质量 | 已验证，LLM 端到端测试高成本 |
| 3 | **用户认证** (注册→登录→JWT→鉴权) | 安全、权限越权 | 集成测试，验证 401/403 正确返回 |
| 4 | **角色 CRUD + 文件系统** | 文件系统异常、路径穿越 | 集成测试 |
| 5 | **审计事件写入** | 静默失败、事件丢失 | 集成测试，验证事件落库 |

### 测试策略

| 层 | 策略 | 原因 |
|----|------|------|
| **API 集成测试** | 启动 FastAPI + PG + Redis，发真实 HTTP 请求 | 覆盖从 Router→Service→Repository→DB 完整链路 |
| **纯函数单测** | 不启动容器，直接测纯逻辑 | 仅用于数据转换、JSON 解析等无依赖代码 |
| **Orchestrator** | 已有 `tests/test_roundtable_agent.py` 和 `tests/test_discussion_e2e.py` | 验证 deepagent 加载 + 多 Agent 讨论 |

### 不写单测的范围

- **Service 层**：全部依赖异步 PG session 和外部 LLM API，mock 后只测假数据流转，用集成测试替代
- **Repository 层**：逻辑在 SQL（排序、索引），mock DB 后 SQL 不执行，用集成测试验证
- **deepagent 内部**：框架代码，由 deepagents 库自身测试覆盖

### 测试命名

```
test_should_[期望结果]_when_[条件]
```

### 已知风险点

1. `_run_orchestrator` 异常分支未验证——需确认崩溃场景审计事件落库
2. `agent_speak_chunk` 写入 `discussion_messages` 的数据归属需确认无重复
3. 并发讨论时 `_active_orchestrators` 字典无并发保护
4. SQL 查询全部依赖 ORM 自动生成，未手写 SQL——排序方向正确性需集成测试验证

---

## 十七、操作清单

### 当前状态

| 指标 | 值 |
|------|-----|
| API 端点 | 23 个 |
| 数据库表 | 6 张 |
| 审计事件 | 全模块 P0/P1/P2 |
| 集成测试 | 27/27 pass |
| 单元测试 | 96/96 pass |
| Docker 容器 | 4 个（backend + frontend + PG + Redis） |
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
