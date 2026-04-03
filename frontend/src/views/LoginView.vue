<template>
  <div class="auth-wrapper">
    <div class="cyber-box">
      <div class="auth-header">
        <h1 class="auth-title">A R C H I V E</h1>
        <div class="auth-subtitle">IDENTIFICATION REQUIRED</div>
        <div class="glow-divider"></div>
      </div>

      <a-alert
        v-if="authStore.error"
        :message="authStore.error"
        type="error"
        show-icon
        closable
        class="cyber-alert"
        @close="authStore.error = null"
      />

      <a-form
        layout="vertical"
        :model="formState"
        @finish="onFinish"
        hide-required-mark
        class="auth-form"
      >
        <a-form-item name="username" class="cyber-form-item">
          <a-input
            v-model:value="formState.username"
            size="large"
            placeholder="[ ENTER_DESIGNATION ]"
            class="cyber-input"
          >
            <template #prefix>
              <span class="prefix-icon">_></span>
            </template>
          </a-input>
        </a-form-item>

        <a-form-item name="password" class="cyber-form-item">
          <a-input-password
            v-model:value="formState.password"
            size="large"
            placeholder="[ ENTER_CIPHER ]"
            class="cyber-input"
          >
            <template #prefix>
              <span class="prefix-icon">***</span>
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
            <span class="btn-text">AUTHENTICATE</span>
          </a-button>
        </a-form-item>

        <div class="auth-footer">
          <span class="footer-text">UNREGISTERED ENTITY?</span>
          <router-link to="/auth/register" class="link-btn">[ INITIATE_REGISTRATION ]</router-link>
        </div>

        <div class="disclaimer">
          <div class="warning-line"></div>
          <p class="warning-text">
            <warning-outlined style="color: #e63946; margin-right: 8px;" />
            WARNING: CONSTRUCTED PERSONAS MAY HALLUCINATE OR DEVIATE FROM HISTORICAL ACCURACY. 
            ENTER AT YOUR OWN EXISTENTIAL RISK.
          </p>
        </div>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { WarningOutlined } from '@ant-design/icons-vue'

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
.auth-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100vh;
  background: radial-gradient(circle at center, #1a1a24 0%, #0b0b0c 100%);
  position: relative;
  z-index: 1;
}

.auth-wrapper::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(212, 175, 55, 0.03) 2px,
    rgba(212, 175, 55, 0.03) 4px
  );
  z-index: -1;
}

.cyber-box {
  width: 100%;
  max-width: 480px;
  background: rgba(15, 15, 20, 0.85);
  border: 1px solid #D4AF37;
  padding: 40px;
  position: relative;
  box-shadow: 0 0 30px rgba(0,0,0,0.8), inset 0 0 20px rgba(212, 175, 55, 0.05);
  backdrop-filter: blur(5px);
}

.cyber-box::before, .cyber-box::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid #D4AF37;
}

.cyber-box::before { top: -2px; left: -2px; border-right: none; border-bottom: none; }
.cyber-box::after { bottom: -2px; right: -2px; border-left: none; border-top: none; }

.auth-header {
  text-align: center;
  margin-bottom: 40px;
}

.auth-title {
  font-family: 'Cormorant Garamond', serif;
  font-size: 48px;
  color: #D4AF37;
  margin: 0;
  letter-spacing: 8px;
  text-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
}

.auth-subtitle {
  font-family: 'Azeret Mono', monospace;
  font-size: 12px;
  color: #888;
  letter-spacing: 4px;
  margin-top: 10px;
}

.glow-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #D4AF37, transparent);
  margin-top: 20px;
  opacity: 0.5;
}

.cyber-form-item {
  margin-bottom: 24px;
}

:deep(.ant-input-affix-wrapper) {
  background: rgba(0,0,0,0.5) !important;
  border: 1px solid #333 !important;
  border-radius: 0 !important;
  padding: 8px 16px !important;
}

:deep(.ant-input-affix-wrapper-focused) {
  border-color: #D4AF37 !important;
  box-shadow: 0 0 10px rgba(212, 175, 55, 0.2) !important;
}

:deep(.ant-input) {
  background: transparent !important;
  color: #F2E8CF !important;
  font-family: 'Azeret Mono', monospace !important;
  letter-spacing: 1px;
}

:deep(.ant-input::placeholder) {
  color: #555 !important;
}

.prefix-icon {
  color: #D4AF37;
  font-family: 'Azeret Mono', monospace;
  font-weight: bold;
  margin-right: 8px;
}

.submit-btn {
  height: 50px;
  background: transparent;
  border: 1px solid #D4AF37;
  color: #D4AF37;
  border-radius: 0;
  margin-top: 16px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
}

.submit-btn:hover {
  background: rgba(212, 175, 55, 0.15);
  color: #FFF;
  border-color: #FFF;
  box-shadow: 0 0 20px rgba(212, 175, 55, 0.4);
}

.submit-btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transition: left 0.5s;
}

.submit-btn:hover::before {
  left: 100%;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
}

.footer-text {
  font-family: 'Azeret Mono', monospace;
  font-size: 11px;
  color: #666;
}

.link-btn {
  color: #D4AF37;
  font-family: 'Azeret Mono', monospace;
  font-size: 11px;
  margin-left: 8px;
  text-decoration: none;
  transition: color 0.3s, text-shadow 0.3s;
}

.link-btn:hover {
  color: #FFF;
  text-shadow: 0 0 8px #D4AF37;
}

.disclaimer {
  margin-top: 40px;
  text-align: center;
}

.warning-line {
  height: 1px;
  background: #e63946;
  opacity: 0.3;
  margin-bottom: 16px;
}

.warning-text {
  font-family: 'Azeret Mono', monospace;
  font-size: 10px;
  color: #888;
  line-height: 1.6;
  margin: 0;
}

.cyber-alert {
  background: rgba(230, 57, 70, 0.1);
  border: 1px solid #e63946;
  border-radius: 0;
  margin-bottom: 24px;
}

@media (max-width: 576px) {
  .cyber-box {
    border: none;
    box-shadow: none;
    padding: 20px;
  }
  .cyber-box::before, .cyber-box::after {
    display: none;
  }
}
</style>
