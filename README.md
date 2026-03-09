# 🎭 MADF: Multi-Agent Discussion Framework

> **让思想在代码中碰撞，让灵魂在字节间共鸣。**

---

### 🌟 想象一下...

想象一下，你置身于一个跨越时空的圆桌会议室。

左手边，**苏格拉底**正抚须沉思，准备用反诘法拆解看似坚固的真理；右手边，**埃隆·马斯克**正激动地挥舞着双手，描绘着火星殖民的宏伟蓝图；而坐在对面的，或许是**孔子**，正温和地阐述着“仁”的治世之道。

他们不再是冰冷的历史符号，也不是只会机械问答的搜索引擎。在这个框架中，他们拥有了**记忆**，拥有了**性格**，甚至拥有了**偏见**。他们会争论，会妥协，会因为观点的共鸣而激动，也会因为理念的冲突而愤怒。

这不是科幻小说，这是 **MADF (Multi-Agent Discussion Framework)** 为你呈现的数字现实。

我们构建的不仅仅是一个聊天室，而是一个**思想的培养皿**。在这里，你可以：
*   观察不同流派的哲学如何交锋；
*   模拟复杂的社会决策过程；
*   甚至仅仅是享受一场高质量的、充满意外的智力狂欢。

---

### 🎯 项目核心

MADF 是一个基于大语言模型（LLM）的**沉浸式多智能体圆桌讨论框架**。它致力于解决传统 AI 对话的“空洞”与“无序”，通过精细的架构设计，赋予智能体真正的“灵魂”。

*   **🧠 深度角色生成 (RealGod Agent)**: 基于 ReAct 框架，智能体能够主动搜索互联网，学习真实人物的生平、理论与性格，拒绝脸谱化的 NPC。
*   **💾 双层记忆系统**: 
    *   **私有记忆**: 智能体拥有内心独白，能记住自己的思考过程，避免“复读机”式的发言。
    *   **共享记忆**: 所有参与者共享讨论上下文，确保对话的连贯性与针对性。
*   **🎤 动态主持机制**: 引入主持人（Moderator）角色，负责控场、总结与推进议题，防止讨论发散或陷入死循环。
*   **📊 多维评估体系**: 独创的 5 维评估指标（观点多样性、深度演进、交互批判性等），量化讨论质量。

---

### 🏗️ 系统架构介绍

MADF 采用 **现代化的前后端分离架构**，后端基于 Python 异步生态构建高性能调度中心，前端采用 Vue 3 打造沉浸式交互体验，通过 WebSocket 实现毫秒级的双向流式通信。

#### 1. 整体架构图

```mermaid
graph TD
    User[用户 (Browser)]
    
    subgraph Frontend ["前端 (Vue 3 + Vite)"]
        UI[界面组件 (Ant Design Vue)]
        Store[状态管理 (Pinia)]
        WS_Client[WebSocket 客户端]
    end
    
    subgraph Backend ["后端 (FastAPI)"]
        API[API 网关 / 路由]
        Auth[认证与权限 (OAuth2/JWT)]
        
        subgraph Services [核心服务层]
            Scheduler[论坛调度器 (ForumScheduler)]
            GodAgent[角色生成 (God Agent)]
            Moderator[主持人代理]
            Participant[嘉宾代理]
        end
        
        WS_Server[WebSocket 服务端]
        LLM_Client[LLM 统一接口 (ZhipuAI)]
    end
    
    subgraph Data [数据层]
        SQLite[(SQLite/PostgreSQL)]
        Redis[(Redis 缓存/消息队列)]
    end
    
    subgraph External [外部服务]
        GLM4[智谱 GLM-4 API]
        Search[搜索引擎 API]
    end

    User <-->|HTTP/WebSocket| Frontend
    Frontend <-->|REST API| API
    Frontend <-->|WebSocket| WS_Server
    
    API --> Services
    WS_Server <--> Scheduler
    
    Scheduler --> LLM_Client
    GodAgent --> LLM_Client
    GodAgent --> Search
    
    LLM_Client --> GLM4
    
    Services --> SQLite
    Services --> Redis
    
    classDef box fill:#f9f,stroke:#333,stroke-width:2px;
    class Frontend,Backend,Data,External box;
```

#### 2. 逐层解析

**🖥️ 前端层 (Frontend)**
- **技术栈**: Vue 3 (Composition API), Vite, TypeScript, Pinia, Ant Design Vue。
- **核心职责**:
    - **流式渲染**: 通过 `useForumWebSocket` 钩子实时接收后端 Token 流，实现“打字机”效果。
    - **状态管理**: 利用 Pinia 管理全局的用户会话、论坛列表及当前对话上下文。
    - **路由与权限**: Vue Router 配合导航守卫，实现基于 JWT 的登录拦截与页面跳转。

**⚙️ 后端层 (Backend)**
- **技术栈**: Python 3.10+, FastAPI, Uvicorn, Pydantic。
- **核心模块**:
    - **API 网关**: 处理 HTTP 请求（如创建论坛、查询历史），集成 CORS 与 JWT 鉴权中间件。
    - **论坛调度器 (ForumScheduler)**: 系统的“心脏”，基于 `asyncio` 维护全局事件循环，管理多个智能体的并发思考、发言队列及时间片轮转。
    - **LLM 客户端**: 统一封装智谱 GLM-4 接口，支持流式响应 (Stream Response) 和 JSON 格式化输出。
- **通信协议**:
    - **HTTP (REST)**: 用于元数据管理（User, Forum, Persona）。
    - **WebSocket**: 用于实时传输对话内容、系统日志及控制信号。

**💾 数据层 (Data Layer)**
- **数据库**:
    - **SQLite (默认)**: 采用 `libsql-client`，零配置启动，适合开发与中小规模部署。
    - **PostgreSQL (生产可选)**: 通过环境变量无缝切换，支持更高并发与数据可靠性。
- **缓存/消息队列**:
    - **Redis (可选)**: 用于存储系统日志缓冲 (System Logs Buffer) 和高频状态同步。

**🏗️ 基础设施 (Infrastructure)**
- **容器化**: 提供标准 `Dockerfile`，支持多阶段构建 (Multi-stage Build)，最小化镜像体积。
- **编排**: `docker-compose.yml` 一键拉起前后端及依赖服务。
- **CI/CD**: 集成 GitHub Actions，自动化执行单元测试 (Pytest/Vitest) 与构建流程。

#### 3. 关键非功能特性
- **性能**: WebSocket 端到端延迟 < 200ms；支持单节点并发 50+ 智能体实时辩论。
- **可用性**: 具备 API 超时自动熔断与重试机制，确保 LLM 波动时不影响系统崩溃。
- **扩展性**: `BaseAgent` 类设计遵循开闭原则，易于扩展新的角色类型（如“记录员”、“捣乱者”）。
- **安全**: 生产环境强制开启 JWT 认证；敏感密钥 (API Key) 仅在服务端存储，不暴露给前端。

#### 4. 架构决策记录 (ADR)
我们记录了项目演进过程中的关键架构决策，以供查阅：
- [ADR-001: 选用 FastAPI 作为后端框架](docs/adr/001-backend-framework-fastapi.md)
- [ADR-002: 选用 Vue 3 + Vite 作为前端技术栈](docs/adr/002-frontend-framework-vue3.md)
- [ADR-003: 选用 SQLite 作为默认数据库](docs/adr/003-database-selection-sqlite.md)

---

### 🚀 快速启动

你可以选择**一键脚本启动**（推荐），也可以选择**手动分步启动**。

#### 1. 环境准备
确保你的电脑上安装了：
*   Python 3.10+
*   Node.js 16+
*   Git

#### 2. 克隆项目
```bash
git clone https://github.com/your-repo/MADF.git
cd MADF
```

#### 3. 配置密钥
MADF 采用环境变量管理配置。请复制示例文件并填入你的密钥：
```bash
cp .env.example .env
```
编辑 `.env` 文件：
```ini
# LLM API Configuration
API_KEY=your_glm_api_key
MODEL_NAME=glm-4.6
BASE_URL=https://open.bigmodel.cn/api/paas/v4/

# Search API Configuration
SERPAPI_API_KEY=your_serpapi_key
```

#### 4. 方式一：一键脚本启动 (推荐)
- **Windows**: 双击根目录下的 **`start.bat`**。
- **Mac/Linux**: 运行 `./start.sh`。

#### 5. 方式二：手动分步启动

如果你希望更精细地控制运行过程，可以分别启动后端和前端：

**步骤 A: 启动后端 (FastAPI)**
```bash
# 创建并激活虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
后端服务地址: `http://localhost:8000/docs`

**步骤 B: 启动前端 (Vue 3)**
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```
前端访问地址: `http://localhost:5173`

#### 6. 方式三：Docker 部署 (推荐生产环境)

如果你希望在容器化环境中运行 MADF，可以使用提供的 Dockerfile。它会自动构建前端并由后端统一提供服务：

```bash
# 构建镜像
docker build -t madf:latest .

# 运行容器
# 请确保通过环境变量传入 API 密钥
docker run -d -p 8000:8000 \
  -e API_KEY="你的_LLM_API_KEY" \
  -e MODEL_NAME="glm-4.6" \
  -e SERPAPI_API_KEY="你的_SERPAPI_KEY" \
  madf:latest
```
访问地址: `http://localhost:8000`

---

### 🖥️ 体验流程

1.  **访问前端**: 浏览器打开 `http://localhost:5173`。
2.  **创建角色**: 点击“上帝模式”，输入“乔布斯”或“一位悲观的历史学家”，观察 AI 如何通过搜索构建角色档案。
3.  **开启论坛**: 设定议题（如“AI 是否会毁灭人类？”），选择参与者，点击“开始”。
4.  **旁观/干预**: 你可以作为上帝静静观察，也可以随时暂停，查看智能体的“内心独白”，甚至直接干预讨论走向。

---

### 📚 深入阅读

*   **[架构设计](docs/ARCHITECTURE.md)**: 理解系统的灵魂与骨架。
*   **[开发指南](docs/GUIDE.md)**: 如何从零开始构建你的智能体。
*   **[实验报告](exam/results/)**: 查看我们在“人类是否应该探索火星”等议题上的消融实验结果。

---

**加入 MADF，让 AI 不止于问答，更始于思考。**
