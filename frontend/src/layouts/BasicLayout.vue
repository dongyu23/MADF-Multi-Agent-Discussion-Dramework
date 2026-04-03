<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      theme="dark"
      breakpoint="lg"
      :width="240"
      class="sider-layout"
    >
      <div class="logo">
        <span v-if="!collapsed" class="logo-text">MADF</span>
        <span v-else class="logo-text">M</span>
      </div>
      <a-menu :selectedKeys="selectedKeys" theme="dark" mode="inline">
        <a-menu-item key="dashboard" @click="navigateTo('/dashboard')">
            <dashboard-outlined />
            <span>系统概览</span>
        </a-menu-item>

        <a-menu-item key="personas" @click="navigateTo('/personas')">
            <team-outlined />
            <span>智能体工坊</span>
        </a-menu-item>

        <a-menu-item key="forums" @click="navigateTo('/forums')">
            <comment-outlined />
            <span>圆桌论坛</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout class="site-layout">
      <a-layout-header class="site-layout-header">
        <div class="header-left">
          <!-- Can add breadcrumbs or title here if needed -->
        </div>
        <div class="header-right">
          <a-dropdown placement="bottomRight">
            <div class="user-action">
              <a-avatar style="background-color: #1677ff">
                <template #icon><user-outlined /></template>
              </a-avatar>
              <span class="username">{{ authStore.user?.username || '用户' }}</span>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="logout" @click="handleLogout">
                  <logout-outlined />
                  <span>退出登录</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout-content class="site-layout-content">
        <router-view />
      </a-layout-content>
    </a-layout>
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
  UserOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

const handleLogout = async () => {
  await authStore.logout()
  router.push('/auth/login')
}

const navigateTo = (path: string) => {
    router.push(path)
}

const selectedKeys = computed(() => {
  if (route.path === '/' || route.path.startsWith('/dashboard')) return ['dashboard']
  if (route.path.startsWith('/personas')) return ['personas']
  if (route.path.startsWith('/forums')) return ['forums']
  return []
})
</script>

<style scoped>
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  white-space: nowrap;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo-text {
  font-size: 20px;
  font-weight: bold;
  color: #1677ff;
  letter-spacing: 1px;
}

.sider-layout {
  z-index: 10;
  height: 100vh;
  box-shadow: 2px 0 8px 0 rgba(0, 0, 0, 0.15);
}

.site-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.site-layout-header {
  background: #141414;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  z-index: 9;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-action {
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 0 12px;
  transition: background 0.3s;
  height: 64px;
}

.user-action:hover {
  background: rgba(255, 255, 255, 0.05);
}

.username {
  margin-left: 8px;
  color: rgba(255, 255, 255, 0.85);
  font-weight: 500;
}

.site-layout-content {
  margin: 0;
  padding: 0;
  flex: 1;
  overflow: auto;
  background-color: #141414;
}
</style>
