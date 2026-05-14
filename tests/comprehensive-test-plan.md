# MADF Comprehensive Test Plan

## 一、测试层次与策略

| 层 | 框架 | 范围 | 速度 | 覆盖率目标 |
|---|---|---|---|---|
| **L1: 单元测试** | pytest + unittest.mock | 纯函数、Pydantic schema、工具类 | < 1s/file | 90%+ |
| **L2: 服务层测试** | pytest + AsyncMock | Service 业务逻辑（mock Repository + 外部依赖） | < 2s/file | 85%+ |
| **L3: 集成测试** | pytest + httpx + 真实 PG/Redis | Router→Service→Repository→DB 全链路 | < 30s 总 | 核心流程 100% |
| **L4: E2E 测试** | Playwright | 浏览器端到端 | < 3min | 关键路径 |
| **静态分析** | mypy + ruff | 类型安全 + 代码规范 | < 5s | 0 错误 |

---

## 二、L1: 单元测试

### 2.1 Pydantic Schema 验证 (`tests/test_schemas.py`)

| ID | 测试名 | 输入 | 预期 |
|---|---|---|---|
| SC-01 | `test_user_register_valid` | 合法 username + password | 通过验证 |
| SC-02 | `test_user_register_username_too_short` | username="a" (1 字符) | ValidationError |
| SC-03 | `test_user_register_password_too_short` | password="12345" (5 字符) | ValidationError |
| SC-04 | `test_user_register_username_max_length` | 64 字符 username | 通过验证 |
| SC-05 | `test_user_register_username_too_long` | 65 字符 | ValidationError |
| SC-06 | `test_discussion_create_duration_boundary` | duration=60/3600 | 通过, duration=59/3601→error |
| SC-07 | `test_discussion_create_empty_characters` | character_ids=[] | ValidationError |
| SC-08 | `test_discussion_create_too_many_characters` | 11 个 character_ids | ValidationError |
| SC-09 | `test_character_create_empty_tags` | tags=[] | 通过, tags 为 [] |
| SC-10 | `test_gallery_page_size_max` | page_size=51 | ValidationError |

### 2.2 配置验证 (`tests/test_config.py`)

| ID | 测试名 | 描述 |
|---|---|---|
| CF-01 | `test_default_settings` | 无 .env 时使用默认值 |
| CF-02 | `test_db_url_property` | 验证拼接后的 URL 格式 |
| CF-03 | `test_redis_url_property` | 验证 Redis URL 格式 |
| CF-04 | `test_jwt_expire_minutes_positive` | jwt_expire_minutes > 0 |

### 2.3 异常处理 (`tests/test_exceptions.py`)

| ID | 测试名 | 描述 |
|---|---|---|
| EX-01 | `test_business_exception_creation` | 验证 ErrorCode → exc 构建 |
| EX-02 | `test_http_status_mapping` | 全部 16 个 ErrorCode → HTTP 状态码 |
| EX-03 | `test_result_ok_format` | Result.ok() 序列化格式 |
| EX-04 | `test_result_fail_format` | Result.fail() 序列化格式 |
| EX-05 | `test_page_result_has_more` | has_more 计算正确性 |
| EX-06 | `test_page_result_no_more` | 最后一页 has_more=false |

### 2.4 文件管理器 (`tests/test_file_manager.py`)

| ID | 测试名 | 描述 |
|---|---|---|
| FM-01 | `test_create_skill_dir` | 创建目录结构 |
| FM-02 | `test_write_and_read_file` | 写入→读取往返 |
| FM-03 | `test_list_files` | 列出所有文件（含嵌套） |
| FM-04 | `test_path_traversal_blocked` | `../../../etc/passwd` 应抛出 ValueError |
| FM-05 | `test_delete_skill_dir` | 删除后 directory 不存在 |
| FM-06 | `test_copy_skill` | 跨 owner 复制后文件一致 |

### 2.5 依赖注入 (`tests/test_deps.py`)

| ID | 测试名 | 描述 |
|---|---|---|
| DP-01 | `test_get_current_user_no_token` | 无 token 时返回空字符串 |
| DP-02 | `test_get_current_user_valid_token` | 有合法 token 返回 user_id |
| DP-03 | `test_get_current_user_invalid_token` | 无效 token 抛出 401 |
| DP-04 | `test_require_user_no_token` | 无 token 时抛出 401 |
| DP-05 | `test_require_user_valid_token` | 有 token 返回 user_id |

---

## 三、L2: 服务层测试

### 3.1 用户服务 (`tests/test_user_service.py`)

所有测试 mock `UserRepository` + `AuditRepository`，不连接真实数据库。

| ID | 测试名 | 描述 |
|---|---|---|
| US-01 | `test_register_success` | 注册成功返回 token + user |
| US-02 | `test_register_username_exists` | 重复用户名 → USERNAME_EXISTS |
| US-03 | `test_register_phone_exists` | 重复手机号 → PHONE_EXISTS |
| US-04 | `test_login_success` | 登录成功 → token |
| US-05 | `test_login_user_not_found` | 用户不存在 → USER_NOT_FOUND |
| US-06 | `test_login_wrong_password` | 密码错误 → WRONG_PASSWORD |
| US-07 | `test_get_me_success` | 获取当前用户 |
| US-08 | `test_get_me_user_not_found` | 用户不存在 → USER_NOT_FOUND |
| US-09 | `test_password_is_hashed` | 验证密码经过 bcrypt hash |

### 3.2 讨论 Schema 验证 (`tests/test_discussion_schemas.py`)

| ID | 测试名 | 描述 |
|---|---|---|
| DS-01 | `test_create_valid` | 合法参数通过验证 |
| DS-02 | `test_duration_minimum` | duration=59 → ValidationError |
| DS-03 | `test_duration_maximum` | duration=3601 → ValidationError |
| DS-04 | `test_empty_topic` | topic="" → ValidationError |
| DS-05 | `test_message_response_exclude_none` | confidence 为 None 时不在输出中 |

---

## 四、L3: API 集成测试（扩展）

在现有 `test_api_integration.py` 基础上新增：

| ID | 测试名 | 优先级 | 描述 |
|---|---|---|---|
| IT-11 | `test_register_duplicate_username` | High | 重复注册返回 409 + code 2001 |
| IT-12 | `test_login_invalid_password` | High | 密码错误返回 400 + code 2004 |
| IT-13 | `test_character_unauthorized_write` | Medium | 无 token 创建角色返回 401 |
| IT-14 | `test_character_update_not_owner` | Medium | 修改他人角色返回 403 |
| IT-15 | `test_character_delete_cascade` | High | 删除角色后 GET 返回 404 |
| IT-16 | `test_discussion_invalid_duration` | Medium | duration=59 → 422 |
| IT-17 | `test_discussion_with_generating_agent` | Medium | 使用未就绪角色 → 400 |
| IT-18 | `test_gallery_only_public_ready` | Medium | 画廊只返回 is_public=true + ready |
| IT-19 | `test_intervene_discussion_ended` | Low | 已结束讨论不能介入 |
| IT-20 | `test_file_path_traversal_protected` | High | `?path=../etc/passwd` → 400/404 |

---

## 五、L4: E2E 测试

现有 `tests/ui_core_flow_test.py` 覆盖核心流程。

---

## 六、静态代码分析

### 6.1 Python (mypy + ruff)

| 工具 | 用途 | 配置 |
|---|---|---|
| `mypy` | 类型检查 | `--strict` 排除 agent_engine（deepagents 无类型标注） |
| `ruff` | Linting + 格式化 | 替代 flake8/isort/black |
| `pytest-cov` | 覆盖率 | `--cov=backend --cov-report=term-missing` |

### 6.2 TypeScript (tsc + ESLint)

| 工具 | 用途 | 配置 |
|---|---|---|
| `typescript` | 类型检查 | `tsconfig.json` 严格模式 |
| `vitest` | 前端测试框架 | 与 Vite 共享 transform 配置 |

---

## 七、覆盖率目标

| 模块 | 目标 | 测量方式 |
|---|---|---|
| `backend/core/` | 95%+ | pytest-cov |
| `backend/services/*/schemas.py` | 100% | pytest-cov |
| `backend/services/*/service.py` | 85%+ | pytest-cov |
| `backend/services/*/repository.py` | 80%+ | 集成测试间接覆盖 |
| `backend/middleware/` | 80%+ | pytest-cov |
| `agent_engine/discussion/orchestrator.py` | 70%+ | pytest-cov |
| `frontend/src/app/api/` | 80%+ | vitest |
| `frontend/src/app/store/` | 80%+ | vitest |
