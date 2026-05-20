# MADF — Multi-Agent Discussion Framework

让 AI 角色坐在一张圆桌上自由辩论——你只需抛出问题。

[![CI/CD](https://img.shields.io/github/actions/workflow/status/dongyu23/MADF-Multi-Agent-Discussion-Framework/ci.yml?branch=main)](https://github.com/dongyu23/MADF-Multi-Agent-Discussion-Framework/actions)
[![Docker Pulls](https://img.shields.io/docker/pulls/frozenfish717/madf)](https://hub.docker.com/r/frozenfish717/madf)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 这是什么？

MADF 是一个多智能体圆桌讨论平台。你选择几个 AI 角色（比如乔布斯、费曼和芒格），给出一个话题，他们会像真人一样自发讨论——不是轮流念稿，而是每轮由"最有话要说"的那个人抢到发言权，流式输出观点。整个过程实时推送到浏览器，你可以随时插话参与。

```
你选角色 → 主持人开场 → Agent 各自思考 → 确信度最高者发言 → 下轮开始
                                                    ↑
                                          你也可以随时插话
```

## 一键部署

```bash
# 拉取镜像
docker pull frozenfish717/madf:latest

# 配置 LLM API key
cat > .env << 'EOF'
LLM_API_KEY=sk-your-key
LLM_MODEL=gpt-4o
TAVILY_API_KEY=tvly-your-key
JWT_SECRET=$(openssl rand -hex 32)
EOF

# 启动
docker compose up -d
```

打开 `http://localhost`，注册账号即可使用。

## 特性

- **去中心化发言** — Agent 每轮独立判断"我有话要说吗"并给出确信度，最高者获得发言权，而非轮流念稿
- **真流式输出** — SSE 逐 token 推送，前端气泡 typewriter 效果，像看直播评论
- **一键生成角色** — 输入人名，系统联网调研（Tavily）→ 自动生成完整 SKILL.md，5 分钟创建新角色
- **Monaco 编辑器管理 Skill** — 文件树 + 代码编辑器查看/编辑角色定义，支持手动精调
- **角色画廊** — 公开分享角色，浏览他人作品并一键复制到自己的角色库
- **用户介入** — 讨论进行中随时通过输入框插话，你的发言会在下一轮被所有 Agent 看到
- **讨论回放** — SSE 断线自动追赶，讨论结束全量加载，不会遗漏任何一轮
- **管理后台** — 独立的审计控制台，用户管理、讨论监控、审计追溯一应俱全

## 目录

- [技术栈](#技术栈)
- [架构](#架构)
- [配置](#配置)
- [开发](#开发)
- [API 概览](#api-概览)
- [License](#license)

## 技术栈

| 层 | 选型 |
|---|------|
| 前端 | React + Monaco Editor + Tailwind CSS |
| 后端 | FastAPI (Python 3.12) |
| 数据库 | PostgreSQL 16 |
| 消息/缓存 | Redis 7 |
| Agent 框架 | deepagents (LangGraph) |
| 大模型 | 云端 API（OpenAI 兼容协议，多 provider 支持） |
| 部署 | Docker Compose (Nginx + Supervisor) |

## 架构

```
浏览器 → Nginx(:80) → FastAPI(:8000) → PostgreSQL + Redis
                         ├── agent_engine (圆桌 Orchestrator)
                         └── skill_gen (角色生成管线)
```

**讨论流程**：每轮每个 Agent 调一次 LLM（非流式）输出决策 JSON `{decision, confidence}`，Orchestrator 收集后选出确信度最高者，赋予发言权后流式输出。全员沉默时随机选一个强制发言。

**角色生成**：输入人名 → 6 个并调研 Agent 通过 Tavily 搜索 → 提炼框架 → 生成 SKILL.md → 3 个验证 Agent 并行检查 → 写入文件系统 + 数据库。

## 配置

所有配置通过 `.env` 设入：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | 大模型 API key | 必填 |
| `LLM_API_BASE` | API 地址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o` |
| `TAVILY_API_KEY` | 联网搜索 key | 可选 |
| `JWT_SECRET` | JWT 签名密钥 | 必改 |

完整变量见 `.env.template`。

## 开发

```bash
# 前置条件：Python 3.12+、Node 22+、PostgreSQL、Redis

# 后端
pip install -e ".[dev]"
pip install git+https://github.com/langchain-ai/deepagents.git#subdirectory=libs/deepagents langchain-openai tavily-python
alembic upgrade head
uvicorn backend.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev

# 审计后端
uvicorn audit_backend.main:app --reload --port 8001
```

## API 概览

所有接口前缀 `/api/v1/`，统一响应结构 `{code, message, data}`。

```
POST   /auth/register                  注册
POST   /auth/login                     登录
GET    /characters                     角色列表
POST   /characters                     创建角色
POST   /characters/{id}/generate       生成 Skill
GET    /characters/{id}/generation-progress  SSE 生成进度
POST   /characters/{id}/copy           从画廊复制
GET    /discussions                    讨论列表
POST   /discussions                    创建讨论
GET    /discussions/{id}/stream         SSE 实时流
POST   /discussions/{id}/intervene     用户插话
GET    /discussions/{id}/messages      消息历史
GET    /discussions/{id}/audit         审计事件
```

管理后台监听 81 端口，审计 API 前缀 `/audit/api/`。

## License

MIT
