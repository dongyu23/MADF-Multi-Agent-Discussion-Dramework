# MADF 工程搭建排期规划

## 一、项目基本信息

| 项目 | 内容 |
|------|------|
| 项目名称 | MADF — Multi-Agent Discussion Framework |
| 后端技术栈 | FastAPI + Python 3.12 + SQLAlchemy + Alembic |
| 前端技术栈 | Vue 3 + Vite + Monaco Editor |
| 数据库 | PostgreSQL 16 |
| 缓存/消息 | Redis 7 |
| Agent 框架 | deepagents（GitHub 安装，非 PyPI） |
| 构建系统 | pip + pyproject.toml（后端），npm + vite（前端） |
| 是否全栈 | 是 |
| 部署方式 | Docker Compose |
| CLAUDE.md | 项目根目录，约 600 行 |

## 二、模块依赖关系图

从 CLAUDE.md 第四章提取：

```
backend/core/        # 公共基础设施
  ├── 被 services/* 所有模块依赖
  └── 无内部依赖

backend/models/      # ORM 实体
  ├── 被 services/*/repository.py 依赖
  └── 依赖 core/base.py (BaseMixin)

agent-engine/        # Agent 引擎 package
  ├── 被 backend/services/discussion/ 调用
  ├── 被 backend/services/character/ 调用
  └── 无内部依赖

backend/services/user/      # 用户模块
  └── 依赖 core/, models/

backend/services/character/ # 角色模块
  ├── 依赖 core/, models/
  └── 依赖 agent-engine/skill_gen/

backend/services/discussion/# 讨论模块
  ├── 依赖 core/, models/
  ├── 依赖 agent-engine/discussion/
  └── 依赖 services/character/, services/realtime/, services/audit/

backend/services/realtime/  # 实时通信模块
  ├── 依赖 core/, models/
  └── 被 discussion 依赖

backend/services/audit/     # 审计模块
  ├── 依赖 core/, models/
  └── 被所有模块调用

backend/main.py             # 应用入口
  └── 依赖所有 services/*, core/, middleware/
```

依赖关系检查：
- ✅ 无循环依赖
- ✅ `core/` → `models/` → `services/*/` → `main.py` 严格单向
- ✅ `agent-engine/` 独立，仅被 services 调用

## 三、依赖层次分析

### 第 0 层：项目配置文件（非代码地基）

- 内容：`pyproject.toml`、`requirements.txt`、`.env.template`、虚拟环境确认
- 为什么是第 0 层：Python 项目没有"编译"步骤，但依赖声明和虚拟环境是所有后续代码的基础
- 包含任务：
  - T0.1：确认虚拟环境 + 创建 pyproject.toml
  - T0.2：安装核心依赖（FastAPI, SQLAlchemy, Alembic, deepagents 等）

### 第 1 层：后端核心基础设施（所有模块的共同依赖）

- 内容：统一响应 `Result[T]`、错误码、全局异常处理、基础实体 `BaseMixin`、配置管理、JWT 中间件
- 为什么是第 1 层：所有 services 模块都依赖这些
- 包含任务：
  - T1.1：创建 `backend/core/`（Result, ErrorCode, BusinessException, exception_handlers）
  - T1.2：创建 `backend/config.py` + `backend/deps.py`（Settings, get_db, get_current_user）
  - T1.3：创建 `backend/models/base.py`（BaseMixin: id UUID v4, created_at, updated_at, deleted_at）
  - T1.4：创建 `backend/middleware/`（JWT auth, CORS）
  - T1.5：创建全部 6 个 ORM 实体（User, Skill, Discussion, DiscussionAgent, DiscussionMessage, AuditEvent）

### 第 2 层：业务模块目录骨架

- 内容：每个 service 模块的目录结构和 `__init__.py` 占位
- 为什么是第 2 层：模块需要引用第 1 层的 core/models，必须等它们就位
- 包含任务：
  - T2.1：创建 `backend/services/user/` 骨架
  - T2.2：创建 `backend/services/character/` 骨架
  - T2.3：创建 `backend/services/discussion/` 骨架
  - T2.4：创建 `backend/services/realtime/` 骨架
  - T2.5：创建 `backend/services/audit/` 骨架

### 第 3 层：应用入口

- 内容：`main.py`、路由注册、健康检查端点、Alembic 迁移
- 为什么是第 3 层：应用入口需要引用所有 services 模块
- 包含任务：
  - T3.1：创建 `backend/main.py`（FastAPI 应用 + 路由注册 + 生命周期）
  - T3.2：创建健康检查端点 `GET /api/v1/health`
  - T3.3：配置 Alembic + 生成初始迁移 + 执行迁移
  - T3.4：后端启动验收

### 第 4 层：agent-engine 基础骨架

- 内容：agent-engine package 的目录结构、Skill 文件缓存接口
- 为什么是第 4 层：agent-engine 独立于 backend，但需要 backend/core 先就位（共享 Result 类型）
- 包含任务：
  - T4.1：创建 `agent-engine/` package 骨架
  - T4.2：创建 `agent-engine/discussion/` 骨架 + `SkillFileCache` 抽象类
  - T4.3：移植 nuwa-source → `agent-engine/skill_gen/`

### 第 5 层：前端工程

- 内容：Vite + Vue 3 脚手架、HTTP 客户端、路由、布局、公共组件
- 为什么是第 5 层：前端需要后端健康检查就位才能做联通验证
- 包含任务：
  - T5.1：Vite + Vue 3 脚手架初始化 + 依赖安装
  - T5.2：配置 Vite 开发代理（→ `http://localhost:8000`）
  - T5.3：封装 HTTP 客户端（自动解包 Result[T]、错误拦截）
  - T5.4：创建路由配置 + 页面空壳（Login, Home, Characters, Discussions）
  - T5.5：创建布局框架（侧边栏 + 顶栏 + 内容区）
  - T5.6：前后端联通验证（前端调 `/api/v1/health`）
  - T5.7：创建前端公共组件（通用表格、表单弹窗、确认对话框）

### 第 6 层：Docker Compose + 数据库初始数据

- 内容：docker-compose.yml、PostgreSQL 初始化 SQL、Redis 配置
- 为什么是第 6 层：需要后端能启动后才验证 Docker 部署
- 包含任务：
  - T6.1：创建 `docker-compose.yml`（FastAPI + PostgreSQL + Redis + Nginx + Vue）
  - T6.2：创建 PostgreSQL 初始化脚本
  - T6.3：创建后端 Dockerfile
  - T6.4：创建前端 Dockerfile + Nginx 配置（含 SSE 缓冲关闭）
  - T6.5：Docker Compose 启动 + 全链路验收

### 第 7 层：收尾

- 内容：启动脚本、停止脚本
- 包含任务：
  - T7.1：创建 `start.sh`（一键启动全部）
  - T7.2：创建 `stop.sh`（一键停止全部）

## 四、详细任务排期表

### T0.1：确认虚拟环境 + 创建 pyproject.toml

| 字段 | 内容 |
|------|------|
| 任务 ID | T0.1 |
| 任务名称 | 确认虚拟环境 + 创建项目构建配置 |
| 所属层次 | 第 0 层 |
| 前置任务 | 无 |
| 产出文件 | `pyproject.toml` |
| 文件数预估 | 1 个文件 |
| 做什么 | 1. 确认 Python 3.12 虚拟环境可用<br>2. 创建 `pyproject.toml`：声明项目元信息、Python 版本要求、依赖列表 |
| 不做什么 | 不安装依赖（T0.2）、不写代码 |
| 验收标准 | `pyproject.toml` 存在，TOML 语法正确 |
| 拆解依据 | 虚拟环境在 Phase 0 已验证。pyproject.toml 是 Python 项目的入口，被 pip 使用 |
| 风险 | 低——纯声明性文件 |

### T0.2：安装核心依赖

| 字段 | 内容 |
|------|------|
| 任务 ID | T0.2 |
| 任务名称 | 安装后端核心依赖 |
| 所属层次 | 第 0 层 |
| 前置任务 | T0.1 |
| 产出文件 | `venv/lib/` 下的已安装包 |
| 文件数预估 | 无代码文件——纯 pip install |
| 做什么 | 安装: fastapi, uvicorn, sqlalchemy, asyncpg, alembic, pydantic, pydantic-settings, python-jose, passlib, redis, httpx, aiofiles, deepagents (从 GitHub) |
| 不做什么 | 不安装前端依赖（第 5 层） |
| 验收标准 | `pip list` 显示所有依赖已安装，`python -c "import fastapi; import deepagents"` 无报错 |
| 拆解依据 | 必须等 pyproject.toml 就位（声明了依赖）。所有后续代码都依赖这些包 |
| 风险 | deepagents 需要从 GitHub 安装（非 PyPI），可能因网络问题失败 |

### T1.1：创建 backend/core/ 公共基础设施

| 字段 | 内容 |
|------|------|
| 任务 ID | T1.1 |
| 任务名称 | 创建统一响应、错误码、异常处理 |
| 所属层次 | 第 1 层 |
| 前置任务 | T0.2 |
| 产出文件 | `backend/core/__init__.py`, `responses.py`, `exceptions.py`, `exception_handlers.py` |
| 文件数预估 | 4 个文件 |
| 做什么 | 1. `responses.py`：`Result[T]` 泛型类（code, message, data）、`PageResult[T]`（items, total, page, page_size, has_more）、工厂方法 `ok()`/`fail()`<br>2. `exceptions.py`：`ErrorCode` 枚举（按分段: 1000-5999）、`BusinessException(ErrorCode)` <br>3. `exception_handlers.py`：FastAPI exception_handler 注册函数 |
| 不做什么 | 不创建业务模块特有的错误码、不做 ORM 实体、不写中间件 |
| 验收标准 | `python -c "from backend.core.responses import Result; print(Result.ok('test'))"` 正常执行 |
| 拆解依据 | 被所有模块依赖，必须先创建。统一响应和错误码高度耦合，合并一步 |
| 风险 | AI 可能硬编码错误码数值——review 时重点检查 |

### T1.2：创建配置和依赖注入

| 字段 | 内容 |
|------|------|
| 任务 ID | T1.2 |
| 任务名称 | 创建配置管理 + 依赖注入 |
| 所属层次 | 第 1 层 |
| 前置任务 | T1.1 |
| 产出文件 | `backend/config.py`, `backend/deps.py`, `.env.template` |
| 文件数预估 | 3 个文件 |
| 做什么 | 1. `config.py`：pydantic-settings `Settings` 类（DB_URL, REDIS_URL, JWT_SECRET, LLM_API_KEY, TAVILY_API_KEY, CORS_ORIGINS）<br>2. `deps.py`：`get_db()` 异步 SQLAlchemy session、`get_current_user()` JWT 解码 |
| 不做什么 | 不写实际的路由、不初始化数据库连接池（第 3 层做） |
| 验收标准 | `python -c "from backend.config import Settings; s = Settings()"` 正常执行 |
| 拆解依据 | 配置是连接基础设施和业务代码的桥梁。T1.1 定了"返回什么格式"，T1.2 定"从哪读取运行参数" |
| 风险 | 低——纯配置代码 |

### T1.3：创建 ORM 基础实体

| 字段 | 内容 |
|------|------|
| 任务 ID | T1.3 |
| 任务名称 | 创建 BaseMixin + 全部 6 个 ORM 实体 |
| 所属层次 | 第 1 层 |
| 前置任务 | T1.2 |
| 产出文件 | `backend/models/__init__.py`, `base.py`, `user.py`, `skill.py`, `discussion.py`, `discussion_agent.py`, `discussion_message.py`, `audit_event.py` |
| 文件数预估 | 8 个文件 |
| 做什么 | 1. `base.py`：`BaseMixin`（id UUID v4, created_at, updated_at, deleted_at），ORM 自动维护时间字段<br>2. 按 CLAUDE.md 第八章创建全部 6 个实体：字段、类型、CHECK 约束、ForeignKey、索引 |
| 不做什么 | 不创建 Alembic 迁移文件（T3.3）、不写 repository 代码 |
| 验收标准 | `python -c "from backend.models import User, Skill, Discussion"` 无报错 |
| 拆解依据 | ORM 实体是数据层核心，被所有 repository 依赖。合并为一个任务避免后续需要"补充遗漏字段" |
| 风险 | 索引/约束漏写——对照 CLAUDE.md 第九章逐条检查 |

### T1.4：创建中间件

| 字段 | 内容 |
|------|------|
| 任务 ID | T1.4 |
| 任务名称 | 创建 JWT 认证 + CORS 中间件 |
| 所属层次 | 第 1 层 |
| 前置任务 | T1.2 |
| 产出文件 | `backend/middleware/__init__.py`, `auth.py`, `cors.py` |
| 文件数预估 | 3 个文件 |
| 做什么 | 1. `auth.py`：JWT 验证依赖（从 Authorization header 解 token → 查 user → 注入 request.state）<br>2. `cors.py`：CORS 中间件配置 |
| 不做什么 | 不做权限/角色校验（RBAC 属于业务层） |
| 验收标准 | `python -c "from backend.middleware.auth import get_current_user"` 无报错 |
| 拆解依据 | 中间件在 Router 之前执行，是安全基础设施 |
| 风险 | 低 |

### T2.1-T2.5：创建 5 个业务模块骨架

| 字段 | 内容 |
|------|------|
| 任务 ID | T2.1-T2.5（合并阐述，执行时逐个做） |
| 任务名称 | 创建 user/character/discussion/realtime/audit 模块骨架 |
| 所属层次 | 第 2 层 |
| 前置任务 | T1.4（core + models + middleware 全部就位） |
| 产出文件 | 每个模块 4 个占位文件：`__init__.py`, `router.py`, `service.py`, `repository.py`, `schemas.py`（共 25 个文件） |
| 文件数预估 | 每个模块 5 个文件 × 5 = 25 个文件 |
| 做什么 | 为每个 service 创建目录结构 + 占位文件（空类/函数签名） |
| 不做什么 | 不实现业务逻辑、不写 SQL、不创建 API 端点 |
| 验收标准 | `python -c "from backend.services.user.router import router"` 等全部无报错 |
| 拆解依据 | 所有业务模块同属一个依赖层（都只依赖 core/models），可以连续执行。但每个模块单独一步方便 review |
| 风险 | 低——空壳代码 |

### T3.1-T3.4：应用入口 + 启动验收

| 字段 | 内容 |
|------|------|
| 任务 ID | T3.1-T3.4 |
| 任务名称 | 创建 main.py + 路由注册 + 健康检查 + Alembic + 启动 |
| 所属层次 | 第 3 层 |
| 前置任务 | T2.5（所有业务模块骨架就位） |
| 产出文件 | `backend/main.py`, `backend/alembic/`, `alembic.ini` |
| 文件数预估 | 5-8 个文件 |
| 做什么 | 1. `main.py`：FastAPI 应用实例 + 注册所有 router + lifespan 事件（startup: 初始化 DB 连接池；shutdown: 关闭）<br>2. 健康检查 `GET /api/v1/health` → `Result.ok("MADF is running")`<br>3. Alembic 初始化 + 生成迁移 |
| 不做什么 | 不实现任何业务接口 |
| 验收标准 | `uvicorn backend.main:app --port 8000` → `curl http://localhost:8000/api/v1/health` 返回 `{"code":200,"message":"success","data":"MADF is running"}` |
| 拆解依据 | 应用入口依赖所有 module 的 router 已创建。健康检查是"系统能跑"的最小验证 |
| 风险 | 端口 8000 被占用 - Phase 0 已确认空闲；Alembic 迁移生成可能因模型定义问题失败 |

### T4.1-T4.3：agent-engine 骨架 + nuwa-source 移植

| 字段 | 内容 |
|------|------|
| 任务 ID | T4.1-T4.3 |
| 任务名称 | 创建 agent-engine package + 移植 nuwa-source |
| 所属层次 | 第 4 层 |
| 前置任务 | T3.4（后端启动验证通过） |
| 产出文件 | `agent-engine/` 整个 package |
| 文件数预估 | 15+ 个文件（nuwa-source 已有代码移植） |
| 做什么 | 1. 创建 `agent-engine/` package 骨架<br>2. 创建 `agent-engine/discussion/` 目录 + `SkillFileCache` 抽象类<br>3. 移植 `nuwa-source/nvwa_agent/` → `agent-engine/skill_gen/`<br>4. 移植 `nuwa-source/nuwa-agent-skill/` → `agent-engine/skill_gen/nuwa-skill/` |
| 不做什么 | 不实现讨论编排逻辑（orchestrator）、不实现 Skill 生成 API 对接 |
| 验收标准 | `python -c "from agent_engine.skill_gen.agent import create_nvwa_agent"` 无报错 |
| 拆解依据 | agent-engine 独立于 backend。移植现有代码而非重写 |
| 风险 | nuwa-source 代码可能引用了绝对路径——需要适配新目录结构 |

### T5.1-T5.7：前端工程（占位——本排期文档聚焦后端）

前端 7 个任务在后端完全稳定后执行，此处简要列出：

| ID | 任务 | 产出 | 验收 |
|----|------|------|------|
| T5.1 | Vite + Vue 3 脚手架 | `frontend/` 目录，`package.json` | `npm run dev` 启动成功 |
| T5.2 | Vite 开发代理配置 | `vite.config.ts` 代理到 `localhost:8000` | 前端 `/api/v1/health` 不走跨域 |
| T5.3 | HTTP 客户端封装 | `src/api/client.ts` | 自动解包 Result[T]、错误拦截 |
| T5.4 | 路由 + 页面空壳 | Login/Home/Characters/Discussions 页面 | 路由切换正常 |
| T5.5 | 布局框架 | 侧边栏 + 顶栏 + 内容区 | 页面结构正常渲染 |
| T5.6 | 前后端联通验证 | 首页显示后端状态 | 页面显示"后端已连接" |
| T5.7 | 公共组件 | 表格、表单弹窗、确认对话框 | 组件独立可用 |

### T6.1-T6.5：Docker Compose + 全链路验收

| 字段 | 内容 |
|------|------|
| 任务 ID | T6.1-T6.5 |
| 任务名称 | Docker Compose + 全链路验收 |
| 所属层次 | 第 6 层 |
| 前置任务 | T4.3 + T5.7（后端 + 前端全部就位） |
| 产出文件 | `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `nginx.conf`, `init.sql` |
| 文件数预估 | 5-6 个文件 |
| 做什么 | 1. `docker-compose.yml`：FastAPI + PostgreSQL + Redis + Nginx + Vue<br>2. PostgreSQL 初始化 SQL（创建数据库、扩展）<br>3. 后端/前端 Dockerfile<br>4. Nginx 配置（SSE buffering off） |
| 不做什么 | 不做 CI/CD 配置、不做 K8s 部署 |
| 验收标准 | `docker compose up -d` → 全部容器 Running → `curl http://localhost/api/v1/health` 返回 200 |
| 拆解依据 | Docker Compose 是所有组件联调的基础。需要后端 + 前端都稳定后才配置 |
| 风险 | 容器间网络、端口映射、volume 权限问题 |

### T7.1-T7.2：启动/停止脚本

| 字段 | 内容 |
|------|------|
| 任务 ID | T7.1-T7.2 |
| 任务名称 | 创建启动/停止脚本 |
| 所属层次 | 第 7 层 |
| 前置任务 | T6.5 |
| 产出文件 | `start.sh`, `stop.sh` |
| 文件数预估 | 2 个文件 |
| 做什么 | `start.sh`：检查依赖 → 启动 Docker Compose → 等待健康检查 → 输出 URL<br>`stop.sh`：停止所有容器 → 清理 |
| 不做什么 | 不做热重载开发模式（那是 dev 脚本） |
| 验收标准 | `bash start.sh` → 全部启动 → `bash stop.sh` → 全部停止 |
| 拆解依据 | 一键启动/停止是项目可交付的基本要求。所有组件验证完后再写 |

## 五、总览时间线

| 顺序 | ID | 任务 | 层 | 前置 | 文件数 | 耗时 |
|------|-----|------|-----|------|-------|------|
| 1 | T0.1 | 虚拟环境 + pyproject.toml | 0 | — | 1 | 短 |
| 2 | T0.2 | 安装核心依赖 | 0 | T0.1 | 0 | 短 |
| 3 | T1.1 | 创建 core/（Result, ErrorCode, 异常） | 1 | T0.2 | 4 | 中 |
| 4 | T1.2 | 创建 config + deps | 1 | T1.1 | 3 | 短 |
| 5 | T1.3 | 创建 ORM 实体（6 个） | 1 | T1.2 | 8 | 长 |
| 6 | T1.4 | 创建中间件（JWT, CORS） | 1 | T1.2 | 3 | 短 |
| 7 | T2.1 | user 模块骨架 | 2 | T1.4 | 5 | 短 |
| 8 | T2.2 | character 模块骨架 | 2 | T2.1 | 5 | 短 |
| 9 | T2.3 | discussion 模块骨架 | 2 | T2.2 | 5 | 短 |
| 10 | T2.4 | realtime 模块骨架 | 2 | T2.3 | 5 | 短 |
| 11 | T2.5 | audit 模块骨架 | 2 | T2.4 | 5 | 短 |
| 12 | T3.1 | main.py + 路由注册 | 3 | T2.5 | 1 | 短 |
| 13 | T3.2 | 健康检查端点 | 3 | T3.1 | 1 | 短 |
| 14 | T3.3 | Alembic 迁移 | 3 | T3.2 | 5-8 | 中 |
| 15 | T3.4 | 后端启动验收 | 3 | T3.3 | — | 短 |
| 16 | T4.1 | agent-engine 骨架 | 4 | T3.4 | 3-5 | 短 |
| 17 | T4.2 | discussion/ 骨架 + SkillFileCache | 4 | T4.1 | 2-3 | 短 |
| 18 | T4.3 | 移植 nuwa-source | 4 | T4.2 | 15+ | 长 |
| 19 | T5.1-T5.7 | 前端工程（7 个子任务） | 5 | T3.4 | 20+ | 长 |
| 20 | T6.1-T6.5 | Docker Compose + 全链路 | 6 | T4.3+T5.7 | 5-6 | 中 |
| 21 | T7.1-T7.2 | 启动/停止脚本 | 7 | T6.5 | 2 | 短 |

总任务数：**21 步**（含前端的 7 个子任务作为一组）
总预估文件数：**100+ 个**
预估执行轮次：**21 轮**

## 六、风险与应对

| 风险 | 严重程度 | 影响任务 | 预防 | 应对 |
|------|---------|---------|------|------|
| deepagents GitHub 安装失败 | 高 | T0.2, T4.3 | Phase 0 网络已通 | 换国内镜像或手动 clone 安装 |
| PostgreSQL 容器启动后连接拒绝 | 中 | T3.3, T6.5 | Docker Compose healthcheck | 检查 volume 权限、端口冲突 |
| AI 硬编码错误码 | 高 | T1.1 | 窄范围指令明确禁止 | SDD 闭环——修代码 + 补 CLAUDE.md |
| Alembic 迁移检测不到模型 | 中 | T3.3 | 模型 import 路径正确 | 检查 Base.metadata 注册 |
| nuwa-source 移植后路径引用失效 | 中 | T4.3 | 对照源码检查 import | 全局替换路径 |
| 前后端联通跨域失败 | 中 | T5.6, T6.5 | Vite proxy 配置 + CORS 中间件 | 检查端口、Origin header |
