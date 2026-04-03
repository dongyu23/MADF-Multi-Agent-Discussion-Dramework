<template>
  <div class="forum-detail-container">
    <div class="forum-header">
      <div class="header-left">
        <a-button @click="goBack" type="text">
          <arrow-left-outlined />
        </a-button>
        <span class="forum-topic">{{ forumStore.currentForum?.topic }}</span>
        <a-tag color="warning" v-if="forumStore.currentForum?.status === 'pending'">未开始</a-tag>
        <a-tag color="processing" v-if="forumStore.currentForum?.status === 'running'">进行中</a-tag>
        <a-tag color="default" v-if="forumStore.currentForum?.status === 'closed' || forumStore.currentForum?.status === 'finished'">已结束</a-tag>
      </div>
      <div class="header-right">
        <a-space>
             <a-button 
                v-if="forumStore.currentForum?.status === 'pending'" 
                type="primary" 
                @click="handleStart"
                :loading="starting"
            >
                <play-circle-outlined /> 开始论坛
            </a-button>
            <a-button @click="showParticipantModal">
              <team-outlined /> 查看参与者
            </a-button>
            <a-popconfirm title="确定删除该论坛吗？" @confirm="handleDelete">
                <a-button danger>
                    <delete-outlined /> 删除
                </a-button>
            </a-popconfirm>
            <a-button @click="showSystemLogModal">
              <code-outlined /> 系统运行日志
            </a-button>
        </a-space>
      </div>
    </div>
    
    <MessageList 
      :messages="forumStore.messages" 
      :loading="forumStore.loading" 
    />
    
    <div class="chat-input-area" v-if="forumStore.currentForum?.status === 'running'">
      <div class="input-wrapper">
        <a-input-search
          v-model:value="userMessage"
          placeholder="作为观众发送消息..."
          enter-button="发送"
          size="large"
          @search="handleUserSend"
          :loading="sendingUserMessage"
        >
            <template #prefix>
                <user-outlined style="color: rgba(0,0,0,.25)" />
            </template>
        </a-input-search>
      </div>
    </div>
    
    <ForumTimer 
      v-if="forumStore.currentForum"
      :start-time="forumStore.currentForum.start_time || ''"
      :duration-minutes="forumStore.currentForum?.duration_minutes || 30" 
      :status="forumStore.currentForum?.status || 'pending'"
    />

    <!-- Participant Modal -->
    <a-modal
      v-model:open="isParticipantModalVisible"
      title="参与者列表"
      width="900px"
      :footer="null"
    >
      <div class="modal-content">
        <div class="modal-section">
          <ParticipantList />
        </div>
      </div>
    </a-modal>

    <!-- System Log Modal -->
    <a-modal
      v-model:open="isSystemLogModalVisible"
      title="系统运行日志"
      width="800px"
      :footer="null"
    >
      <div class="modal-content">
        <div class="modal-section">
          <SystemLogConsole />
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { useForumWebSocket } from '@/composables/useForumWebSocket'
import MessageList from '@/components/forum/MessageList.vue'
import ForumTimer from '@/components/forum/ForumTimer.vue'
import ParticipantList from '@/components/forum/ParticipantList.vue'
import SystemLogConsole from '@/components/forum/SystemLogConsole.vue'
import { 
  ArrowLeftOutlined, 
  TeamOutlined, 
  DeleteOutlined, 
  PlayCircleOutlined, 
  CodeOutlined, 
  UserOutlined, 
  PauseCircleOutlined
} from '@ant-design/icons-vue'

import { message } from 'ant-design-vue'
import request from '@/utils/request' // Import request

const route = useRoute()
const forumStore = useForumStore()
const personaStore = usePersonaStore()
const authStore = useAuthStore()
const router = useRouter()

const starting = ref(false)
const sendingUserMessage = ref(false)
const userMessage = ref('')
const isParticipantModalVisible = ref(false)
const isSystemLogModalVisible = ref(false)
const forumId = Number(route.params.id)
const { connect, disconnect, isConnected } = useForumWebSocket(forumId)

const handleUserSend = async () => {
    if (!userMessage.value.trim()) return
    
    sendingUserMessage.value = true
    try {
        await request.post(`/forums/${forumId}/chat`, {
            content: userMessage.value,
            speaker: authStore.user?.username || '观众'
        })
        userMessage.value = ''
        message.success('发送成功')
    } catch (e) {
        message.error('发送失败')
    } finally {
        sendingUserMessage.value = false
    }
}

const showParticipantModal = () => {
  isParticipantModalVisible.value = true
}

const showSystemLogModal = () => {
  isSystemLogModalVisible.value = true
}

const goBack = () => {
    router.push('/forums')
}

onMounted(async () => {
  // Use a local flag to track if component is still mounted
  let isMounted = true
  
  // Cleanup function for this specific mount
  onUnmounted(() => {
    isMounted = false
    // We don't call disconnect() here as per requirements to keep connection alive
    // But we might want to save state
    forumStore.leaveForum()
  })
  
  try {
    // 1. Initial Load: Use store to fetch data (this handles cache internally)
    await forumStore.fetchForum(forumId)
    
    if (!isMounted) return

    // 2. Validate forum existence
    if (!forumStore.currentForum) {
         message.error('论坛不存在或加载失败')
         router.push('/forums')
         return
    }
    
    // 3. Background: Load participant info context (non-blocking)
    personaStore.fetchPersonas(authStore.user?.id).catch(e => console.warn('Persona fetch failed', e))
    
    // 4. Background: Connect WS (non-blocking)
    // IMPORTANT: Check if WS is already connected for THIS forum
    // If not, connect. If yes, maybe just refresh messages?
    // connect() inside useForumWebSocket already handles idempotency
    try {
        await connect()
    } catch (e) {
        console.error('WS Connect error:', e)
    }

  } catch (e) {
    console.error('Failed to load forum details', e)
  } finally {
    if (isMounted) {
      forumStore.loading = false
    }
  }
})

// Remove the separate onUnmounted hook to avoid double cleanup/disconnect
// onUnmounted(() => {
//   disconnect()
// })

const handleDelete = async () => {
    try {
        await forumStore.deleteForum(forumId)
        message.success('论坛已删除')
        router.push('/forums')
    } catch (e: any) {
        // If 404, it's already deleted
        if (e.response && e.response.status === 404) {
             message.success('论坛已删除')
             router.push('/forums')
        } else {
             message.error('删除失败')
        }
    }
}

const handleStart = async () => {
    if (!forumStore.currentForum) return
    
    starting.value = true
    try {
        // Ensure WebSocket is connected BEFORE starting the forum task
        if (!isConnected.value) {
            await connect()
        }
        await forumStore.startForum(forumId)
        // fetchMessages is called by connect() on open, but good to ensure
        await forumStore.fetchMessages(forumId)
    } catch (e) {
        console.error('Start failed', e)
    } finally {
        starting.value = false
    }
}

const handleStop = async () => {
    if (!forumStore.currentForum) return
    try {
        await forumStore.stopForum(forumId)
    } catch (e) {
        console.error('Stop failed', e)
    }
}
</script>

<style scoped>
.forum-detail-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #0B0B0C;
  position: relative;
  z-index: 1;
}

.forum-detail-container::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(24, 144, 255, 0.02) 2px,
    rgba(24, 144, 255, 0.02) 4px
  );
  z-index: -1;
  pointer-events: none;
}

.forum-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #141414;
  border-bottom: 1px solid #D4AF37;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
  backdrop-filter: blur(10px);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.forum-topic {
  font-weight: 600;
  font-size: 24px;
  font-weight: bold;
  color: #1890ff;
  letter-spacing: 2px;
  text-transform: uppercase;
}

:deep(.ant-tag) {
  font-size: 14px;
  font-size: 10px;
  border-radius: 8px;
  padding: 2px 8px;
  border: 1px solid;
  letter-spacing: 1px;
}

.header-right :deep(.ant-btn) {
  font-size: 14px;
  border-radius: 8px;
  letter-spacing: 1px;
  background: transparent;
  color: #F2E8CF;
  border: 1px solid #333;
}

.header-right :deep(.ant-btn-primary) {
  border-color: #1890ff;
  color: #1890ff;
}

.header-right :deep(.ant-btn-primary:hover) {
  background: rgba(24, 144, 255, 0.1);
  color: #FFF;
  border-color: #FFF;
  box-shadow: 0 0 10px rgba(24, 144, 255, 0.4);
}

.header-right :deep(.ant-btn-dangerous) {
  border-color: #e63946;
  color: #e63946;
}

.header-right :deep(.ant-btn-dangerous:hover) {
  background: rgba(230, 57, 70, 0.1);
  color: #FFF;
  border-color: #FFF;
  box-shadow: 0 0 10px rgba(230, 57, 70, 0.4);
}

.chat-input-area {
  padding: 24px;
  background: #141414;
  border-top: 1px solid #D4AF37;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.input-wrapper {
  max-width: 1000px;
  margin: 0 auto;
}

:deep(.ant-input-search .ant-input) {
  background: rgba(0,0,0,0.5) !important;
  border: 1px solid #333 !important;
  color: #F2E8CF !important;
  font-family: 'Azeret Mono', monospace !important;
  border-radius: 8px !important;
}

:deep(.ant-input-search .ant-input:focus) {
  border-color: #D4AF37 !important;
  box-shadow: 0 0 10px rgba(24, 144, 255, 0.2) !important;
}

:deep(.ant-input-search-button) {
  background: transparent !important;
  border: 1px solid #D4AF37 !important;
  color: #D4AF37 !important;
  border-radius: 8px !important;
  font-family: 'Azeret Mono', monospace !important;
  transition: all 0.3s;
}

:deep(.ant-input-search-button:hover) {
  background: rgba(24, 144, 255, 0.1) !important;
  color: #FFF !important;
  border-color: #FFF !important;
  box-shadow: 0 0 10px rgba(24, 144, 255, 0.4) !important;
}

.participant-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.participant-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  border: 1px solid #222;
  background: rgba(0,0,0,0.3);
}

.p-name {
  font-weight: 600;
  font-size: 18px;
  font-weight: bold;
  color: #1890ff;
  letter-spacing: 1px;
}

.p-role {
  font-size: 14px;
  font-size: 10px;
  border: 1px solid #1890ff;
  color: #1890ff;
  padding: 2px 6px;
  background: rgba(24, 144, 255, 0.1);
}

.system-log-terminal {
  background-color: #050505;
  color: #4CAF50;
  font-size: 14px;
  padding: 16px;
  height: 400px;
  overflow-y: auto;
  border: 1px solid #333;
}

.log-line {
  margin-bottom: 8px;
  line-height: 1.4;
  font-size: 12px;
  border-bottom: 1px dashed #111;
  padding-bottom: 4px;
}

.log-time {
  color: #888;
  margin-right: 12px;
}

.log-level {
  display: inline-block;
  width: 50px;
  font-weight: bold;
}

.level-info { color: #1890ff; }
.level-warning { color: #faad14; }
.level-error { color: #f5222d; }
.level-debug { color: #888; }
.level-success { color: #52c41a; }

.log-content {
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-word;
}

:deep(.ant-modal-content) {
  background: #111 !important;
  border: 1px solid #D4AF37 !important;
  border-radius: 8px !important;
}

:deep(.ant-modal-header) {
  background: transparent !important;
  border-bottom: 1px solid #333 !important;
}

:deep(.ant-modal-title) {
  color: #D4AF37 !important;
  font-family: 'Cormorant Garamond', serif !important;
  font-size: 24px !important;
  letter-spacing: 2px !important;
}

:deep(.ant-modal-close-x) {
  color: #D4AF37 !important;
}
</style>
