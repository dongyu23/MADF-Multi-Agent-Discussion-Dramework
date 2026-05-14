# Test Cases: MADF 多智能体圆桌讨论平台

## Overview
- **Feature**: 一期全部功能（A-M）
- **Requirements Source**: CLAUDE.md
- **Test Coverage**: 功能性、边界条件、错误处理、状态转换
- **Last Updated**: 2026-05-14

---

## 一、用户模块（功能 J/K）

### TC-F-001：用户注册成功
- **Requirement**: J. 注册/登录
- **Priority**: High
- **Preconditions**: 无
- **Test Steps**:
  1. POST `/api/v1/auth/register` body: `{username:"newuser", password:"test123456", phone:"13900000001"}`
  2. 检查响应
- **Expected Results**:
  - HTTP 200, code=200
  - data.token.token 非空 JWT 字符串
  - data.user.username = "newuser"
  - data.user.id 为 UUID 格式
- **Postconditions**: users 表有新记录, audit_events 有 `user.register` 事件

### TC-F-002：用户登录成功
- **Requirement**: J. 注册/登录
- **Priority**: High
- **Preconditions**: 用户已注册
- **Test Steps**:
  1. POST `/api/v1/auth/login` body: `{username:"newuser", password:"test123456"}`
- **Expected Results**:
  - HTTP 200, code=200
  - data.token.token 非空 JWT 可解码
  - audit_events 有 `user.login` 事件

### TC-E-001：重复注册
- **Requirement**: J
- **Priority**: High
- **Preconditions**: 用户名已存在
- **Test Steps**:
  1. POST `/api/v1/auth/register` 使用已存在的 username
- **Expected Results**:
  - HTTP 409, code=2001 (USERNAME_EXISTS)

### TC-ERR-001：密码错误登录
- **Requirement**: J
- **Priority**: High
- **Preconditions**: 用户已注册
- **Test Steps**:
  1. POST `/api/v1/auth/login` body: `{username:"newuser", password:"wrong_password"}`
- **Expected Results**:
  - HTTP 400, code=2004 (WRONG_PASSWORD)
  - audit_events 有 `user.login_failed` 事件

### TC-ERR-002：无 Token 访问受保护接口
- **Requirement**: J
- **Priority**: High
- **Preconditions**: 无
- **Test Steps**:
  1. GET `/api/v1/auth/me` 不带 Authorization header
- **Expected Results**:
  - HTTP 401

### TC-ERR-003：无效 Token 访问
- **Requirement**: J
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/v1/auth/me` 带 `Authorization: Bearer invalidtoken`
- **Expected Results**:
  - HTTP 401

---

## 二、角色模块（功能 G/H/I）

### TC-F-003：AI 生成角色 Skill
- **Requirement**: G. 角色 Skill 生成
- **Priority**: High
- **Preconditions**: .env 已配置 LLM_API_KEY + TAVILY_API_KEY, 用户已登录
- **Test Steps**:
  1. POST `/api/v1/characters/generate` body: `{query:"Steve Jobs"}`
  2. 立即检查返回的 skill.status = "generating"
  3. SSE 连接 `GET /api/v1/characters/{id}/generation-progress`
  4. 等待 status 变为 "ready"
  5. GET `/api/v1/characters/{id}/files` 检查产物
- **Expected Results**:
  - SSE 事件包含: level=main, level=sub (12 个子 Agent), level=done
  - SKILL.md 包含 YAML frontmatter + 10 个标准 section
  - references/research/ 有 01-06.md 调研文件
  - 调研文件包含 URL 链接
  - source_count ≥ 1
- **Postconditions**: skills/ 目录有完整 skill 文件夹, PG skills 表 status=ready

### TC-F-004：创建角色
- **Requirement**: H. 角色 Skill 管理
- **Priority**: High
- **Test Steps**:
  1. POST `/api/v1/characters` body: `{name:"Test", description:"desc", tags:["a","b"], is_public:true}`
- **Expected Results**:
  - HTTP 200
  - data.name 以 "-perspective" 结尾
  - skills/ 目录有 SKILL.md 文件
  - audit_events 有 `skill.create` 事件

### TC-F-005：角色列表（分页）
- **Requirement**: H/I
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/v1/characters?page=1&page_size=5`
- **Expected Results**:
  - data.items 数组长度 ≤ 5
  - data.total ≥ 0
  - data.has_more 正确
  - 响应字段: id, owner_id, name, description, tags, is_public, status, created_at

### TC-F-006：角色详情
- **Requirement**: H
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/v1/characters/{id}`
- **Expected Results**:
  - HTTP 200, 包含完整字段

### TC-F-007：更新角色
- **Requirement**: H
- **Priority**: Medium
- **Test Steps**:
  1. PUT `/api/v1/characters/{id}` body: `{description:"new desc", is_public:false}`
- **Expected Results**:
  - data.description = "new desc"
  - data.is_public = false
  - audit_events 有 `skill.update`，changed_fields 包含 ["description", "is_public"]

### TC-F-008：删除角色
- **Requirement**: H
- **Priority**: High
- **Test Steps**:
  1. DELETE `/api/v1/characters/{id}`
  2. GET `/api/v1/characters?page=1` 确认已移除
- **Expected Results**:
  - HTTP 200 (软删除)
  - skills/ 目录已删除
  - audit_events 有 `skill.delete`

### TC-F-009：公开画廊
- **Requirement**: H/I
- **Priority**: Medium
- **Preconditions**: 至少一个 is_public=true 且 status=ready 的角色
- **Test Steps**:
  1. GET `/api/v1/characters/gallery?page_size=5`
  2. 测试搜索: `?search=Jobs`
  3. 测试标签: `?tag=产品`
  4. 测试游标: `?after={created_at}`
- **Expected Results**:
  - 只返回 public+ready 的角色
  - data.has_more 标识正确
  - 游标分页正确

### TC-F-010：画廊复制
- **Requirement**: H/I
- **Priority**: Medium
- **Preconditions**: 另一个用户有公开角色
- **Test Steps**:
  1. 用户B登录
  2. POST `/api/v1/characters/{id}/copy`
  3. GET `/api/v1/characters` 确认新角色存在
- **Expected Results**:
  - HTTP 200
  - 新角色 owner_id = 用户B
  - 新角色 is_public = false
  - skills/ 目录完整复制
  - audit_events 有 `skill.copy`

### TC-F-011：角色文件列表与读取
- **Requirement**: H
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/v1/characters/{id}/files` → 返回文件清单
  2. GET `/api/v1/characters/{id}/files?path=SKILL.md` → 返回纯文本
- **Expected Results**:
  - 文件列表包含 "SKILL.md"
  - SKILL.md 内容非空

### TC-E-002：角色名称重复
- **Requirement**: H
- **Priority**: Medium
- **Test Steps**:
  1. 创建同名角色
- **Expected Results**:
  - HTTP 409, code=3004 (SKILL_NAME_EXISTS)

### TC-E-003：路径穿越防护
- **Requirement**: H
- **Priority**: High
- **Test Steps**:
  1. PUT `/api/v1/characters/{id}/files` body: `{path:"../../../etc/passwd", content:"test"}`
- **Expected Results**:
  - ValueError 或 400 错误

### TC-ERR-004：生成已存在的角色
- **Requirement**: G
- **Priority**: Medium
- **Test Steps**:
  1. 对已存在的角色名再次调用 generate
- **Expected Results**:
  - HTTP 409, code=3004

### TC-ERR-005：删除有依赖的角色
- **Requirement**: H
- **Priority**: Low
- **Test Steps**:
  1. 创建讨论使用某角色
  2. 尝试删除该角色
- **Expected Results**:
  - 应返回 409 或提示 `SKILL_IN_USE`

### TC-ERR-006：不存在的角色
- **Requirement**: H
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/v1/characters/00000000-0000-0000-0000-000000000000`
- **Expected Results**:
  - HTTP 404

---

## 三、讨论模块（功能 A/B/C/D/E/F）

### TC-F-012：创建讨论并启动
- **Requirement**: A/B. 讨论创建 + 去中心化发言
- **Priority**: High
- **Preconditions**: 至少 2 个 status=ready 的角色
- **Test Steps**:
  1. POST `/api/v1/discussions` body: `{topic:"测试讨论", character_ids:[id1,id2], duration:120}`
  2. 立即检查返回值
  3. SSE 连接 `GET /api/v1/discussions/{id}/stream`
- **Expected Results**:
  - HTTP 200
  - data.status = "running" 或 "starting"
  - data.topic = "测试讨论"
  - audit_events 有 `discussion.create`
  - SSE 收到 host_intro 事件

### TC-F-013：主持人开场
- **Requirement**: E
- **Priority**: Medium
- **Test Steps**:
  1. 在 SSE 流中监听 host_intro 事件
- **Expected Results**:
  - 包含讨论主题和参与嘉宾信息
  - 内容非空，3-5 句

### TC-F-014：去中心化发言流程
- **Requirement**: B
- **Priority**: High
- **Test Steps**:
  1. 创建 2-Agent 讨论，duration=60
  2. 监听 SSE 事件流
  3. 验证每轮: agent_think(×2) → agent_speak_start → agent_speak_chunk(×N) → agent_speak_end
- **Expected Results**:
  - agent_think 包含: decision, confidence(两位小数), reasoning
  - 同一发言人 chunks 追加到同一气泡（前端验证）
  - confidence 最高者获得发言权
  - reasoning 以第一人称"我"出发

### TC-F-015：全员沉默强制发言
- **Requirement**: B
- **Priority**: Medium
- **Test Steps**:
  1. 两个 Agent 倾向 wait 的讨论场景
- **Expected Results**:
  - 随机选一个 Agent 发言
  - 讨论继续进行不中断

### TC-F-016：流式发言真 Token 级推送
- **Requirement**: C
- **Priority**: High
- **Test Steps**:
  1. 监听 SSE agent_speak_chunk 事件
  2. 统计 chunks 数量和间隔
- **Expected Results**:
  - chunks 数量 > 10（非假流式手动分块）
  - chunks 间隔自然（非等间隔）
  - 前端同发言人追加到同一气泡

### TC-F-017：主持人总结
- **Requirement**: E
- **Priority**: Medium
- **Test Steps**:
  1. 等讨论 duration 到期
  2. 监听 host_summary 事件
- **Expected Results**:
  - 内容概括各方观点和分歧
  - discussion_end 事件随后触发
  - discussion.status = "completed"

### TC-F-018：讨论历史消息加载
- **Requirement**: F
- **Priority**: High
- **Test Steps**:
  1. GET `/api/v1/discussions/{id}/messages`
  2. 验证消息类型
- **Expected Results**:
  - 返回按 created_at 升序的消息列表
  - 包含 message_type, agent_name, content, round_number

### TC-F-019：SSE 断开重连追赶
- **Requirement**: F
- **Priority**: High
- **Test Steps**:
  1. 连接 SSE 5 秒后断开
  2. 20 秒后重连 `?after={断开时时间戳}`
  3. 监听 catchup_start/catchup_summary 事件
- **Expected Results**:
  - 追赶事件推送断开期间的消息
  - 追赶完成后接入实时流
  - 不重复推送

### TC-F-020：讨论结束后加载历史
- **Requirement**: F
- **Priority**: Medium
- **Test Steps**:
  1. 讨论 completed 后访问页面
  2. 前端自动调 GET `/discussions/{id}/messages` 全量加载
- **Expected Results**:
  - 完整对话渲染，无缺失

### TC-E-004：最短/最长讨论时长
- **Requirement**: A
- **Priority**: Medium
- **Test Steps**:
  1. duration=59 → 应 422
  2. duration=3601 → 应 422
  3. duration=60 → 应 200
  4. duration=3600 → 应 200
- **Expected Results**:
  - Pydantic validation 生效

### TC-ERR-007：使用未就绪角色创建讨论
- **Requirement**: A
- **Priority**: Medium
- **Test Steps**:
  1. 用 status=generating 的角色创建讨论
- **Expected Results**:
  - HTTP 400, code=3002 或 4003

### TC-ERR-008：不存在的讨论
- **Requirement**: A
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/v1/discussions/00000000-0000-0000-0000-000000000000`
- **Expected Results**:
  - HTTP 404, code=4001

### TC-ERR-009：orchestrator 崩溃恢复
- **Requirement**: F
- **Priority**: High
- **Test Steps**:
  1. 模拟 orchestrator 异常（如 LLM API key 无效）
- **Expected Results**:
  - discussion.status = "error"
  - audit_events 有 `discussion.error` 事件
  - SSE 收到错误提示

---

## 四、审计模块（功能 L）

### TC-F-021：审计事件写入
- **Requirement**: L
- **Priority**: High
- **Test Steps**:
  1. 执行注册操作
  2. 执行登录操作（成功+失败）
  3. 执行角色 CRUD
  4. 创建讨论
  5. 查询 audit_events 表
- **Expected Results**:
  - 每个操作对应一条审计事件
  - event_type 正确
  - payload 包含相关上下文
  - user_id 正确关联

### TC-F-022：审计事件查询
- **Requirement**: L
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/v1/discussions/{id}/audit`
  2. 测试筛选: `?event_type=agent_think`
  3. 测试游标: `?after={timestamp}`
- **Expected Results**:
  - 返回该讨论的所有审计事件
  - 筛选和分页正常工作

---

## 五、部署与运维（功能 M）

### TC-F-023：Docker Compose 全栈启动
- **Requirement**: M
- **Priority**: High
- **Test Steps**:
  1. `docker compose up -d`
  2. 等待所有容器 healthy
  3. curl `http://localhost:8000/api/v1/health`
  4. curl `http://localhost`
- **Expected Results**:
  - 4 个容器 Running
  - PostgreSQL + Redis healthy
  - Backend health 返回 200
  - Frontend Nginx 返回 200

### TC-F-024：SSE 流式 Nginx 配置
- **Requirement**: C
- **Priority**: Medium
- **Test Steps**:
  1. 通过 Nginx 代理建立 SSE 连接
  2. 验证流式数据实时到达
- **Expected Results**:
  - 代理不缓冲 SSE 数据
  - proxy_buffering=off 生效

---

## 六、前端 UI（7 页）

### TC-F-025：登录页 → 跳转首页
- **Priority**: High
- **Test Steps**:
  1. 浏览器打开 `/login`
  2. 输入用户名密码，点击登录
  3. 验证跳转到 `/home`
- **Expected Results**:
  - 登录成功 → 跳转首页
  - 登录失败 → 显示错误信息
  - Token 过期 → 跳转 `/login?redirect=原页`

### TC-F-026：首页状态展示
- **Priority**: Medium
- **Test Steps**:
  1. 打开 `/home`
  2. 查看服务状态指示器
- **Expected Results**:
  - 在线: 绿色脉冲圆点 + "服务运行中"
  - 离线: 红色圆点 + "服务离线"
  - 角色数/讨论数统计正确

### TC-F-027：角色列表 → 画廊切换
- **Priority**: Medium
- **Test Steps**:
  1. 打开 `/characters`
  2. 查看"我的角色" tab
  3. 切换到"公开画廊" tab
  4. 搜索 + 标签筛选
  5. 点击"复制到我的"
- **Expected Results**:
  - 两个 tab 独立加载
  - 画廊搜索筛选生效
  - 复制后出现在"我的角色"

### TC-F-028：角色生成进度 SSE
- **Priority**: High
- **Test Steps**:
  1. 输入人名点击"AI 生成"
  2. 跳转到详情页
  3. 观察 SSE 进度面板
- **Expected Results**:
  - 显示当前阶段中文描述
  - 子 Agent 卡片逐一出现
  - 完成后自动刷新加载文件

### TC-F-029：Monaco Editor 文件浏览
- **Priority**: Medium
- **Test Steps**:
  1. 打开角色详情页
  2. 点击文件树中的不同文件
  3. 查看编辑器内容
- **Expected Results**:
  - Monaco Editor 正确加载内容
  - 文件切换流畅
  - 只读模式/编辑模式符合状态

### TC-F-030：讨论室实时气泡
- **Priority**: High
- **Test Steps**:
  1. 创建讨论后进入讨论室
  2. 观察主持人开场气泡
  3. 观察思考气泡（含确信度）
  4. 观察发言气泡（typewriter 效果）
  5. 底部输入框介入发言
- **Expected Results**:
  - 发言气泡同发言人追加不重复创建
  - 思考气泡显示 reasoning
  - 用户介入气泡正确显示
  - 讨论结束后显示总结

---

## Test Coverage Matrix

| 功能 | 测试用例 | 类型覆盖 | 状态 |
|------|---------|---------|------|
| A. 讨论创建 | TC-F-012, TC-E-004 | F/E | ✓ |
| B. 去中心化发言 | TC-F-014, TC-F-015 | F/E | ✓ |
| C. 流式输出 SSE | TC-F-016, TC-F-024, TC-F-030 | F | ✓ |
| D. 用户介入 | TC-F-030 | F | ✓ |
| E. 主持人开场/摘要 | TC-F-013, TC-F-017 | F | ✓ |
| F. 讨论历史回放 | TC-F-018, TC-F-019, TC-F-020, TC-ERR-009 | F/E | ✓ |
| G. 角色 Skill 生成 | TC-F-003, TC-ERR-004 | F/E | ✓ |
| H. 角色 Skill 管理 | TC-F-004~008, TC-F-011, TC-E-002/003, TC-ERR-005/006 | F/E | ✓ |
| I. 角色选择 | TC-F-009, TC-F-010 | F | ✓ |
| J. 注册/登录 | TC-F-001/002, TC-E-001, TC-ERR-001~003 | F/E | ✓ |
| K. 用户数据绑定 | TC-F-001 | F | ✓ |
| L. 业务审计 | TC-F-021, TC-F-022 | F | ✓ |
| M. Docker Compose | TC-F-023 | F | ✓ |

## Notes
- 登录态 Token 过期：前端拦截器 `code=1002/1003` → 跳转 `/login?redirect=`
- 发言模式要求 reasoning 从"我"出发，禁止"作为AI"等表达
- 审计写入与业务操作共享 DB session，成功一起提交失败一起回滚
- SSE 追赶分级: ≤20 逐条 / 20-200 批量 / >200 摘要+最近 20
