<template>
  <a-layout class="madf-layout">
    <a-layout-header class="madf-header">
      <div class="header-container">
        <div class="logo-area" @click="navigateTo('/dashboard')">
          <div class="logo-icon">M</div>
          <span class="logo-text">MADF Platform</span>
        </div>
        
        <a-menu
          v-model:selectedKeys="selectedKeys"
          theme="dark"
          mode="horizontal"
          class="top-nav-menu"
          :selectable="false"
        >
          <a-menu-item key="dashboard" @click="navigateTo('/dashboard')" :class="{ 'active-menu': isActive('/dashboard') }">
            <dashboard-outlined /> 控制台
          </a-menu-item>
          <a-menu-item key="personas" @click="navigateTo('/personas')" :class="{ 'active-menu': isActive('/personas') }">
            <team-outlined /> 智能体库
          </a-menu-item>
          <a-menu-item key="forums" @click="navigateTo('/forums')" :class="{ 'active-menu': isActive('/forums') }">
            <comment-outlined /> 讨论空间
          </a-menu-item>
        </a-menu>

        <div class="user-area">
          <a-dropdown placement="bottomRight" :trigger="['click']">
            <div class="user-profile-btn">
              <a-avatar size="small" class="user-avatar">
                <template #icon><user-outlined /></template>
              </a-avatar>
              <span class="username">{{ authStore.user?.username || '用户' }}</span>
              <down-outlined class="dropdown-icon" />
            </div>
            <template #overlay>
              <a-menu class="user-dropdown-menu">
                <div class="dropdown-header">
                  <div class="dropdown-user">{{ authStore.user?.username }}</div>
                  <div class="dropdown-role">系统操作员</div>
                </div>
                <a-menu-divider />
                <a-menu-item key="logout" @click="handleLogout" class="logout-item">
                  <logout-outlined /> 退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>
    </a-layout-header>

    <a-layout-content class="madf-content">
      <div class="content-wrapper">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  DashboardOutlined,
  TeamOutlined,
  CommentOutlined,
  LogoutOutlined,
  UserOutlined,
  DownOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const handleLogout = async () => {
  await authStore.logout()
  router.push('/auth/login')
}

const navigateTo = (path: string) => {
  router.push(path)
}

const isActive = (path: string) => {
  if (path === '/dashboard') return route.path === '/' || route.path.startsWith('/dashboard')
  return route.path.startsWith(path)
}

const selectedKeys = computed(() => {
  if (route.path === '/' || route.path.startsWith('/dashboard')) return ['dashboard']
  if (route.path.startsWith('/personas')) return ['personas']
  if (route.path.startsWith('/forums')) return ['forums']
  return []
})
</script>

<style scoped>
.madf-layout {
  min-height: 100vh;
  background-color: #09090b; /* Very dark background */
}

.madf-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  height: 64px;
  padding: 0;
  background: rgba(9, 9, 11, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.header-container {
  max-width: 1440px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  margin-right: 48px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #1677ff 0%, #36cfc9 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 800;
  font-size: 18px;
  box-shadow: 0 0 15px rgba(22, 119, 255, 0.3);
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: -0.5px;
}

.top-nav-menu {
  flex: 1;
  background: transparent;
  border-bottom: none;
  line-height: 64px;
}

:deep(.ant-menu-dark.ant-menu-horizontal > .ant-menu-item) {
  padding: 0 20px;
  margin: 0 4px;
  border-radius: 8px;
  top: 0;
  margin-top: 12px;
  height: 40px;
  line-height: 40px;
  color: rgba(255, 255, 255, 0.65);
  transition: all 0.2s ease;
}

:deep(.ant-menu-dark.ant-menu-horizontal > .ant-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.active-menu {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: #ffffff !important;
  font-weight: 500;
}

:deep(.ant-menu-dark.ant-menu-horizontal > .ant-menu-item-selected) {
  background-color: transparent;
}

.user-area {
  display: flex;
  align-items: center;
}

.user-profile-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
}

.user-profile-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.user-avatar {
  background: #1677ff;
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.dropdown-icon {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
}

.dropdown-header {
  padding: 12px 16px;
  outline: none;
}

.dropdown-user {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
}

.dropdown-role {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  margin-top: 4px;
}

.logout-item {
  color: #ff4d4f !important;
}

.logout-item:hover {
  background-color: rgba(255, 77, 79, 0.1) !important;
}

.madf-content {
  display: flex;
  flex-direction: column;
}

.content-wrapper {
  flex: 1;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 32px;
}

/* Page transition animations */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 768px) {
  .header-container {
    padding: 0 16px;
  }
  
  .logo-text, .username {
    display: none;
  }
  
  .logo-area {
    margin-right: 16px;
  }
  
  .content-wrapper {
    padding: 16px;
  }
}
</style>
