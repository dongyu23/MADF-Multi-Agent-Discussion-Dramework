<template>
  <div class="dashboard-page">
    <div class="welcome-section">
      <h2 class="welcome-title">欢迎回来，{{ authStore.user?.username || '用户' }}</h2>
      <p class="welcome-subtitle">这里是 MADF 协作枢纽，随时随地开启智能讨论。</p>
    </div>

    <a-row :gutter="[24, 24]">
      <a-col :xs="24" :lg="16">
        <a-card title="活跃的圆桌论坛" :bordered="false" class="dashboard-card">
          <template #extra>
            <router-link to="/forums">查看全部</router-link>
          </template>
          
          <div v-if="forumStore.loading" class="state-container">
            <a-spin />
          </div>
          
          <div v-else-if="forumStore.forums.length === 0" class="state-container">
            <a-empty description="暂无活跃的讨论组" />
          </div>
          
          <a-list
            v-else
            item-layout="horizontal"
            :data-source="forumStore.forums.slice(0, 5)"
          >
            <template #renderItem="{ item }">
              <a-list-item class="list-item-hover">
                <template #actions>
                  <a @click="$router.push(`/forums/${item.id}`)">进入</a>
                </template>
                <a-list-item-meta :description="`创建时间：${new Date(item.start_time).toLocaleDateString()}`">
                  <template #title>
                    <a @click="$router.push(`/forums/${item.id}`)" class="item-title">{{ item.topic }}</a>
                  </template>
                  <template #avatar>
                    <a-avatar style="background-color: #1677ff">{{ item.topic[0] }}</a-avatar>
                  </template>
                </a-list-item-meta>
                <div>
                   <a-tag :color="item.status === 'active' ? 'processing' : 'default'">
                     {{ item.status === 'active' ? '进行中' : '已结束' }}
                   </a-tag>
                </div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="8">
        <div class="side-column">
          <a-card title="快捷操作" :bordered="false" class="dashboard-card">
            <div class="quick-actions">
              <a-button type="primary" block @click="$router.push('/personas')" class="action-btn">
                创建智能体
              </a-button>
              <a-button block @click="$router.push('/forums')" class="action-btn">
                发起新讨论
              </a-button>
            </div>
          </a-card>

          <a-card title="我的智能体" :bordered="false" class="dashboard-card">
            <template #extra>
              <router-link to="/personas">管理</router-link>
            </template>
            <div class="persona-mini-list">
              <div v-if="personaStore.loading" class="state-container-small">
                <a-spin size="small" />
              </div>
              <div v-else-if="personaStore.personas.length === 0" class="state-container-small">
                暂无智能体
              </div>
              <template v-else>
                <div v-for="p in personaStore.personas.slice(0, 4)" :key="p.id" class="persona-item">
                  <a-avatar size="small" style="background-color: #7265e6">{{ p.name[0] }}</a-avatar>
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
  padding: 24px;
}

.welcome-section {
  margin-bottom: 32px;
}

.welcome-title {
  font-size: 24px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 8px;
}

.welcome-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
}

.dashboard-card {
  height: 100%;
}

.state-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.state-container-small {
  text-align: center;
  padding: 24px 0;
  color: rgba(255, 255, 255, 0.45);
}

.list-item-hover {
  transition: background-color 0.3s;
  padding: 16px 24px;
  margin: 0 -24px;
}

.list-item-hover:hover {
  background-color: rgba(255, 255, 255, 0.04);
}

.item-title {
  font-size: 15px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
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
  height: 40px;
  font-size: 14px;
}

.persona-mini-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.persona-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  transition: background-color 0.3s;
}

.persona-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.persona-name {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
}

@media (max-width: 576px) {
  .dashboard-page {
    padding: 16px;
  }
}
</style>
