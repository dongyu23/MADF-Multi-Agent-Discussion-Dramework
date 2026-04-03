<template>
  <div class="auth-box">
    <div class="auth-header">
      <h2 class="auth-title">登录系统</h2>
      <p class="auth-subtitle">请输入您的凭据以继续</p>
    </div>

    <a-alert
      v-if="authStore.error"
      :message="authStore.error"
      type="error"
      show-icon
      closable
      style="margin-bottom: 24px"
      @close="authStore.error = null"
    />

    <a-form
      layout="vertical"
      :model="formState"
      @finish="onFinish"
      hide-required-mark
    >
      <a-form-item name="username">
        <a-input
          v-model:value="formState.username"
          size="large"
          placeholder="用户名"
        >
          <template #prefix>
            <user-outlined style="color: rgba(255, 255, 255, 0.45)" />
          </template>
        </a-input>
      </a-form-item>

      <a-form-item name="password" style="margin-bottom: 32px">
        <a-input-password
          v-model:value="formState.password"
          size="large"
          placeholder="密码"
        >
          <template #prefix>
            <lock-outlined style="color: rgba(255, 255, 255, 0.45)" />
          </template>
        </a-input-password>
      </a-form-item>

      <a-form-item>
        <a-button
          type="primary"
          html-type="submit"
          size="large"
          block
          :loading="authStore.loading"
        >
          登 录
        </a-button>
      </a-form-item>

      <div class="auth-footer">
        <span class="footer-text">还没有账号？</span>
        <router-link to="/auth/register" class="link-btn">立即注册</router-link>
      </div>

      <div class="disclaimer">
        <a-divider style="margin: 16px 0; border-color: rgba(255,255,255,0.1)">免责声明</a-divider>
        <p class="warning-text">
          <warning-outlined style="color: #faad14; margin-right: 4px;" />
          系统生成的 AI 角色发言可能包含虚构内容，不代表真实人物观点。仅供研究与演示使用。
        </p>
      </div>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { UserOutlined, LockOutlined, WarningOutlined } from '@ant-design/icons-vue'

const authStore = useAuthStore()
const formState = reactive({
  username: '',
  password: ''
})

const onFinish = async (values: any) => {
  await authStore.login(values)
}
</script>

<style scoped>
.auth-box {
  width: 100%;
  background: #1f1f1f;
  border-radius: 8px;
  padding: 32px 24px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-title {
  font-size: 24px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
}

.footer-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
}

.link-btn {
  color: #1677ff;
  font-size: 14px;
  margin-left: 8px;
  text-decoration: none;
}

.link-btn:hover {
  color: #4096ff;
}

.disclaimer {
  margin-top: 32px;
  text-align: center;
}

.warning-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.6;
  margin: 0;
  text-align: left;
}

:deep(.ant-divider-inner-text) {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.25);
}
</style>
