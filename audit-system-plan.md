# MADF 企业级管理后台 — 完整开发计划

## 一、产品定义

### 一句话定义
MADF 管理后台——企业级运维控制台，管理员在此监控系统健康、管理用户、旁听讨论、追溯变更、查看资源消耗。

### 7 个页面

| 页面 | 路由 | 内容 |
|------|------|------|
| 总览 | `/` | 异常数、在线人数、今日访问量、新注册数、各组件健康状态灯、token 消耗趋势图 |
| 用户管理 | `/users` | 用户列表(分页/搜索/排序)、用户详情(注册时间/最近活跃/token消耗/角色列表/参与讨论数)、禁用/启用、改用户名、改密码 |
| 讨论监控 | `/discussions` | 所有讨论列表(按状态/时间/创建者筛选)、进入 SSE 实时旁听、消息完整历史、讨论 token 消耗、删除讨论 |
| 审计与追溯 | `/audit` | 审计事件列表(按类型/用户/时间范围/操作对象筛选)、事件详情+关联上下文链、操作审计明细(角色生成/讨论创建：成功/失败、耗时、token) |
| 系统健康 | `/health` | 异常列表(500错误/LLM失败/DB断连/Redis断连)、异常详情(堆栈/时间/影响范围)、系统负载(CPU/内存/DB连接数/活跃讨论数/SSE连接数)、未正常结束的讨论列表 |
| 管理员管理 | `/admins` | 管理员账号列表、创建/编辑/删除管理员、角色分配（仅 superadmin 可见） |
| 设置 | `/settings` | 端口配置及自动重启、告警阈值、数据保留策略 |

### 核心架构原则
- **独立部署**：端口 81，独立 JWT 认证，独立登录页。管理后台 react app 是独立的前端项目（`audit-frontend/`），与主系统前端（`frontend/`）完全分离
- **只读隔离**：审计后端用 `madf_audit_ro` 连接主库，审计事件表只读。审计后端可写的表仅限 `audit_admin_users`、`audit_access_log`、`audit_retention_policy`、`audit_integrity_rules`
- **API 网关**：审计后端作为网关，所有管理操作经审计后端转发调主系统 API。审计后端 down 时管理后台不可用，但主系统不受影响（用户流量不经过审计后端）
- **服务间 JWT**：审计后端调用主系统 `/api/v1/admin/*` 时携带服务 JWT（HS256，独立 `ADMIN_JWT_SECRET`，5 分钟过期），payload 含 `jti` 防重放（主系统 Redis 缓存已用 jti，TTL 5 分钟）
- **改主系统数据走 API，不直接写库**

---

## 二、主系统管理 API（38 个接口）

所有接口前缀：`/api/v1/admin`，由 `backend/services/admin/` 模块集中管理。

认证方式：验证 `Authorization: Bearer <service-jwt>`（HS256，独立 `ADMIN_JWT_SECRET`，5 分钟过期）。
service-jwt payload：`{"sub": "audit-backend", "jti": "uuid", "admin_id": "uuid", "admin_username": "str", "role": "str", "exp": "timestamp"}`。

### 用户管理 (6)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/users` | 用户列表（分页、搜索、按注册时间/活跃时间/用户名排序） |
| GET | `/admin/users/{id}` | 用户详情（注册时间、最近活跃时间、token总消耗、拥有的角色列表、参与的讨论数） |
| PUT | `/admin/users/{id}/status` | 禁用/启用用户 → 记审计 `user.status_changed` |
| PUT | `/admin/users/{id}/username` | 修改用户名 → 记审计 `user.username_changed` |
| PUT | `/admin/users/{id}/password` | 重置密码（随机生成或指定）→ 记审计 `user.password_reset` |
| GET | `/admin/users/{id}/token-usage` | 单个用户 token 消耗明细（按讨论/按角色生成/按其他） |

### 讨论监控 (6)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/discussions` | 所有讨论列表（分页、按状态/时间/创建者/关键词筛选） |
| GET | `/admin/discussions/{id}` | 讨论详情（参与Agent、总轮数、状态、创建者、开始/结束时间） |
| GET | `/admin/discussions/{id}/stream` | SSE 实时旁听。不走用户身份验证，由服务 JWT 鉴权。管理员通过审计后端代理连接，代理在请求头注入服务 JWT |
| GET | `/admin/discussions/{id}/messages` | 完整消息历史（按轮次排序，含 agent_think 的 decision/confidence） |
| DELETE | `/admin/discussions/{id}` | 软删除讨论 → 记审计 `discussion.deleted_by_admin` |
| GET | `/admin/discussions/{id}/token-usage` | 单场讨论 token 消耗明细 |

### 角色管理 (4)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/characters` | 全量角色列表（跨用户，分页、按名称/创建者/状态/公开性筛选） |
| GET | `/admin/characters/{id}` | 角色详情（Skill 文件清单、生成记录：耗时/token/成功失败/时间） |
| PUT | `/admin/characters/{id}/visibility` | 强制设公开/私有 → 记审计 `character.visibility_changed` |
| DELETE | `/admin/characters/{id}` | 管理员强制软删除角色 → 记审计 `character.deleted_by_admin` |

### 画廊管理 (2)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/gallery` | 全量公开角色列表（分页、搜索） |
| DELETE | `/admin/gallery/{id}` | 管理员强制下架（设 is_public=false）→ 记审计 `gallery.unlisted` |

### 审计与追溯 (4)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/audit/events` | 审计事件列表（按event_type/user_id/discussion_id/level/时间范围筛选，游标分页） |
| GET | `/admin/audit/events/{id}` | 事件详情（完整payload + 同一discussion_id的关联事件链） |
| GET | `/admin/audit/operations` | 操作审计明细——角色生成记录 + 讨论创建记录（成功/失败、耗时ms、token数、发起人） |
| GET | `/admin/audit/operations/{id}` | 单条操作审计详情 |

### 系统健康 (5)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/health/overview` | 健康概览（DB状态/Redis状态/LLM API可达性/SSE连接状态） |
| GET | `/admin/health/errors` | 异常列表（错误类型、时间、影响范围、堆栈摘要，分页） |
| GET | `/admin/health/errors/{id}` | 异常详情（完整堆栈、请求上下文、发生时间、是否已恢复） |
| GET | `/admin/health/load` | 系统负载（CPU使用率/内存使用率/DB活跃连接数/活跃讨论数/SSE连接数） |
| GET | `/admin/health/orphan-discussions` | 未正常结束的讨论（discussion.create 有但无 discussion_end，超过时长阈值） |

### 统计总览 (3)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/stats/overview` | 总览（异常总数、在线人数、今日访问量、今日新注册、活跃讨论数） |
| GET | `/admin/stats/tokens` | Token 消耗统计（按讨论/按角色生成/按其他的分类汇总，支持时间范围） |
| GET | `/admin/stats/tokens/trend` | Token 消耗趋势（按小时聚合，默认近7天） |

### 管理员管理 (4)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/admins` | 管理员账号列表 |
| POST | `/admin/admins` | 创建管理员（用户名+密码+角色） |
| PUT | `/admin/admins/{id}` | 更新管理员（角色/状态） |
| DELETE | `/admin/admins/{id}` | 删除管理员（软删除） |

### 设置 (4)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/settings` | 当前配置（主系统端口、审计端口、审计JWT过期时间、告警阈值） |
| PUT | `/admin/settings` | 更新配置（写入 DB + 返回重启状态） |
| POST | `/admin/settings/restart` | 触发容器重启（详见 4.4 节重启流程） |
| PUT | `/admin/settings/retention` | 更新数据保留策略（按 P0/P1/P2 三级分别设置 hot_days/warm_days） |

---

## 三、主系统异常记录改造

### P0 — 不改则管理后台大屏永远看不到的异常

#### 3.1 HTTP 500 审计记录
**文件**：`backend/core/exception_handlers.py`
**改动**：在泛型 Exception 处理器中，调用 `AuditRepository.record("system.error")`，payload 含：
- `request_path`、`request_method`
- `traceback_summary`（最后 3 帧）
- `level: "P0"`
**注意**：异常处理器可能拿不到 DB session。使用独立 async session 写入，若 DB 也不可达则降级到 Redis publish + 异步落库

#### 3.2 Redis Pub/Sub 失败记录
**文件**：`backend/services/audit/repository.py`
**改动**：当前 `except Exception: pass` 改为 `logger.warning()` + 尝试直接写 PG `system.redis_pubsub_error` 事件

#### 3.3 Agent think / speak / host 超时保护
**文件**：`agent_engine/discussion/orchestrator.py`
**改动**：三个核心 LLM 调用点全部加超时：
- `_agent_think_fast`：`asyncio.wait_for(timeout=15)`，超时记录 `agent.think_timeout` 并降级为 `wait`
- `_agent_speak_stream`：`asyncio.wait_for(timeout=60)`，超时记录 `agent.speak_timeout` 并跳过本轮发言
- `_call_host_llm_stream`：`asyncio.wait_for(timeout=60)`，超时记录 `host.llm_timeout` 并降级为短摘要

单个超时不拖垮整轮讨论

### P1 — 业务级异常记录

#### 3.4 DB 连接池监听
**文件**：`backend/deps.py`
**改动**：给 async engine 注册 `handle_error` 事件监听，连接池溢出/连接失败时记录 `system.db_pool_error` 审计事件

#### 3.5 LLM 推荐失败保留原始错误
**文件**：`backend/services/character/service.py`
**改动**：`get_recommendations` 中 `except Exception` 把原始异常的 type 和 message 写入 audit payload

#### 3.6 健康检查加深（新增独立端点）
**文件**：`backend/main.py`
**改动**：新增 `GET /api/v1/health/detailed` 端点，检查 DB（`SELECT 1`）、Redis（`PING`）、LLM API 可达性。
保持现有 `/api/v1/health` 不变（轻量存活检查，返回 200 即可），Docker healthcheck 继续用原有端点

#### 3.7 审计事件统一 level
**文件**：所有调用 `AuditRepository.record()` 的地方 + `AuditRepository.record()` 方法本身
**改动**：
- `AuditEvent` ORM 模型的 `level` 字段已作为独立列存在（migration `7883e7a9b2c1` 中添加），数据库存储使用独立列而非 JSONB 路径
- `AuditRepository.record()` 增加 `level` 参数，默认 `"P2"`。调用方显式传入正确的 level
- 映射规则（严格对齐 CLAUDE.md 第十二节）：

| 事件 | level | 依据 |
|------|------|------|
| user.login | P0 | CLAUDE.md: 安全事件 |
| user.login_failed | P0 | CLAUDE.md: 安全事件 |
| user.register | P1 | CLAUDE.md: 数据变更 |
| user.status_changed（新增） | P0 | 安全事件 |
| user.username_changed（新增） | P0 | 安全事件 |
| user.password_reset（新增） | P0 | 安全事件 |
| skill.generate | P0 | CLAUDE.md: 资源消耗（LLM调用） |
| skill.generate_complete | P1 | CLAUDE.md: 生命周期事件 |
| skill.generate_error | P1 | CLAUDE.md: 生命周期事件 |
| skill.create | P2 | CLAUDE.md: 数据修改 |
| skill.update | P2 | CLAUDE.md: 数据修改 |
| skill.delete | P1 | CLAUDE.md: 数据变更 |
| skill.copy | P1 | CLAUDE.md: 跨用户操作 |
| skill.file_write | P2 | CLAUDE.md: 数据修改 |
| skill.visibility_changed（新增） | P1 | 跨用户影响 |
| character.deleted_by_admin（新增） | P1 | 数据变更 |
| discussion.create | P1 | CLAUDE.md: 生命周期事件 |
| discussion.error | P1 | CLAUDE.md: 生命周期事件 |
| discussion.deleted_by_admin（新增） | P1 | 数据变更 |
| discussion_end | — | 通过 orchestrator event handler 自动进入，不单独标注 |
| gallery.unlisted（新增） | P1 | 内容管理 |
| host_intro / host_summary / agent_speak_chunk | — | 高频运行时事件，归属 discussion_messages 表，不进入 audit_events |
| system.error（新增） | P0 | 基础设施异常 |
| system.db_pool_error（新增） | P0 | 基础设施异常 |
| system.redis_pubsub_error（新增） | P1 | 基础设施降级 |
| system.restart_triggered（新增） | P0 | 安全事件 |

**回填迁移**：
```sql
-- 已有事件默认 P2
UPDATE audit_events SET level = 'P2';
-- P0 事件
UPDATE audit_events SET level = 'P0' WHERE event_type IN (
    'user.login', 'user.login_failed', 'skill.generate'
);
-- P1 事件
UPDATE audit_events SET level = 'P1' WHERE event_type IN (
    'user.register', 'skill.generate_complete', 'skill.generate_error',
    'skill.delete', 'skill.copy', 'discussion.create', 'discussion.error'
);
```

---

## 四、审计后端改造

### 4.1 服务间 JWT 签发
**新文件**：`audit_backend/services/admin_gateway.py`
**功能**：管理员操作需要调主系统 `/api/v1/admin/*` 时，签发短时效服务 JWT
- `sub: "audit-backend"`
- `jti: uuid4()` — 防重放 ID
- `admin_id`、`admin_username`、`role`（从当前登录的管理员 session 提取）
- `exp: now + 5min`
- 签名密钥：`ADMIN_JWT_SECRET`（与 `AUDIT_JWT_SECRET` 分开）

**主系统验证**：`backend/middleware/admin_auth.py`
- 验 JWT 签名
- 检查 `jti` 是否已在 Redis 中出现过（`SET jti 1 EX 300 NX`），防止 5 分钟窗口内重放
- 提取 `admin_id` 作为操作人

### 4.2 代理路由
**新文件**：`audit_backend/services/admin_proxy/router.py`
**功能**：所有 `/api/v1/admin/*` 请求 → 签发服务 JWT → httpx 转发到主系统 `http://backend:8000/api/v1/admin/*` → 返回结果

### 4.3 自审计
**文件**：`audit_backend/middleware/access_log.py`
**改动**：已有自审计记录每次 API 访问。补充 `admin_username` 字段。
管理员的所有操作（查询、修改、导出、重启）均写入 `audit_access_log`，管理员 CRUD 操作本身也被审计。

### 4.4 容器重启机制
**场景**：管理员在"设置"页面修改端口配置后点击"应用并重启"

**流程**：
1. 审计前端发送 `PUT /admin/settings` 保存配置
2. 弹出确认对话框：显示变更内容、警告"重启期间服务约 10 秒不可用"、当前活跃讨论数（若 > 0 则额外警告）
3. 管理员确认 → 前端调 `POST /admin/settings/restart`
4. 审计后端记录 `system.restart_triggered` 审计事件（含 `admin_id`、`config_diff`）
5. 审计后端调用 Docker API（通过挂载 `/var/run/docker.sock`）执行 `POST /containers/{name}/restart`
6. 前端显示倒计时（预计 10 秒）+ 轮询健康检查直到服务恢复
7. 重启成功 → 前端提示"重启完成"；重启失败 → 前端提示"重启失败，请手动检查"

**安全约束**：
- 仅 superadmin 可触发重启
- 每次重启记审计事件
- 重启前自动创建配置快照（写入 `admin_actions` 表），失败时可回滚

---

## 五、数据库变更

### 5.1 审计事件 level 回填
使用 3.7 节的回填 SQL。`level` 是 `audit_events` 表的独立列（在 Alembic 迁移 `7883e7a9b2c1` 中已添加），不再依赖 JSONB 路径提取。

### 5.2 新增表
- `admin_actions`：管理后台操作记录（admin_id、action_type、target_type、target_id、config_diff JSONB、created_at）
- `system_health_events`：系统健康事件（event_type、component、status、detail、created_at）

### 5.3 已有表
- `audit_admin_users`、`audit_access_log`、`audit_retention_policy`、`audit_integrity_rules` — 已创建，无需变更

---

## 六、前端页面设计

### 6.1 页面结构与路由

```
/ → 总览                    (Dashboard)
/users → 用户管理           (UserManagement)
/users/:id → 用户详情       (UserDetail)
/discussions → 讨论监控     (DiscussionMonitor)
/discussions/:id → 讨论旁听  (DiscussionWatch)
/audit → 审计与追溯         (AuditTrail)
/audit/:id → 事件详情       (AuditEventDetail)
/health → 系统健康          (SystemHealth)
/settings → 设置            (Settings)
/login → 管理员登录          (AdminLogin)
```

### 6.2 各页面布局

**总览**：顶部 5 个统计卡片（异常数/P0数/在线人数/今日访问/新注册）→ 中间系统健康状态灯（DB/Redis/LLM/SSE/Orchestrator 5 个组件，绿色正常/黄色降级/红色故障）→ 下方 token 消耗趋势折线图（近 7 天）+ 最近异常列表（最新 5 条 P0 事件）→ 每个卡片/图表点击跳转对应详情页

**用户管理**：顶部搜索栏（用户名/注册时间范围）→ 用户表格（用户名/注册时间/最近活跃/角色数/讨论数/token消耗/状态）→ 每行操作按钮（查看详情/禁用/重置密码/改用户名）→ 分页

**用户详情**：用户基本信息卡片 + 该用户拥有的角色列表（可点击跳转角色详情）+ token 消耗按分类饼图 + 最近操作审计记录（该用户相关的事件时间线）

**讨论监控**：顶部筛选栏（状态/时间范围/创建者）→ 讨论表格（主题/创建者/参与Agent/轮数/状态/token消耗/开始时间）→ 每行操作（进入旁听/查看详情/删除）→ 分页

**讨论旁听**：顶部讨论信息栏（主题/Agent/状态）→ 主体区域：SSE 实时消息流（左侧消息列表类似聊天界面，右侧可折叠的侧栏显示每个 Agent 的 think 数据：decision/confidence）→ 底部：本轮信息（第几轮/当前发言人）

**审计与追溯**：顶部筛选栏（事件类型多选/用户/时间范围/操作对象搜索）→ 下方时间线视图（左侧时间轴，右侧事件卡片：图标+事件类型+操作摘要+Payload可展开）→ 加载更多

**事件详情**：完整 JSON payload（语法高亮）+ 关联事件链（同一 discussion_id 的相关事件时间线）

**系统健康**：顶部组件状态卡片（DB/Redis/LLM/SSE，含上次检测时间和延迟ms）→ 中间异常列表（错误类型/时间/影响范围/是否已恢复，可展开看堆栈）→ 右侧系统负载仪表（CPU/内存/连接数/活跃讨论数，进度条或仪表盘样式）

**设置**：左侧 tab 导航（端口配置/告警阈值/管理员账号/保留策略）→ 右侧对应表单。端口配置页含"应用并重启"按钮 + 重启确认对话框（显示影响范围 + 倒计时）

**登录页**：独立于主系统，暗色主题。MADF 审计系统 logo + 用户名/密码输入 + 登录按钮

### 6.3 全局 UI 规范
- **主题**：暗色（slate-900 底 + emerald-500 强调色），独立于主系统的浅色主题
- **导航**：左侧侧边栏（6 个页面入口 + 底部管理员信息/退出）
- **实时数据**：总览页和系统健康页通过 SSE 订阅 `audit:events` 实时更新数字
- **部署**：`audit-frontend/` 是独立 React 项目（独立 `package.json`、`vite.config.ts`），构建产物由独立 Nginx 容器托管（端口 81），与主系统前端完全隔离

---

## 七、实施阶段

### Phase 1：主系统异常记录 + level 统一
**改动清单**：
1. `exception_handlers.py`：500 审计记录（`system.error`）
2. `audit/repository.py`：Redis publish 失败记 `system.redis_pubsub_error`
3. `orchestrator.py`：Agent think/speak/host 三个 LLM 调用点超时保护
4. `deps.py`：DB 连接池事件监听（`system.db_pool_error`）
5. `main.py`：新增 `/health/detailed` 端点
6. `character/service.py`：LLM 推荐异常信息保留
7. **全部审计调用点加 level 参数** + `AuditRepository.record()` 加 `level` 参数（默认 P2）
8. 数据库回填迁移（已有事件的 level 修正）

**验证**：触发各类异常 → 检查审计事件正确记录 level → `/admin/audit/events?level=P0` 可查询到

### Phase 2：主系统管理 API（36 个接口）
1. `backend/services/admin/` 模块搭建（router + service + repository + schemas）
2. `backend/middleware/admin_auth.py`：服务 JWT 验证 + jti 防重放
3. 用户管理（6）+ 讨论管理（6）+ 角色管理（4）+ 画廊管理（2）
4. 审计与追溯（4）+ 系统健康（5）+ 统计（3）+ 设置（8）

**验证**：逐一调所有接口 → 确认数据正确 → 确认管理操作在主系统生效

### Phase 3：审计后端代理网关
1. 服务 JWT 签发（`admin_gateway.py`，含 jti）
2. 代理路由（`admin_proxy/router.py`）
3. 自审计中间件增强 + 容器重启机制（Docker API）

**验证**：审计后端登录 → 调管理 API → 主系统正确执行 → 审计记录含 admin_id

### Phase 4：前端 6 页面
1. 总览（含实时 SSE）
2. 用户管理 + 用户详情
3. 讨论监控 + 讨论旁听（SSE 集成）
4. 审计与追溯 + 事件详情
5. 系统健康
6. 设置（含重启确认流程）+ 管理员登录页

**验证**：浏览器端到端测试每个页面

### Phase 5：测试 & 文档 & CLAUDE.md 同步
1. 管理 API 集成测试（pytest + httpx）
2. 审计后端代理测试
3. 前端组件测试（vitest）
4. 端到端验证（Playwright）
5. CLAUDE.md 更新：补充审计系统完整架构、管理 API 规范、level 映射表

---

## 八、关键风险

| 风险 | 缓解 |
|------|------|
| 主系统异常处理器拿不到 DB session | 独立 async session 写入；DB 不可达时降级到 Redis publish |
| 审计事件 level 回填可能遗漏 | 迁移脚本先备份 `audit_events` 表，迁移后可验证 P0/P1 计数 |
| 服务 JWT secret 泄露 | 5 分钟短过期 + jti 防重放 + 独立 secret |
| Agent 超时保护影响讨论体验 | think 超时降级为 wait，speak/host 超时降级为短摘要，不中断讨论 |
| 容器重启中断活跃讨论 | 重启前警告活跃讨论数；管理员在低峰时段操作；重启前自动记配置快照可回滚 |
| 管理后台 down 不影响主系统 | 用户流量不经过审计后端，正向链路独立 |
