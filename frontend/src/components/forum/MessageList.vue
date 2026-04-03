<template>
  <div class="chat-area" ref="chatAreaRef">
    <div v-if="loading && messages.length === 0" class="loading-state">
      <a-spin tip="加载消息记录..." />
    </div>
    
    <div v-else class="message-list">
      <ChatBubble
        v-for="msg in messages"
        :key="msg.id"
        :speaker-name="msg.speaker_name"
        :content="msg.content"
        :timestamp="msg.timestamp"
        :is-self="isSelf(msg)"
        :is-streaming="(msg as any).isStreaming"
        :moderator-id="msg.moderator_id"
        :thought="msg.thought"
      />
    </div>
    <div ref="bottomRef"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import ChatBubble from './ChatBubble.vue'
import type { Message } from '@/stores/forum'
import { useAuthStore } from '@/stores/auth'
import { usePersonaStore } from '@/stores/persona'

const props = defineProps<{
  messages: Message[]
  loading: boolean
}>()

const authStore = useAuthStore()
const personaStore = usePersonaStore()
const bottomRef = ref<HTMLElement | null>(null)

const scrollToBottom = () => {
  bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
}

// Watch for both message count AND message content changes (streaming)
watch(() => props.messages, () => {
  nextTick(scrollToBottom)
}, { deep: true })

const isSelf = (msg: Message) => {
  if (msg.speaker_name === authStore.user?.username) return true
  if (msg.persona_id && personaStore.personas.find(p => p.id === msg.persona_id)) return true
  return false
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
.message-list-container {
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px;
  background: transparent;
  scroll-behavior: smooth;
  position: relative;
}

/* Custom scrollbar for the cyber feel */
.message-list-container::-webkit-scrollbar {
  width: 6px;
}
.message-list-container::-webkit-scrollbar-track {
  background: #0B0B0C;
  border-left: 1px solid #222;
}
.message-list-container::-webkit-scrollbar-thumb {
  background: #1890ff;
}

.messages-wrapper {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1000px;
  margin: 0 auto;
}

.loading-indicator {
  text-align: center;
  padding: 40px;
  font-size: 14px;
  color: #1890ff;
  letter-spacing: 2px;
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: #888;
  font-size: 14px;
  border: 1px dashed #333;
  margin-top: 40px;
}

.typing-indicator {
  padding: 16px;
  border-left: 2px solid #1890ff;
  background: rgba(15, 15, 20, 0.8);
  font-size: 14px;
  font-size: 12px;
  color: #888;
  margin-top: 16px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}
</style>
