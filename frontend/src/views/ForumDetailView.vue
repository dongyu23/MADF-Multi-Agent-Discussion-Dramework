<template>
  <div class="forum-layout">
    <!-- Left Sidebar: Forum Details & Agents -->
    <div class="forum-sidebar">
      <div class="sidebar-header">
        <a-button type="text" @click="goBack" class="back-btn">
          <arrow-left-outlined /> 返回列表
        </a-button>
      </div>

      <div class="sidebar-content">
        <div class="forum-info">
          <div class="status-badge" :class="forumStore.currentForum?.status">
            <div class="status-dot"></div>
            {{ statusText(forumStore.currentForum?.status) }}
          </div>
          <h2 class="forum-topic">{{ forumStore.currentForum?.topic }}</h2>
          <p class="forum-desc">{{ forumStore.currentForum?.description || '无详细描述' }}</p>
          
          <div class="forum-actions">
            <a-button
              v-if="forumStore.currentForum?.status === 'pending'"
              type="primary"
              block
              size="large"
              @click="handleStart"
              :loading="starting"
              class="action-btn start-btn"
            >
              <play-circle-outlined /> 启动讨论组
            </a-button>
            <a-popconfirm title="确定要永久删除此讨论组吗？" @confirm="handleDelete">
              <a-button danger block type="dashed" class="action-btn">
                <delete-outlined /> 删除讨论组
              </a-button>
            </a-popconfirm>
            <a-button block @click="showSystemLogModal" class="action-btn log-btn">
              <code-outlined /> 运行日志
            </a-button>
          </div>
        </div>

        <div class="agents-section">
          <h3 class="section-title">参与智能体 ({{ forumStore.currentForum?.participants?.length || 0 }})</h3>
          <div class="agent-list">
            <div v-for="p in forumStore.currentForum?.participants" :key="p.id" class="agent-card">
              <div class="agent-avatar">{{ p.name[0] }}</div>
              <div class="agent-info">
                <div class="agent-name">{{ p.name }}</div>
                <div class="agent-role">{{ p.role || '智能体' }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="forum-main">
      <div class="chat-container">
        <MessageList
          :messages="forumStore.messages"
          :loading="forumStore.loading"
        />

        <div class="chat-input-area" v-if="forumStore.currentForum?.status === 'running'">
          <div class="input-wrapper">
            <a-textarea
              v-model:value="userMessage"
              placeholder="作为观察者输入消息，按 Enter 发送，Shift + Enter 换行..."
              :auto-size="{ minRows: 2, maxRows: 6 }"
              class="chat-textarea"
              @pressEnter="handleEnter"
            />
            <a-button 
              type="primary" 
              class="send-btn" 
              :disabled="!userMessage.trim()"
              @click="handleUserSend(userMessage)"
            >
              <send-outlined />
            </a-button>
          </div>
        </div>
      </div>
    </div>

    <!-- System Log Modal -->
    <a-modal
      v-model:open="isSystemLogVisible"
      title="系统运行日志"
      width="800px"
      :footer="null"
      destroyOnClose
    >
      <div class="system-log-terminal">
        <div v-for="(log, index) in systemLogs" :key="index" class="log-line">
          <span class="log-time">[{{ new Date(log.timestamp).toLocaleTimeString() }}]</span>
          <span :class="['log-level', `level-${log.level.toLowerCase()}`]">{{ log.level }}</span>
          <span class="log-content">{{ log.message }}</span>
        </div>
        <div v-if="systemLogs.length === 0" style="color: #666; text-align: center; padding: 40px;">
          暂无日志记录
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForumStore } from '@/stores/forum'
import MessageList from '@/components/forum/MessageList.vue'
import { message } from 'ant-design-vue'
import { 
  ArrowLeftOutlined, 
  PlayCircleOutlined, 
  DeleteOutlined,
  CodeOutlined,
  SendOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const forumStore = useForumStore()
const forumId = route.params.id as string

const userMessage = ref('')
const starting = ref(false)
const isSystemLogVisible = ref(false)
const systemLogs = ref<any[]>([])
let logInterval: any = null

const statusText = (status: string | undefined) => {
  if (status === 'pending') return '准备中'
  if (status === 'running') return '正在讨论'
  if (status === 'finished' || status === 'closed') return '已结束'
  return '未知状态'
}

const goBack = () => {
  router.push('/forums')
}

const handleStart = async () => {
  try {
    starting.value = true
    await forumStore.startForum(forumId)
    message.success('讨论组启动成功')
  } catch (error: any) {
    message.error(error.message || '启动失败')
  } finally {
    starting.value = false
  }
}

const handleDelete = async () => {
  try {
    await forumStore.deleteForum(forumId)
    message.success('删除成功')
    router.push('/forums')
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

const handleEnter = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (userMessage.value.trim()) {
      handleUserSend(userMessage.value)
    }
  }
}

const handleUserSend = async (val: string) => {
  if (!val.trim()) return
  try {
    const msg = val
    userMessage.value = ''
    await forumStore.sendMessage(forumId, msg)
  } catch (error: any) {
    message.error(error.message || '发送失败')
  }
}

const showSystemLogModal = async () => {
  isSystemLogVisible.value = true
  await fetchLogs()
  logInterval = setInterval(fetchLogs, 3000)
}

const fetchLogs = async () => {
  if (!isSystemLogVisible.value) return
  try {
    systemLogs.value = await forumStore.getForumLogs(forumId)
  } catch (e) {
    console.error('Failed to fetch logs')
  }
}

onMounted(async () => {
  await forumStore.fetchForumDetail(forumId)
  forumStore.startPolling(forumId)
})

onUnmounted(() => {
  forumStore.stopPolling()
  if (logInterval) clearInterval(logInterval)
})
</script>

<style scoped>
.forum-layout {
  display: flex;
  height: calc(100vh - 64px);
  background-color: #09090b;
}

/* Sidebar Styles */
.forum-sidebar {
  width: 320px;
  background: rgba(255, 255, 255, 0.02);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.back-btn {
  color: rgba(255, 255, 255, 0.65);
  padding: 0;
}

.back-btn:hover {
  color: #ffffff;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* Forum Info */
.forum-info {
  margin-bottom: 32px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 16px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.65);
}

.status-badge.running {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.2);
}

.status-badge.running .status-dot { background: #52c41a; box-shadow: 0 0 8px #52c41a; }
.status-badge.pending .status-dot { background: #faad14; }
.status-badge.finished .status-dot { background: #8c8c8c; }
.status-badge.closed .status-dot { background: #ff4d4f; }

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.forum-topic {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
  line-height: 1.3;
}

.forum-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.6;
  margin-bottom: 24px;
}

.forum-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  height: 40px;
  border-radius: 8px;
}

.start-btn {
  background: linear-gradient(135deg, #1677ff 0%, #096dd9 100%);
  border: none;
}

.log-btn {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.log-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

/* Agents Section */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(25, 25, 35, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.agent-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #2b323b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: #ffffff;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 2px;
}

.agent-role {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

/* Main Chat Area */
.forum-main {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  background: #141414;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* Chat Input Area */
.chat-input-area {
  padding: 24px;
  background: rgba(20, 20, 20, 0.8);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.input-wrapper {
  max-width: 800px;
  margin: 0 auto;
  position: relative;
  display: flex;
  align-items: flex-end;
  background: #1f1f1f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 8px;
  transition: all 0.3s ease;
}

.input-wrapper:focus-within {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.1);
}

.chat-textarea {
  flex: 1;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #ffffff;
  resize: none;
  padding: 4px 8px;
}

.chat-textarea::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 8px;
}

/* Log Terminal */
.system-log-terminal {
  background-color: #0d0d12;
  color: #a6e22e;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  padding: 16px;
  height: 500px;
  overflow-y: auto;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.log-line {
  margin-bottom: 6px;
  line-height: 1.5;
  font-size: 13px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  padding-bottom: 4px;
}

.log-time {
  color: rgba(255, 255, 255, 0.3);
  margin-right: 12px;
}

.log-level {
  display: inline-block;
  width: 50px;
  font-weight: 600;
}

.level-info { color: #1677ff; }
.level-warning { color: #faad14; }
.level-error { color: #ff4d4f; }
.level-debug { color: #8c8c8c; }
.level-success { color: #52c41a; }

.log-content {
  color: rgba(255, 255, 255, 0.85);
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 768px) {
  .forum-layout {
    flex-direction: column;
  }
  .forum-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  .sidebar-content {
    max-height: 300px;
  }
}
</style>
