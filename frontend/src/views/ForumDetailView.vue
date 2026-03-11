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
    
    <ForumTimer 
      v-if="forumStore.currentForum"
      :start-time="forumStore.currentForum.start_time"
      :duration-minutes="forumStore.currentForum?.duration_minutes || 30" 
      :status="forumStore.currentForum?.status || 'pending'"
    />

    <!-- Participant Modal -->
    <a-modal
      v-model:open="isParticipantModalVisible"
      title="参与者列表"
      width="600px"
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
  CodeOutlined
} from '@ant-design/icons-vue'

import { message } from 'ant-design-vue'

const route = useRoute()
const forumStore = useForumStore()
const personaStore = usePersonaStore()
const authStore = useAuthStore()
const router = useRouter()

const starting = ref(false)
const isParticipantModalVisible = ref(false)
const isSystemLogModalVisible = ref(false)
const forumId = Number(route.params.id)
const { connect, disconnect, isConnected } = useForumWebSocket(forumId)

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
  // If we are coming back to the same forum, reset loading state if needed
  // But forumStore.fetchForum handles smart reloading
  
  try {
    // 1. Load static forum data first via HTTP
    await forumStore.fetchForum(forumId)
    
    // Check if forum exists (fetchForum might set currentForum to null on error)
    // NOTE: If fetchForum uses cached data, it might return immediately but loading might not be triggered.
    // We rely on forumStore to manage loading state.
    
    if (!forumStore.currentForum) {
         // Maybe it's still loading? fetchForum awaits.
         // If it's null after await, it failed.
         message.error('论坛不存在或加载失败')
         router.push('/forums')
         return
    }
    
    // Force reactivity update if needed?
    // Vue should handle it.
    
    // 3. Load participant info context
    personaStore.fetchPersonas(authStore.user?.id).catch(e => console.warn('Persona fetch failed', e))
    
    // 4. Connect WS in background for realtime updates
    // Non-blocking call
    connect()
  } catch (e) {
    console.error('Failed to load forum details', e)
    // Even if load fails, allow navigation back
  }
})

onUnmounted(() => {
  disconnect()
  // forumStore.leaveForum() // <-- REMOVED THIS
  // We want to KEEP the state when navigating away, so when we come back, it's instant.
  // The fetchForum logic handles "switching" to a new forum properly.
  // leaveForum was clearing messages/currentForum which caused the "white screen" flash or state loss.
})

const handleDelete = async () => {
    try {
        await forumStore.deleteForum(forumId)
        message.success('论坛已删除')
        router.push('/forums')
    } catch (e: any) {
        message.error('删除失败')
    }
}

const handleStart = async () => {
    starting.value = true
    try {
        // Ensure WebSocket is connected BEFORE starting the forum task
        // This ensures we catch the very first "System Log" messages
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
</script>

<style scoped>
.forum-detail-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Occupy full viewport height */
  background: #fff;
  overflow: hidden;
}

.forum-header {
  height: 60px;
  flex-shrink: 0; /* Prevent shrinking */
  padding: 0 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  position: relative; /* Ensure stacking context */
  z-index: 100; /* Higher than content area */
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.forum-topic {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
}
</style>
