# 女娲 Agent (Nvwa Agent)

> 基于 DeepAgents 框架的轻量级智能体，专为女娲 Skill 配套设计，用于蒸馏名人/思想家的思维框架并生成可运行的 Skill

## 项目简介

女娲 Agent 是一个独立的、轻量级的智能体系统，使用 [DeepAgents](https://github.com/langchain-ai/deepagents) 框架构建。它专门为女娲 Skill 生态设计，能够：

- 🔍 **深度调研**：从 6 个维度全面调研人物（著作、对话、表达风格、外部评价、决策记录、时间线）
- 🧠 **框架提炼**：提取核心心智模型和思维框架
- ⚙️ **Skill 生成**：生成可执行的人物视角 Skill（兼容 Claude Code）
- ✅ **质量保证**：3 重验证（已知立场、边缘情况、表达风格）+ 2 轮优化（结构、可用性）
- 💬 **多轮对话**：支持持续交互和上下文记忆

## 核心特性

### 🏗️ 多层 Agent 架构
- **1 个主 Agent**：协调整体流程，支持多轮对话
- **12 个子 Agent**：专业分工，并行执行
  - 6 个调研 Agent（Phase 1）
  - 1 个综合 Agent（Phase 2）
  - 3 个验证 Agent（Phase 4）
  - 2 个优化 Agent（Phase 5）

### 🔄 5 阶段蒸馏流程
```
信息采集 → 框架提炼 → Skill 生成 → 质量验证 → 精炼优化
```

### 🚀 轻量级设计
- 无需 Claude Code 或其他 IDE 集成
- 纯 Python 实现，依赖最小化
- 命令行交互，简单直接
- 独立运行，易于部署

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd deepagents

# 创建虚拟环境（Python 3.11+）
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# Windows: .venv\Scripts\activate

# 安装依赖
pip install -r nvwa_agent/requirements.txt
```

### 2. 配置 API Keys

在项目根目录创建 `.env` 文件（已被 `.gitignore` 忽略，不会提交到 Git）：

```bash
# ============================================================
# 必需配置
# ============================================================

# Tavily 搜索 API（用于网络调研）
# 获取地址：https://tavily.com
# 支持多个 key 用逗号分隔，实现负载均衡
TAVILY_API_KEY="key1,key2,key3"

# MiniMax 模型 API（通过 JD Cloud 端点）
# 如果未设置，程序会报错并退出
OPENAI_API_KEY="your-minimax-key"

# ============================================================
# 可选配置
# ============================================================

# OpenAI API Base URL（默认：JD Cloud 的 MiniMax 端点）
# 如需使用其他端点，可以修改此配置
OPENAI_API_BASE="https://modelservice.jdcloud.com/coding/openai/v1"

# LangSmith 追踪（用于调试和监控，可选）
# 获取地址：https://smith.langchain.com
# 如果未设置，追踪功能会自动禁用
LANGSMITH_API_KEY="your-langsmith-key"
LANGSMITH_PROJECT="nvwa-agent"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
```

**重要提示**：
- ⚠️ `.env` 文件包含敏感信息，**不要提交到 Git**（已在 `.gitignore` 中配置）
- ✅ `TAVILY_API_KEY` 和 `OPENAI_API_KEY` 是必需的
- ✅ LangSmith 配置是可选的，用于调试时追踪 Agent 执行流程
- ✅ 支持多个 Tavily API key 实现负载均衡，用逗号分隔即可

### 3. 运行 Agent

```bash
# 激活虚拟环境
source .venv/bin/activate

# 交互模式（推荐）
python nvwa_agent/run.py

# 单次查询模式
python nvwa_agent/run.py "蒸馏保罗·格雷厄姆的思维方式"
```

### 4. 使用示例

```
欢迎使用女娲 Agent！
输入 'exit' 或 'quit' 退出，输入 'clear' 清空对话历史

You: 蒸馏保罗·格雷厄姆的思维方式

Agent: [开始 6 个维度的并行调研...]
       [提炼心智模型...]
       [生成 Skill 文件...]
       [3 重验证...]
       [2 轮优化...]
       
       ✅ 已生成 Skill: skill-distill/paul-graham-perspective/

You: 继续优化这个 Skill 的表达风格

Agent: [基于上下文继续优化...]
```

## 架构设计

### 主 Agent

**文件**：`nvwa_agent/agent.py`

**职责**：
- 协调 12 个子 Agent 的执行
- 管理 5 个阶段的流程
- 支持多轮对话（使用 `MemorySaver` checkpointer）
- 集成女娲 Skill 系统

**关键配置**：
```python
agent = create_deep_agent(
    model=llm,
    skills=["nuwa-agent-skill"],  # 加载女娲 Skill
    subagents=[...],              # 12 个子 Agent
    checkpointer=MemorySaver(),   # 多轮对话支持
    backend=FilesystemBackend()   # 文件系统访问
)
```

### 子 Agent 体系

#### Phase 1: 信息采集（6 个并行）
| Agent | 职责 |
|-------|------|
| `researcher-writings` | 著作、论文、长文 |
| `researcher-conversations` | 播客、访谈、视频 |
| `researcher-expressions` | 社交媒体、短内容、表达风格 |
| `researcher-external` | 外部评价、批评、他者视角 |
| `researcher-decisions` | 决策记录、行动轨迹 |
| `researcher-timeline` | 人物时间线、关键事件 |

#### Phase 2: 框架提炼（1 个）
| Agent | 职责 |
|-------|------|
| `synthesizer` | 读取 6 个调研文件，提取心智模型 |

#### Phase 4: 质量验证（3 个并行）
| Agent | 职责 |
|-------|------|
| `validator-known` | 测试已知立场的准确性 |
| `validator-edge` | 测试边缘情况的不确定性处理 |
| `validator-voice` | 测试表达风格的还原度 |

#### Phase 5: 精炼优化（2 个并行）
| Agent | 职责 |
|-------|------|
| `optimizer-structure` | 结构和可操作性优化 |
| `optimizer-usability` | 激活触发和可用性优化 |

### 工具系统

**内置工具**：
- `internet_search`：Tavily 网络搜索（支持多 API key 负载均衡）
- `read_file`：读取文件
- `write_file`：写入文件
- `bash`：执行命令
- `list_directory`：列出目录

**速率限制**：
- 2 requests/second（避免 API 过载）
- 最大桶容量：10

## 项目结构

```
deepagents/
├── .env                        # 环境变量配置（不提交）
├── .gitignore                  # Git 忽略规则
├── README.md                   # 本文档
├── AGENTS.md                   # 项目技术文档
│
├── nvwa_agent/                 # 女娲 Agent 核心实现
│   ├── __init__.py             # 包初始化
│   ├── agent.py                # 主 Agent + 12 个子 Agent
│   ├── run.py                  # 命令行启动脚本
│   └── requirements.txt        # Python 依赖
│
├── nuwa-agent-skill/           # 女娲 Skill 定义（source）
│   └── nuwa-skill/
│       ├── SKILL.md            # Skill 指令和流程
│       ├── scripts/            # 辅助脚本
│       └── examples/           # 示例 Skill
│           └── mrbeast-perspective/
│
└── skill-distill/              # 生成的 Skill 输出目录
    └── [person-name]-perspective/
        ├── SKILL.md            # 生成的 Skill 定义
        ├── scripts/            # 工具脚本（可选）
        └── examples/           # 使用示例（可选）
```

## 多轮对话实现

女娲 Agent 支持多轮对话，可以在同一会话中持续交互：

```python
# agent.py 中的实现
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()  # 内存中的对话状态存储

agent = create_deep_agent(
    checkpointer=checkpointer,
    ...
)

# run.py 中的使用
config = {"configurable": {"thread_id": "nvwa-conversation-1"}}

for user_input in conversation:
    agent.stream({"messages": [...]}, config)
```

**关键点**：
- 使用 `MemorySaver` 存储对话历史（内存中）
- 通过 `thread_id` 区分不同会话
- 只有主 Agent 需要 checkpointer，子 Agent 是临时的

## 生成的 Skill 格式

生成的 Skill 存储在 `skill-distill/[person-name]-perspective/` 目录：

```markdown
---
name: paul-graham-perspective
description: 保罗·格雷厄姆的思维方式和创业哲学
trigger: 当需要从创业、产品、写作的角度思考问题时
---

# 保罗·格雷厄姆视角

## 核心心智模型

1. **做不 scale 的事情**
   - 早期专注于深度而非广度
   - 手动服务用户，建立深度理解
   
2. **写作即思考**
   - 通过写作澄清思维
   - 长文是探索的过程
   
...
```

生成的 Skill 可以直接用于 Claude Code：
```bash
# 在 Claude Code 中使用
> 用保罗·格雷厄姆的视角分析这个创业想法
```

## 技术细节

### DeepAgents Skills 系统

女娲 Agent 使用 DeepAgents 的 **SkillsMiddleware** 加载女娲 Skill：

```python
skills_list = ["nuwa-agent-skill"]  # 指向 source 目录
backend = FilesystemBackend(root_dir=str(project_root), virtual_mode=True)

agent = create_deep_agent(
    model=llm,
    skills=skills_list,      # DeepAgents 会扫描 nuwa-agent-skill/nuwa-skill/SKILL.md
    backend=backend,
    checkpointer=checkpointer
)
```

**加载流程**：
1. SkillsMiddleware 扫描 `nuwa-agent-skill/nuwa-skill/SKILL.md`
2. 解析 YAML frontmatter（name, description）
3. 在系统提示中注入 skill 元数据
4. Agent 使用 `read_file` 读取完整指令

### 子 Agent 设计

子 Agent 是 **ephemeral（临时的）**：
- 每次调用都是新实例
- 不需要对话历史
- 专注于单一任务
- 并行执行提高效率

### LangSmith 追踪

默认启用 LangSmith 追踪（可在 `create_nvwa_agent()` 中禁用）：

```python
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "nvwa-agent"
```

## 依赖说明

```
deepagents>=0.5.3          # DeepAgents 框架
langchain-anthropic>=1.4.0 # Anthropic 集成
langchain-openai>=0.3.0    # OpenAI 兼容接口（用于 MiniMax）
tavily-python>=0.5.0       # Tavily 搜索
python-dotenv>=1.0.0       # 环境变量管理
langgraph>=0.2.0           # LangGraph 状态图
```

## 常见问题

### Q: 为什么叫"女娲"？
A: 女娲造人，这个 Agent 蒸馏人物思维并"创造"出可运行的 Skill，寓意相似。

### Q: 必须使用 Claude Code 吗？
A: 不需要。女娲 Agent 是独立的命令行工具，生成的 Skill 可以用于 Claude Code，但 Agent 本身不依赖任何 IDE。

### Q: 支持哪些模型？
A: 默认使用 MiniMax（通过 OpenAI 兼容接口），可以轻松切换到其他模型（Claude、GPT-4 等）。

### Q: 生成的 Skill 可以修改吗？
A: 可以。生成的 Skill 是标准的 Markdown 文件，可以手动编辑和优化。

### Q: 如何添加新的调研维度？
A: 在 `agent.py` 中添加新的子 Agent 到 Phase 1，定义其职责和系统提示即可。

### Q: 多轮对话的历史存储在哪里？
A: 使用 `MemorySaver` 存储在内存中，进程结束后清空。如需持久化，可以切换到 `SqliteSaver`。

## 开发路线图

- [ ] 支持更多模型（Claude、GPT-4、Gemini）
- [ ] 持久化对话历史（SQLite）
- [ ] Web UI 界面
- [ ] Skill 版本管理
- [ ] 批量蒸馏模式
- [ ] 自定义调研维度

## 许可证

MIT License

## 相关项目

- [DeepAgents](https://github.com/langchain-ai/deepagents) - 底层框架
- [女娲 Skill](https://github.com/alchaincyf/nuwa-skill) - Skill 生态

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**女娲造人，智能蒸馏 🎭**
