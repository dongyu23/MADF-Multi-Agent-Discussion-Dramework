<template>
  <div class="auth-wrapper">
    <div class="glass-container">
      <div class="auth-header">
        <h1 class="auth-title">加入 MADF</h1>
        <div class="auth-subtitle">注册账号，开启多智能体协作之旅</div>
        <div class="accent-line"></div>
      </div>

      <a-alert
        v-if="authStore.error"
        :message="authStore.error"
        type="error"
        show-icon
        closable
        class="custom-alert"
        @close="authStore.error = null"
      />

      <a-form
        layout="vertical"
        :model="formState"
        @finish="onFinish"
        hide-required-mark
        class="auth-form"
      >
        <a-form-item
          name="username"
          class="custom-form-item"
          :rules="[{ required: true, message: '请输入用户名' }]"
        >
          <a-input
            v-model:value="formState.username"
            size="large"
            placeholder="请输入用户名"
            class="custom-input"
          >
            <template #prefix>
              <user-outlined class="input-icon" />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item
          name="password"
          class="custom-form-item"
          :rules="[{ required: true, message: '请输入密码' }]"
        >
          <a-input-password
            v-model:value="formState.password"
            size="large"
            placeholder="请输入密码"
            class="custom-input"
          >
            <template #prefix>
              <lock-outlined class="input-icon" />
            </template>
          </a-input-password>
        </a-form-item>

        <a-form-item
          name="confirmPassword"
          class="custom-form-item"
          :rules="[
            { required: true, message: '请确认密码' },
            { validator: validateConfirmPassword }
          ]"
        >
          <a-input-password
            v-model:value="formState.confirmPassword"
            size="large"
            placeholder="请确认密码"
            class="custom-input"
          >
            <template #prefix>
              <lock-outlined class="input-icon" />
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
            class="submit-btn"
          >
            注 册
          </a-button>
        </a-form-item>

        <div class="auth-footer">
          <span class="footer-text">已有账号？</span>
          <router-link to="/auth/login" class="link-btn">直接登录</router-link>
        </div>

        <div class="disclaimer">
          <div class="divider-line"></div>
          <p class="warning-text">
            <warning-outlined style="color: rgba(255, 255, 255, 0.45); margin-right: 8px;" />
            系统生成的 AI 角色发言可能包含虚构内容，不代表真实人物观点。本平台内容仅供研究与演示，请勿作为专业建议。
          </p>
        </div>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { UserOutlined, LockOutlined, WarningOutlined } from '@ant-design/icons-vue'
import type { Rule } from 'ant-design-vue/es/form'

const authStore = useAuthStore()
const formState = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = async (_rule: Rule, value: string) => {
  if (value !== formState.password) {
    return Promise.reject('两次输入的密码不一致')
  }
  return Promise.resolve()
}

const onFinish = async (values: any) => {
  await authStore.register(values)
}
</script>

<style scoped>
.auth-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100vh;
  background: radial-gradient(circle at top right, #1f1f2e 0%, #0d0d12 100%);
  position: relative;
}

.auth-wrapper::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 24px 24px;
  z-index: 0;
}

.glass-container {
  width: 100%;
  max-width: 440px;
  background: rgba(25, 25, 35, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 48px 40px;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.auth-header {
  text-align: center;
  margin-bottom: 40px;
}

.auth-title {
  font-size: 32px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
  letter-spacing: 2px;
}

.auth-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 1px;
}

.accent-line {
  height: 3px;
  width: 40px;
  background: #1890ff;
  margin: 20px auto 0;
  border-radius: 2px;
}

.custom-form-item {
  margin-bottom: 24px;
}

:deep(.ant-input-affix-wrapper) {
  background: rgba(0, 0, 0, 0.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 8px !important;
  padding: 10px 16px !important;
  transition: all 0.3s ease;
}

:deep(.ant-input-affix-wrapper-focused),
:deep(.ant-input-affix-wrapper:hover) {
  border-color: rgba(24, 144, 255, 0.6) !important;
  background: rgba(0, 0, 0, 0.3) !important;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1) !important;
}

:deep(.ant-input) {
  background: transparent !important;
  color: #ffffff !important;
  font-size: 15px !important;
}

:deep(.ant-input::placeholder) {
  color: rgba(255, 255, 255, 0.3) !important;
}

.input-icon {
  color: rgba(255, 255, 255, 0.4);
  font-size: 16px;
  margin-right: 8px;
}

:deep(.ant-input-affix-wrapper-focused) .input-icon {
  color: #1890ff;
}

.submit-btn {
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  margin-top: 8px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(24, 144, 255, 0.4);
  background: linear-gradient(135deg, #40a9ff 0%, #1890ff 100%);
}

.submit-btn:active {
  transform: translateY(1px);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
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
  color: #1890ff;
  font-size: 14px;
  margin-left: 8px;
  text-decoration: none;
  transition: color 0.3s;
}

.link-btn:hover {
  color: #40a9ff;
}

.disclaimer {
  margin-top: 32px;
  text-align: center;
}

.divider-line {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  margin-bottom: 20px;
}

.warning-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  line-height: 1.6;
  margin: 0;
  text-align: left;
  padding: 0 12px;
}

.custom-alert {
  background: rgba(255, 77, 79, 0.1);
  border: 1px solid rgba(255, 77, 79, 0.3);
  border-radius: 8px;
  margin-bottom: 24px;
}

:deep(.ant-alert-message) {
  color: #ff4d4f;
}

:deep(.ant-alert-icon) {
  color: #ff4d4f;
}

@media (max-width: 576px) {
  .glass-container {
    border-radius: 0;
    border: none;
    background: transparent;
    box-shadow: none;
    backdrop-filter: none;
    padding: 32px 24px;
  }
}
</style>
