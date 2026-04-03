<template>
  <div class="dashboard-wrapper">
    <div class="dashboard-hero">
      <div class="hero-content">
        <h1 class="hero-title">构建下一代多智能体系统</h1>
        <p class="hero-subtitle">欢迎回来，{{ authStore.user?.username || '用户' }}。您可以通过配置不同背景的虚拟智能体，观察他们在特定话题下的多维思想碰撞。</p>
        <div class="hero-actions">
          <a-button type="primary" size="large" class="create-btn" @click="$router.push('/forums')">
            <plus-outlined /> 发起新讨论
          </a-button>
          <a-button size="large" class="manage-btn" @click="$router.push('/personas')">
            <team-outlined /> 管理智能体
          </a-button>
        </div>
      </div>
      <div class="hero-illustration">
        <div class="orbit">
          <div class="planet p1"></div>
          <div class="planet p2"></div>
          <div class="planet p3"></div>
          <div class="center-core">MADF</div>
        </div>
      </div>
    </div>

    <div class="dashboard-stats">
      <div class="stat-card">
        <div class="stat-icon forums-icon"><comment-outlined /></div>
        <div class="stat-info">
          <div class="stat-value">{{ forumStore.forums.length }}</div>
          <div class="stat-label">总计讨论组</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon active-icon"><play-circle-outlined /></div>
        <div class="stat-info">
          <div class="stat-value">{{ activeForumsCount }}</div>
          <div class="stat-label">正在进行中</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon agents-icon"><team-outlined /></div>
        <div class="stat-info">
          <div class="stat-value">{{ personaStore.personas.length }}</div>
          <div class="stat-label">可用智能体</div>
        </div>
      </div>
    </div>

    <div class="dashboard-sections">
      <div class="section-main">
        <div class="section-header">
          <h3>最近活跃的讨论组</h3>
          <router-link to="/forums" class="view-all">查看全部 ➔</router-link>
        </div>
        
        <div class="forum-cards-grid">
          <div v-if="forumStore.loading" class="empty-state">
            <a-spin />
          </div>
          <div v-else-if="forumStore.forums.length === 0" class="empty-state">
            <div class="empty-icon"><comment-outlined /></div>
            <p>暂无活跃的讨论组</p>
            <a-button type="primary" ghost @click="$router.push('/forums')">创建第一个讨论</a-button>
          </div>
          
          <div 
            v-else 
            v-for="item in forumStore.forums.slice(0, 4)" 
            :key="item.id" 
            class="forum-glass-card"
            @click="$router.push(`/forums/${item.id}`)"
          >
            <div class="card-top">
              <div class="forum-icon">{{ item.topic[0] }}</div>
              <a-tag :color="item.status === 'active' ? 'processing' : 'default'" class="status-pill">
                {{ item.status === 'active' ? '进行中' : '已结束' }}
              </a-tag>
            </div>
            <h4 class="forum-topic">{{ item.topic }}</h4>
            <div class="forum-meta">
              <span><calendar-outlined /> {{ new Date(item.start_time).toLocaleDateString() }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="section-side">
        <div class="section-header">
          <h3>最近使用的智能体</h3>
          <router-link to="/personas" class="view-all">管理 ➔</router-link>
        </div>
        
        <div class="agent-list">
          <div v-if="personaStore.loading" class="empty-state small">
            <a-spin size="small" />
          </div>
          <div v-else-if="personaStore.personas.length === 0" class="empty-state small">
            暂无智能体数据
          </div>
          <div 
            v-else 
            v-for="p in personaStore.personas.slice(0, 5)" 
            :key="p.id" 
            class="agent-list-item"
          >
            <div class="agent-avatar">{{ p.name[0] }}</div>
            <div class="agent-info">
              <div class="agent-name">{{ p.name }}</div>
              <div class="agent-desc">{{ p.description || '无详细描述' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { 
  PlusOutlined, 
  TeamOutlined, 
  CommentOutlined, 
  PlayCircleOutlined,
  CalendarOutlined
} from '@ant-design/icons-vue'

const authStore = useAuthStore()
const forumStore = useForumStore()
const personaStore = usePersonaStore()

const activeForumsCount = computed(() => {
  return forumStore.forums.filter(f => f.status === 'active').length
})

onMounted(() => {
  forumStore.fetchForums()
  personaStore.fetchPersonas(authStore.user?.id)
})
</script>

<style scoped>
.dashboard-wrapper {
  display: flex;
  flex-direction: column;
  gap: 32px;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Hero Section */
.dashboard-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, rgba(22, 119, 255, 0.1) 0%, rgba(20, 20, 20, 0) 100%);
  border: 1px solid rgba(22, 119, 255, 0.2);
  border-radius: 16px;
  padding: 48px 64px;
  position: relative;
  overflow: hidden;
}

.hero-content {
  max-width: 600px;
  z-index: 2;
}

.hero-title {
  font-size: 36px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}

.hero-subtitle {
  font-size: 16px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.65);
  margin-bottom: 32px;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.create-btn {
  height: 48px;
  padding: 0 32px;
  font-size: 16px;
  font-weight: 500;
  box-shadow: 0 8px 16px rgba(22, 119, 255, 0.25);
}

.manage-btn {
  height: 48px;
  padding: 0 32px;
  font-size: 16px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.manage-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

/* Abstract Hero Illustration */
.hero-illustration {
  position: absolute;
  right: 10%;
  top: 50%;
  transform: translateY(-50%);
  width: 300px;
  height: 300px;
  z-index: 1;
  opacity: 0.8;
}

.orbit {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 1px dashed rgba(22, 119, 255, 0.3);
  animation: rotate 20s linear infinite;
}

.center-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  background: radial-gradient(circle, #1677ff 0%, transparent 70%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: white;
  font-size: 18px;
  box-shadow: 0 0 30px rgba(22, 119, 255, 0.4);
  animation: reverse-rotate 20s linear infinite;
}

.planet {
  position: absolute;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.5);
}

.p1 { width: 16px; height: 16px; top: -8px; left: 50%; background: #36cfc9; }
.p2 { width: 12px; height: 12px; bottom: 20%; right: -6px; background: #722ed1; }
.p3 { width: 20px; height: 20px; bottom: 10%; left: 10%; background: #eb2f96; }

@keyframes rotate { 100% { transform: rotate(360deg); } }
@keyframes reverse-rotate { 100% { transform: translate(-50%, -50%) rotate(-360deg); } }

/* Stats Row */
.dashboard-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.stat-card {
  background: rgba(25, 25, 35, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  background: rgba(25, 25, 35, 0.8);
  border-color: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.forums-icon { background: rgba(22, 119, 255, 0.1); color: #1677ff; }
.active-icon { background: rgba(82, 196, 26, 0.1); color: #52c41a; }
.agents-icon { background: rgba(114, 46, 209, 0.1); color: #722ed1; }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
  font-weight: 500;
}

/* Main Content Sections */
.dashboard-sections {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.view-all {
  color: #1677ff;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
}

.view-all:hover {
  color: #4096ff;
}

/* Forum Grid */
.forum-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.forum-glass-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.forum-glass-card:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(22, 119, 255, 0.3);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  transform: translateY(-4px);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.forum-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2b323b 0%, #141414 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  color: #ffffff;
}

.status-pill {
  border-radius: 12px;
  padding: 2px 10px;
  border: none;
  font-weight: 500;
}

.forum-topic {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  margin: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.forum-meta {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: auto;
}

/* Agent List */
.agent-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-list-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.agent-list-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

.agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #2b323b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 4px;
}

.agent-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  background: rgba(255, 255, 255, 0.01);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.empty-state.small {
  padding: 32px 0;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 16px;
  opacity: 0.5;
}

@media (max-width: 1024px) {
  .dashboard-sections {
    grid-template-columns: 1fr;
  }
  .hero-illustration {
    display: none;
  }
}

@media (max-width: 768px) {
  .dashboard-hero {
    padding: 32px 24px;
  }
  .dashboard-stats {
    grid-template-columns: 1fr;
  }
  .forum-cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>
