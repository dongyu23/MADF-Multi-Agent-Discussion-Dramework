<template>
  <a-modal
    v-model:open="visible"
    title="上帝模式：创造智能体"
    width="1000px"
    :footer="null"
    @cancel="handleCancel"
    class="god-agent-modal"
    :bodyStyle="{ padding: 0, height: '80vh' }"
    centered
  >
    <div class="god-agent-container">
      <div class="chat-window" ref="chatWindowRef">
        <div v-for="(msg, index) in godStore.messages" :key="index" class="message-item" :class="msg.role">
          <div class="avatar">
            <a-avatar v-if="msg.role === 'assistant'" style="background-color: #7265e6">G</a-avatar>
            <a-avatar v-else style="background-color: #1890ff">U</a-avatar>
          </div>
          <div class="content">
            <div class="bubble">
              {{ msg.content }}
            </div>
            
            <!-- Generated Personas Preview -->
            <div v-if="msg.personas && msg.personas.length > 0" class="persona-preview">
              <a-card 
                v-for="p in msg.personas" 
                :key="p.id" 
                class="persona-card"
                size="small"
                :title="p.name"
              >
                <template #extra>
                  <a-tag color="blue">{{ p.title }}</a-tag>
                </template>
                <p class="persona-bio">{{ p.bio }}</p>
                <div class="persona-tags">
                  <a-tag v-for="t in p.theories.slice(0, 3)" :key="t">{{ t }}</a-tag>
                </div>
                <div class="actions">
                  <a-button type="primary" size="small" @click="handleViewPersona">查看详情</a-button>
                </div>
              </a-card>
            </div>
          </div>
        </div>
        
        <div v-if="godStore.loading" class="message-item assistant">
          <div class="avatar">
            <a-avatar style="background-color: #7265e6">G</a-avatar>
          </div>
          <div class="content">
            <div class="bubble loading">
              <a-spin size="small" /> 正在构思智能体...
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <a-textarea
          v-model:value="input"
          placeholder="描述您想要创建的智能体（例如：一个性格暴躁但心地善良的资深程序员，信奉极简主义代码哲学...）"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          @keydown.ctrl.enter.prevent="handleSend"
          :disabled="godStore.loading"
        />
        <a-button type="primary" class="send-btn" @click="handleSend" :loading="godStore.loading">
          发送
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { useGodStore } from '@/stores/god'
import { useRouter } from 'vue-router'
import { usePersonaStore } from '@/stores/persona'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits(['update:open'])

const godStore = useGodStore()
const personaStore = usePersonaStore()
const router = useRouter()
const input = ref('')
const chatWindowRef = ref<HTMLElement | null>(null)

const visible = computed({
  get: () => props.open,
  set: (val) => emit('update:open', val)
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatWindowRef.value) {
      chatWindowRef.value.scrollTop = chatWindowRef.value.scrollHeight
    }
  })
}

watch(() => props.open, (val) => {
  if (val) {
    if (godStore.messages.length === 0) {
      godStore.messages.push({
        role: 'assistant',
        content: '我是上帝智能体代理。请告诉我您想创建什么样的角色，我会为您生成详细的设定。',
        timestamp: Date.now()
      })
    }
    scrollToBottom()
  }
})

watch(() => godStore.messages.length, scrollToBottom)

const handleSend = async () => {
  if (!input.value.trim() || godStore.loading) return
  
  const prompt = input.value
  input.value = ''
  
  try {
    await godStore.sendMessage(prompt)
  } catch (error: any) {
    godStore.messages.push({
        role: 'assistant',
        content: `生成失败: ${error.message || '请求超时'}。请点击发送按钮重试。`,
        timestamp: Date.now()
    })
    input.value = prompt
  }
}

const handleCancel = () => {
  visible.value = false
}

const handleViewPersona = () => {
  visible.value = false
  personaStore.fetchPersonas()
  router.push('/personas')
}

// Watch visibility to refresh list when modal closes if generation happened
watch(visible, (newVal) => {
  if (!newVal && godStore.messages.some(m => m.personas && m.personas.length > 0)) {
    personaStore.fetchPersonas()
  }
})
</script>

<style scoped>
.god-agent-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border-radius: 0;
}

.chat-window {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7f9;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 90%;
}

.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-item.assistant {
  align-self: flex-start;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bubble {
  padding: 10px 14px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.message-item.user .bubble {
  background: #1890ff;
  color: #fff;
  border-radius: 8px 0 8px 8px;
}

.message-item.assistant .bubble {
  border-radius: 0 8px 8px 8px;
}

.loading {
  font-style: italic;
  color: #8c8c8c;
}

.persona-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.persona-card {
  width: 100%;
}

.persona-bio {
  font-size: 12px;
  color: #666;
  margin: 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.persona-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.input-area {
  padding: 16px;
  background: #fff;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  border-top: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.send-btn {
  height: auto;
  padding: 8px 24px;
}
</style>