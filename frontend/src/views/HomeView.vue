<template>
  <div class="dashboard-page">
    <div class="welcome-section">
      <h2 class="welcome-title">ARCHIVE OF SOULS // {{ authStore.user?.username?.toUpperCase() || 'GUEST' }}</h2>
      <p class="welcome-subtitle">Multidimensional Agent Discussion Framework | <span>SYSTEM ONLINE</span></p>
      <div class="glow-line"></div>
    </div>

    <a-row :gutter="[32, 32]" class="content-grid">
      <a-col :xs="24" :lg="15" class="left-panel">
        <a-card title="ACTIVE DISCOURSES" :bordered="false" class="dashboard-card main-card">
            <template #extra>
              <router-link to="/forums" class="neon-link">[ VIEW_ALL ]</router-link>
            </template>
            
            <div v-if="forumStore.loading" class="terminal-loader">
              <span class="blinking-cursor">LOADING_DATABANKS...</span>
            </div>
            
            <div v-else-if="forumStore.forums.length === 0" class="terminal-empty">
              <p>NO ACTIVE DISCOURSES FOUND.</p>
            </div>
            
            <a-list
              v-else
              item-layout="horizontal"
              :data-source="forumStore.forums.slice(0, 5)"
              class="cyber-list"
            >
              <template #renderItem="{ item }">
                <a-list-item class="cyber-list-item">
                  <template #actions>
                    <a @click="$router.push(`/forums/${item.id}`)" class="action-enter">ENTER_NEXUS</a>
                  </template>
                  <a-list-item-meta :description="`[INITIATED: ${new Date(item.start_time).toLocaleDateString()}]`">
                    <template #title>
                      <a @click="$router.push(`/forums/${item.id}`)" class="list-item-title">{{ item.topic.toUpperCase() }}</a>
                    </template>
                    <template #avatar>
                      <div class="cyber-avatar">{{ item.topic[0] }}</div>
                    </template>
                  </a-list-item-meta>
                  <div class="status-tag">
                     <span :class="['glitch-tag', item.status === 'active' ? 'active-tag' : 'ended-tag']">
                       {{ item.status === 'active' ? 'PROCESSING' : 'ARCHIVED' }}
                     </span>
                  </div>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
      </a-col>

      <a-col :xs="24" :lg="9" class="right-panel">
        <div class="side-column">
          <a-card title="COMMAND_UPLINK" :bordered="false" class="dashboard-card command-card">
            <div class="quick-actions">
              <a-button type="primary" block @click="$router.push('/personas')" class="action-btn primary-cyber">
                <span class="btn-text">CONSTRUCT_PERSONA</span>
              </a-button>
              <a-button block @click="$router.push('/forums')" class="action-btn secondary-cyber">
                <span class="btn-text">INITIATE_DISCOURSE</span>
              </a-button>
              <a-button block danger @click="authStore.logout()" class="action-btn danger-cyber">
                <span class="btn-text">SEVER_CONNECTION</span>
              </a-button>
            </div>
          </a-card>

          <a-card title="CONSTRUCTED_ENTITIES" :bordered="false" class="dashboard-card entities-card">
            <template #extra><router-link to="/personas" class="neon-link">[ MANAGE ]</router-link></template>
            <div class="persona-mini-list">
              <div v-if="personaStore.loading" class="terminal-loader">
                <span class="blinking-cursor">SYNCING...</span>
              </div>
              <div v-else-if="personaStore.personas.length === 0" class="terminal-empty">
                NO ENTITIES FOUND
              </div>
              <template v-else>
                <div v-for="p in personaStore.personas.slice(0, 4)" :key="p.id" class="persona-item">
                  <div class="cyber-avatar small">{{ p.name[0] }}</div>
                  <span class="persona-name">{{ p.name.toUpperCase() }}</span>
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
  max-width: 1300px;
  margin: 0 auto;
  padding: 40px 24px;
  min-height: 100vh;
  background: radial-gradient(circle at 50% 0%, #1a1a24 0%, #0b0b0c 100%);
  position: relative;
  z-index: 1;
}

/* Diagonal scanning line effect */
.dashboard-page::after {
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
  pointer-events: none;
}

.welcome-section {
  margin-bottom: 48px;
  position: relative;
  padding-left: 16px;
  border-left: 4px solid #D4AF37;
}

.welcome-title {
  font-size: 36px;
  font-weight: 700;
  color: #D4AF37;
  margin-bottom: 4px;
  text-shadow: 0 0 10px rgba(212, 175, 55, 0.3);
  letter-spacing: 2px;
}

.welcome-subtitle {
  font-family: 'Azeret Mono', monospace;
  font-size: 14px;
  color: #888899;
  letter-spacing: 1px;
}

.welcome-subtitle span {
  color: #4CAF50;
  animation: pulse 2s infinite;
}

.glow-line {
  height: 1px;
  background: linear-gradient(90deg, #D4AF37, transparent);
  width: 100%;
  margin-top: 16px;
  opacity: 0.5;
}

@keyframes pulse {
  0% { opacity: 0.5; }
  50% { opacity: 1; text-shadow: 0 0 8px #4CAF50; }
  100% { opacity: 0.5; }
}

.dashboard-card {
  background: rgba(15, 15, 20, 0.85);
  border: 1px solid #2a2a35;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  transition: transform 0.3s ease, border-color 0.3s ease;
  position: relative;
  overflow: hidden;
}

.dashboard-card:hover {
  transform: translateY(-2px);
  border-color: #D4AF37;
}

/* Corner accents */
.dashboard-card::before, .dashboard-card::after {
  content: '';
  position: absolute;
  width: 10px;
  height: 10px;
  border: 1px solid #D4AF37;
  transition: all 0.3s ease;
}
.dashboard-card::before { top: 0; left: 0; border-right: none; border-bottom: none; }
.dashboard-card::after { bottom: 0; right: 0; border-left: none; border-top: none; }

.main-card {
  min-height: 450px;
}

.neon-link {
  color: #D4AF37;
  font-family: 'Azeret Mono', monospace;
  font-size: 12px;
  letter-spacing: 1px;
  transition: all 0.3s;
}

.neon-link:hover {
  color: #FFF;
  text-shadow: 0 0 8px #D4AF37;
}

.cyber-list-item {
  border-bottom: 1px solid #222 !important;
  padding: 20px 16px !important;
  transition: background 0.3s;
}

.cyber-list-item:hover {
  background: rgba(212, 175, 55, 0.05);
}

.list-item-title {
  font-size: 16px;
  font-family: 'Cormorant Garamond', serif;
  font-weight: 700;
  color: #F2E8CF !important;
  letter-spacing: 1px;
}

.action-enter {
  color: #D4AF37;
  font-family: 'Azeret Mono', monospace;
  font-size: 12px;
  border: 1px solid #D4AF37;
  padding: 4px 8px;
  text-decoration: none;
  transition: all 0.3s;
}
.action-enter:hover {
  background: #D4AF37;
  color: #0B0B0C;
}

.cyber-avatar {
  width: 40px;
  height: 40px;
  background: #1a1a24;
  border: 1px solid #D4AF37;
  color: #D4AF37;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Cormorant Garamond', serif;
  font-size: 20px;
  font-weight: bold;
  transform: rotate(45deg);
}

.cyber-avatar.small {
  width: 32px;
  height: 32px;
  font-size: 16px;
}

.cyber-avatar > * {
  transform: rotate(-45deg);
}

.glitch-tag {
  font-family: 'Azeret Mono', monospace;
  font-size: 10px;
  padding: 2px 6px;
  letter-spacing: 1px;
  border: 1px solid;
}

.active-tag {
  color: #4CAF50;
  border-color: #4CAF50;
  box-shadow: 0 0 5px rgba(76, 175, 80, 0.2);
}

.ended-tag {
  color: #888;
  border-color: #555;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-btn {
  height: 48px;
  position: relative;
  overflow: hidden;
  background: transparent;
  border: 1px solid #333;
  color: #F2E8CF;
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
  transition: left 0.5s;
}

.action-btn:hover::before {
  left: 100%;
}

.primary-cyber {
  border-color: #D4AF37;
  color: #D4AF37;
}

.primary-cyber:hover {
  background: rgba(212, 175, 55, 0.1);
  color: #FFF;
  border-color: #FFF;
  box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
}

.danger-cyber {
  border-color: #e63946;
  color: #e63946;
}

.danger-cyber:hover {
  background: rgba(230, 57, 70, 0.1);
  color: #FFF;
  border-color: #FFF;
  box-shadow: 0 0 15px rgba(230, 57, 70, 0.4);
}

.persona-mini-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.persona-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  border: 1px solid #222;
  background: rgba(0,0,0,0.3);
  transition: all 0.3s;
}

.persona-item:hover {
  border-color: #D4AF37;
  transform: translateX(5px);
}

.persona-name {
  font-family: 'Azeret Mono', monospace;
  font-size: 13px;
  color: #F2E8CF;
  letter-spacing: 1px;
}

.terminal-loader, .terminal-empty {
  font-family: 'Azeret Mono', monospace;
  text-align: center;
  padding: 40px;
  color: #888;
}

.blinking-cursor::after {
  content: '_';
  animation: blink 1s step-start infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}
</style>
