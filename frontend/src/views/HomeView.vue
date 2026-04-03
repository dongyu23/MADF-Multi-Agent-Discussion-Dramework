<template>
  <div class="dashboard-page">
    <div class="welcome-section">
      <h2 class="welcome-title">欢迎，{{ authStore.user?.username || '访客' }}</h2>
      <p class="welcome-subtitle">MADF 多智能体协作枢纽 <span>系统已就绪</span></p>
      <div class="glow-line"></div>
    </div>

    <a-row :gutter="[32, 32]" class="content-grid">
      <a-col :xs="24" :lg="15" class="left-panel">
        <a-card title="活跃讨论组" :bordered="false" class="dashboard-card main-card">
            <template #extra>
              <router-link to="/forums" class="modern-link">查看全部 ➔</router-link>
            </template>
            
            <div v-if="forumStore.loading" class="modern-loader">
              <a-spin />
            </div>
            
            <div v-else-if="forumStore.forums.length === 0" class="modern-empty">
              <a-empty description="暂无活跃的讨论组" />
            </div>
            
            <a-list
              v-else
              item-layout="horizontal"
              :data-source="forumStore.forums.slice(0, 5)"
              class="modern-list"
            >
              <template #renderItem="{ item }">
                <a-list-item class="modern-list-item">
                  <template #actions>
                    <a @click="$router.push(`/forums/${item.id}`)" class="action-enter">进入</a>
                  </template>
                  <a-list-item-meta :description="`创建时间：${new Date(item.start_time).toLocaleDateString()}`">
                    <template #title>
                      <a @click="$router.push(`/forums/${item.id}`)" class="list-item-title">{{ item.topic }}</a>
                    </template>
                    <template #avatar>
                      <div class="modern-avatar">{{ item.topic[0] }}</div>
                    </template>
                  </a-list-item-meta>
                  <div class="status-tag">
                     <a-tag :color="item.status === 'active' ? 'processing' : 'default'" class="custom-tag">
                       {{ item.status === 'active' ? '进行中' : '已结束' }}
                     </a-tag>
                  </div>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
      </a-col>

      <a-col :xs="24" :lg="9" class="right-panel">
        <div class="side-column">
          <a-card title="快捷操作" :bordered="false" class="dashboard-card command-card">
            <div class="quick-actions">
              <a-button type="primary" block @click="$router.push('/personas')" class="action-btn primary-modern">
                创建新智能体
              </a-button>
              <a-button block @click="$router.push('/forums')" class="action-btn secondary-modern">
                发起新讨论
              </a-button>
              <a-button block danger @click="authStore.logout()" class="action-btn danger-modern">
                退出登录
              </a-button>
            </div>
          </a-card>

          <a-card title="我的智能体" :bordered="false" class="dashboard-card entities-card">
            <template #extra><router-link to="/personas" class="modern-link">管理 ➔</router-link></template>
            <div class="persona-mini-list">
              <div v-if="personaStore.loading" class="modern-loader">
                <a-spin size="small" />
              </div>
              <div v-else-if="personaStore.personas.length === 0" class="modern-empty">
                暂无智能体
              </div>
              <template v-else>
                <div v-for="p in personaStore.personas.slice(0, 4)" :key="p.id" class="persona-item">
                  <div class="modern-avatar small">{{ p.name[0] }}</div>
                  <span class="persona-name">{{ p.name }}</span>
                </div>
              </template>
            </div>
          </a-card>
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'

const authStore = useAuthStore()
const forumStore = useForumStore()
const personaStore = usePersonaStore()

onMounted(() => {
  forumStore.fetchForums()
  personaStore.fetchPersonas(authStore.user?.id)
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px;
  min-height: 100vh;
  background-color: #0d0d12;
}

.welcome-section {
  margin-bottom: 48px;
  position: relative;
}

.welcome-title {
  font-size: 32px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.welcome-subtitle {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.45);
  letter-spacing: 0.5px;
}

.welcome-subtitle span {
  color: #1890ff;
  font-weight: 500;
}

.glow-line {
  height: 2px;
  background: linear-gradient(90deg, #1890ff, transparent);
  width: 60px;
  margin-top: 16px;
  border-radius: 2px;
}

.dashboard-card {
  background: rgba(25, 25, 35, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.dashboard-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}

:deep(.ant-card-head) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0 24px;
  min-height: 56px;
}

:deep(.ant-card-head-title) {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.main-card {
  min-height: 450px;
}

.modern-link {
  color: #1890ff;
  font-size: 14px;
  text-decoration: none;
  transition: color 0.3s;
}

.modern-link:hover {
  color: #40a9ff;
}

.modern-list-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
  padding: 20px 24px !important;
  transition: background 0.3s ease;
}

.modern-list-item:hover {
  background: rgba(255, 255, 255, 0.02);
}

.list-item-title {
  font-size: 16px;
  font-weight: 500;
  color: #ffffff !important;
  transition: color 0.3s ease;
}

.list-item-title:hover {
  color: #1890ff !important;
}

:deep(.ant-list-item-meta-description) {
  color: rgba(255, 255, 255, 0.45) !important;
  font-size: 13px;
  margin-top: 4px;
}

.action-enter {
  color: #1890ff;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  background: rgba(24, 144, 255, 0.1);
  transition: all 0.3s ease;
}

.action-enter:hover {
  background: rgba(24, 144, 255, 0.2);
}

.modern-avatar {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border-radius: 12px;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

.modern-avatar.small {
  width: 36px;
  height: 36px;
  font-size: 16px;
  border-radius: 10px;
}

.custom-tag {
  border-radius: 4px;
  padding: 2px 8px;
  border: none;
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-btn {
  height: 44px;
  font-size: 15px;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.primary-modern {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

.primary-modern:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(24, 144, 255, 0.4);
}

.secondary-modern {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.secondary-modern:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.danger-modern {
  background: transparent;
  border: 1px solid rgba(255, 77, 79, 0.3);
  color: #ff4d4f;
}

.danger-modern:hover {
  background: rgba(255, 77, 79, 0.1);
  border-color: #ff4d4f;
  color: #ff4d4f;
}

.persona-mini-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.persona-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.persona-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  transform: translateX(4px);
}

.persona-name {
  font-size: 14px;
  color: #ffffff;
  font-weight: 500;
}

.modern-loader, .modern-empty {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.45);
}

@media (max-width: 576px) {
  .dashboard-page {
    padding: 24px 16px;
  }
  .welcome-title {
    font-size: 24px;
  }
  .status-tag {
    display: none;
  }
}
</style>
