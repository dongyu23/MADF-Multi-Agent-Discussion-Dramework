<template>
  <div class="message-item" :class="{ 'message-moderator': isModerator }">
    <div class="message-avatar">
      <a-avatar v-if="isModerator" key="moderator-avatar" :style="{ backgroundColor: avatarColor }" size="large">
        <template #icon>
          <user-outlined />
        </template>
      </a-avatar>
      <a-avatar v-else key="participant-avatar" :style="{ backgroundColor: avatarColor }" size="large">
        {{ speakerInitial }}
      </a-avatar>
    </div>
    
    <div class="message-content-wrapper">
      <div class="message-info">
        <span class="speaker-name">
          {{ speakerName }}
          <a-tag v-if="isModerator" color="gold" style="margin-left: 4px; font-size: 10px; line-height: 14px; height: 16px; padding: 0 4px;">主持人</a-tag>
        </span>
        <span class="time">{{ formatTime(timestamp) }}</span>
      </div>
      
      <div class="message-bubble">
        <!-- Thought Process Expansion -->
        <div v-if="thought" class="thought-process">
            <a-collapse ghost :bordered="false" style="background: transparent; padding: 0;">
                <a-collapse-panel key="1" header="思考过程 (点击展开)" style="border: none; padding: 0;">
                    <template #extra>
                        <bulb-outlined />
                    </template>
                    <div class="thought-content">
                        {{ thought }}
                    </div>
                </a-collapse-panel>
            </a-collapse>
            <div class="thought-divider"></div>
        </div>

        <div v-if="isStreaming" class="streaming-indicator">
          <loading-outlined />
        </div>
        {{ content }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { LoadingOutlined, UserOutlined, BulbOutlined } from '@ant-design/icons-vue'

const props = defineProps<{
  speakerName: string
  content: string
  thought?: string | null // Added thought prop
  timestamp: string
  isSelf: boolean
  isStreaming?: boolean
  moderatorId?: number | null
}>()

const isModerator = computed(() => {
  return !!props.moderatorId || props.speakerName.includes('主持人')
})

const isStreaming = computed(() => {
    return props.isStreaming || false
})

const speakerInitial = computed(() => {
    return props.speakerName ? props.speakerName[0] : '?'
})

const formatTime = (isoString: string) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleTimeString()
}

const avatarColor = computed(() => {
  if (isModerator.value) return '#faad14' // Gold for moderator
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < props.speakerName.length; i++) {
    hash = props.speakerName.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
})
</script>

<style scoped>
.chat-bubble-container {
  display: flex;
  margin-bottom: 24px;
  width: 100%;
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.is-system {
  justify-content: center;
}

.is-self {
  justify-content: flex-end;
}

.system-message {
  background: rgba(212, 175, 55, 0.05);
  border: 1px solid rgba(212, 175, 55, 0.2);
  color: #D4AF37;
  padding: 8px 24px;
  font-family: 'Azeret Mono', monospace;
  font-size: 11px;
  letter-spacing: 1px;
  max-width: 80%;
  text-align: center;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 75%;
}

.is-self .message-content {
  align-items: flex-end;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.is-self .message-header {
  flex-direction: row-reverse;
}

.sender-name {
  font-family: 'Cormorant Garamond', serif;
  font-size: 18px;
  font-weight: bold;
  color: #D4AF37;
  letter-spacing: 1px;
}

.sender-role {
  font-family: 'Azeret Mono', monospace;
  font-size: 9px;
  padding: 2px 6px;
  border: 1px solid #1890ff;
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  text-transform: uppercase;
}

.message-time {
  font-family: 'Azeret Mono', monospace;
  font-size: 10px;
  color: #666;
}

.message-body {
  position: relative;
  background: rgba(15, 15, 20, 0.85);
  border: 1px solid #333;
  padding: 20px 24px;
  color: #F2E8CF;
  font-family: 'Cormorant Garamond', serif;
  font-size: 18px;
  line-height: 1.6;
  box-shadow: 0 4px 15px rgba(0,0,0,0.5);
  border-left: 3px solid #D4AF37;
}

.is-self .message-body {
  background: rgba(212, 175, 55, 0.05);
  border-left: 1px solid #333;
  border-right: 3px solid #D4AF37;
}

.thought-process {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed #333;
}

.thought-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #888;
  font-family: 'Azeret Mono', monospace;
  font-size: 11px;
  margin-bottom: 8px;
}

.thought-content {
  font-family: 'Azeret Mono', monospace;
  font-size: 12px;
  color: #888;
  line-height: 1.5;
  background: rgba(0,0,0,0.3);
  padding: 12px;
  border-left: 2px solid #555;
}

.markdown-content {
  overflow-wrap: break-word;
  word-wrap: break-word;
}

.markdown-content :deep(p) {
  margin-bottom: 1em;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(pre) {
  background: #050505 !important;
  border: 1px solid #333 !important;
  border-radius: 0 !important;
  font-family: 'Azeret Mono', monospace !important;
  padding: 16px !important;
}

.markdown-content :deep(code) {
  font-family: 'Azeret Mono', monospace !important;
  color: #D4AF37;
  background: rgba(0,0,0,0.3);
  padding: 2px 4px;
}

.markdown-content :deep(pre code) {
  color: #a6e22e;
  background: transparent;
  padding: 0;
}
</style>
