# 问题复现步骤文档

## 故障描述
当用户点击论坛页面上的按钮（如“登录”、“创建角色”、“创建讨论”）时，系统似乎无响应，或操作未生效。

## 1. 复现环境
- **操作系统**: Windows
- **前端**: Vue 3 + Vite
- **后端**: FastAPI + SQLite

## 2. 复现步骤 (Root Cause Analysis)

### 场景 A: 创建角色按钮失效 (Promise Error)
1. 打开论坛详情页 (`/forums/:id`)。
2. 该页面在加载时会调用 `personaStore.fetchPersonas`。
3. **关键点**: 如果 `fetchPersonas` 动作没有返回 Promise (例如在测试环境 mock 不当，或特定逻辑分支返回 `undefined`)，原本代码中的 `.catch(...)` 会抛出 `TypeError: Cannot read properties of undefined (reading 'catch')`。
4. **现象**: JS 执行中断，后续的事件绑定可能失效，或者页面渲染不完整，导致按钮无法点击。

### 场景 B: 创建公开角色权限错误 (Permission Denied)
1. 以普通用户身份登录。
2. 点击“创建新角色”按钮。
3. 在表单中勾选“公开”选项 (is_public=True)。
4. 点击“提交”按钮。
5. **现象**: 后端返回 403 Forbidden。如果前端没有显示错误消息，用户会认为按钮没有反应。

### 场景 C: 数据库锁定 (Database Locked)
1. 快速连续点击“开始讨论”按钮。
2. 后端尝试写入数据库状态。
3. **现象**: 日志中出现 `SQLITE_BUSY_RECOVERY: database is locked`。操作失败，状态未更新。

## 3. 验证修复

我们已通过以下测试验证修复方案：

1. **运行前端测试**:
   ```bash
   cd frontend
   npm run test:unit
   ```
   确保 `LoginView` 和 `ForumDetailView` 测试通过。

2. **运行后端测试**:
   ```bash
   python -m pytest app/tests/test_button_apis_v2.py
   ```
   确保 API 逻辑正确处理权限和状态变更。

3. **手动验证**:
   - 登录普通用户，创建私有角色（不勾选“公开”）。
   - 创建论坛并启动，观察状态是否变为“进行中”。
