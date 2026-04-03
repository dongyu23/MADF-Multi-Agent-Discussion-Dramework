<template>
  <a-modal
    v-model:open="visible"
    title="上帝模式：创造真实智能体 (联网版)"
    width="1000px"
    :footer="null"
    @cancel="handleCancel"
    class="god-agent-modal"
    :bodyStyle="{ padding: 0, height: '80vh' }"
    centered
  >
    <div class="god-agent-container">
      <div class="chat-window" ref="chatWindowRef">
        <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
          <div class="avatar">
            <a-avatar v-if="msg.role === 'assistant'" style="background-color: #faad14">R</a-avatar>
            <a-avatar v-else style="background-color: #1890ff">U</a-avatar>
          </div>
          <div class="content-wrapper">
            <!-- User Message -->
            <div v-if="msg.role === 'user'" class="bubble user-bubble">
              {{ msg.content }}
            </div>

            <!-- Assistant Message (Structured Items) -->
            <template v-else>
               <!-- Fallback for simple content -->
               <div v-if="msg.content && (!msg.items || msg.items.length === 0)" class="bubble">
                 {{ msg.content }}
               </div>

               <!-- Structured Items -->
               <div v-for="(item, i) in msg.items" :key="i" class="msg-item">
                 
                 <!-- 1. Normal Text -->
                 <div v-if="item.type === 'text'" class="bubble">
                   {{ item.content }}
                 </div>

                 <!-- 2. Search Intent (Thought) -->
                 <div v-else-if="item.type === 'thought'" class="bubble thought-bubble">
                   <div class="thought-header">
                     <span class="icon">🤔</span> 思考过程
                   </div>
                   <div class="thought-content">{{ item.content }}</div>
                 </div>

                 <!-- 3. Searching State -->
                 <div v-else-if="item.type === 'search'" class="search-block">
                   <div class="search-status">
                     <span v-if="item.status === 'loading'" class="icon loading">⏳</span>
                     <span v-else class="icon success">✅</span>
                     <span class="status-text">
                       {{ item.status === 'loading' ? '正在搜索' : '搜索完成' }}: 
                       <span class="query">{{ item.query }}</span>
                     </span>
                   </div>
                   <div v-if="item.status === 'done' && item.result" class="search-result">
                     <a-collapse ghost size="small">
                        <a-collapse-panel key="1" header="查看搜索结果">
                          <pre>{{ item.result }}</pre>
                        </a-collapse-panel>
                     </a-collapse>
                   </div>
                 </div>

                 <!-- 4. Generated Persona -->
                 <div v-else-if="item.type === 'persona'" class="persona-block">
                   <a-card 
                    size="small" 
                    class="persona-card"
                    :title="item.persona.name"
                   >
                     <template #extra>
                        <a-tag color="orange">{{ item.persona.title }}</a-tag>
                     </template>
                     <p class="persona-bio">{{ item.persona.bio }}</p>
                     <div class="persona-tags">
                        <a-tag v-for="t in (item.persona.theories || []).slice(0, 3)" :key="t">{{ t }}</a-tag>
                     </div>
                     <div class="actions">
                        <a-button type="primary" size="small" @click="handleViewPersona">查看详情</a-button>
                     </div>
                   </a-card>
                 </div>

                 <!-- 6. Status/Progress -->
                 <div v-else-if="item.type === 'status'" class="status-block">
                   <div class="status-content">
                     <span class="icon">🚀</span> 
                     <span class="status-text">{{ item.content }}</span>
                   </div>
                 </div>

                 <!-- 5. Error -->
                 <div v-else-if="item.type === 'error'" class="bubble error-bubble">
                   ❌ {{ item.content }}
                 </div>
               </div>
            </template>
          </div>
        </div>
        
        <div v-if="loading && (!messages[messages.length-1]?.items || messages[messages.length-1]?.items?.length === 0)" class="message-item assistant">
          <div class="avatar">
            <a-avatar style="background-color: #faad14">R</a-avatar>
          </div>
          <div class="content-wrapper">
            <div class="bubble loading">
              <a-spin size="small" /> 正在呼唤上帝...
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <a-textarea
          v-model:value="input"
          placeholder="描述您想要创建的真实人物... (Enter 发送, Shift+Enter 换行)"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.ctrl.enter.prevent="handleSend"
          :disabled="loading"
          class="custom-textarea"
        />
        <a-button type="primary" class="send-btn" @click="handleSend" :loading="loading">
          <template #icon><send-outlined /></template>
          发送
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePersonaStore } from '@/stores/persona'
import { SendOutlined } from '@ant-design/icons-vue'

interface MessageItem {
  type: 'text' | 'thought' | 'search' | 'persona' | 'error' | 'status'
  content?: string
  query?: string
  result?: string
  status?: 'loading' | 'done'
  persona?: any
  current?: number
  total?: number
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content?: string // For user messages or simple assistant messages
  items?: MessageItem[] // For structured assistant messages
  timestamp: number
}

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits(['update:open'])

const router = useRouter()
const personaStore = usePersonaStore()
const input = ref('')
const chatWindowRef = ref<HTMLElement | null>(null)
const messages = ref<ChatMessage[]>([])
const loading = ref(false)
const totalToGenerate = ref(1)

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
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'assistant',
        content: '',
        items: [{ type: 'text', content: '我是联网版上帝智能体。我可以搜索互联网信息，为您创造基于真实背景的深度角色。' }],
        timestamp: Date.now()
      })
    }
    scrollToBottom()
  }
})

watch(() => messages.value.length, scrollToBottom)
// Deep watch for items updates
watch(() => messages.value[messages.value.length - 1]?.items, scrollToBottom, { deep: true })

const handleSend = async () => {
  if (!input.value.trim() || loading.value) return
  
  const prompt = input.value
  input.value = ''
  
  // Add user message
  messages.value.push({
    role: 'user',
    content: prompt,
    timestamp: Date.now()
  })
  
  loading.value = true
  totalToGenerate.value = 1 // Reset
  
  // Prepare assistant message container
  const assistantMsg = ref<ChatMessage>({
    role: 'assistant',
    items: [],
    timestamp: Date.now()
  })
  messages.value.push(assistantMsg.value)
  
  try {
    // Fetch SSE
    const response = await fetch('/api/v1/god/generate_real', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({ prompt, n: 1 })
    })

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) throw new Error('No reader')

    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      
      for (const line of parts) {
        if (line.trim().startsWith('data: ')) {
          try {
            const jsonStr = line.trim().slice(6)
            if (!jsonStr) continue
            
            const event = JSON.parse(jsonStr)
            const items = assistantMsg.value.items || []
            
            if (event.type === 'count') {
                totalToGenerate.value = event.content
                
            } else if (event.type === 'thought_start') {
                // High level status update
                items.push({ type: 'status', content: event.content })
                
            } else if (event.type === 'progress') {
                // Update total and find the last status item to update
                if (event.total) totalToGenerate.value = event.total
                
                // Find last status item
                const lastStatus = [...items].reverse().find(i => i.type === 'status')
                if (lastStatus) {
                    lastStatus.content = `=== 开始生成第 ${event.current} 位角色 (共 ${event.total} 位) ===`
                }
                
            } else if (event.type === 'thought_chunk') {
                // Find active thought item or create one
                let lastItem = items[items.length - 1]
                
                // Skip creating thought item if the last item is status (which happens at start)
                // But we need to put thoughts SOMEWHERE.
                // If last item is status, create a thought item.
                if (!lastItem || lastItem.type !== 'thought') {
                    lastItem = { type: 'thought', content: '' }
                    items.push(lastItem)
                }
                lastItem.content += event.content
                
            } else if (event.type === 'thought') {
                // Finalized thought (cleaned up)
                // Update the last thought item if exists
                let lastItem = items[items.length - 1]
                if (lastItem && lastItem.type === 'thought') {
                    lastItem.content = event.content
                } else {
                    items.push({ type: 'thought', content: event.content })
                }
                
            } else if (event.type === 'action') {
                // e.g. "搜索: keyword"
                const content = event.content
                if (content.includes('搜索') || content.includes('Search')) {
                    // Extract query roughly
                    const query = content.replace(/搜索[:：]|Search\[|\]/g, '').trim()
                    items.push({ type: 'search', query: query, status: 'loading', result: '' })
                } else {
                    // Other actions (like Finish) - maybe log as text?
                    // Usually Finish is handled by result event, but the Action: Finish log exists.
                    // We can ignore Finish action log or show as text.
                    // Let's show as debug/text if not search
                    // items.push({ type: 'text', content: `[Action] ${content}` })
                }
                
            } else if (event.type === 'observation') {
                // Update last search item
                // Find the last search item that is loading
                // Reverse search
                let searchItem = [...items].reverse().find(i => i.type === 'search' && i.status === 'loading')
                if (searchItem) {
                    searchItem.status = 'done'
                    // Fix: Clean up observation content if it contains raw JSON string artifacts
                    let cleanContent = event.content;
                    // Check if content looks like a JSON string dump (starts with " and ends with ")
                    // and try to parse it if it's double encoded
                    if (typeof cleanContent === 'string') {
                        // Remove potential surrounding quotes and unescape
                        // But simple approach: just display it. Pre tag handles formatting.
                        // If user complains about specific artifacts like "[ \n " \n \", handle them:
                        if (cleanContent.startsWith('[\n "') || cleanContent.startsWith('["')) {
                             try {
                                 const parsed = JSON.parse(cleanContent);
                                 if (Array.isArray(parsed)) {
                                     cleanContent = parsed.join('\n');
                                 }
                             } catch (e) {
                                 // ignore
                             }
                        }
                    }
                    searchItem.result = cleanContent
                } else {
                    // Fallback
                    items.push({ type: 'text', content: `[Observation] ${event.content}` })
                }
                
            } else if (event.type === 'result') {
                // Persona(s) generated
                const results = Array.isArray(event.content) ? event.content : [event.content]
                for (const p of results) {
                    items.push({ type: 'persona', persona: p })
                }
                items.push({ type: 'text', content: `✅ 生成完成！` })
                
            } else if (event.type === 'error') {
                items.push({ type: 'error', content: event.content })
                message.error('生成过程中发生错误')
            }
            
            scrollToBottom()
          } catch (e) {
            console.error('JSON parse error', e)
          }
        }
      }
    }

  } catch (error: any) {
    assistantMsg.value.items?.push({ type: 'error', content: error.message || '网络请求失败' })
  } finally {
    loading.value = false
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
  if (!newVal && messages.value.some(m => m.items?.some(i => i.type === 'persona'))) {
    personaStore.fetchPersonas()
  }
})
</script>

<style scoped>
.god-agent-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #141414;
  border-radius: 8px;
  overflow: hidden;
}

.chat-window {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: #141414;
}

/* Custom scrollbar */
.chat-window::-webkit-scrollbar {
  width: 6px;
}
.chat-window::-webkit-scrollbar-track {
  background: transparent;
}
.chat-window::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.message-item {
  display: flex;
  margin-bottom: 24px;
  align-items: flex-start;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-item.user {
  flex-direction: row-reverse;
}

.avatar {
  margin: 0 16px;
}

.content-wrapper {
  max-width: 75%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-item.user .content-wrapper {
  align-items: flex-end;
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.85);
  background: #1f1f1f;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.user-bubble {
  background: #1677ff;
  border: none;
  color: #fff;
}

/* Tool Call and Search Items */
.tool-call, .search-result {
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
}

.tool-header, .search-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 8px;
  font-weight: 500;
}

.tool-args, .search-content {
  background: rgba(0, 0, 0, 0.3);
  padding: 8px;
  border-radius: 4px;
  color: #1677ff;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
}

.search-content {
  color: rgba(255, 255, 255, 0.65);
}

/* Persona Generated Block */
.persona-generated {
  background: linear-gradient(135deg, rgba(22, 119, 255, 0.1) 0%, rgba(20, 20, 20, 0) 100%);
  border: 1px solid rgba(22, 119, 255, 0.3);
  border-radius: 12px;
  padding: 20px;
  width: 100%;
}

.persona-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1677ff;
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(22, 119, 255, 0.2);
  padding-bottom: 12px;
}

.persona-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.label {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.65);
  min-width: 60px;
  font-size: 13px;
}

.value {
  flex: 1;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  line-height: 1.5;
}

.system-prompt {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-family: monospace;
  white-space: pre-wrap;
}

.persona-actions {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.loading-indicator {
  padding: 16px;
  color: rgba(255, 255, 255, 0.45);
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-area {
  padding: 20px 24px;
  background: #1f1f1f;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.input-wrapper {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

:deep(.ant-input) {
  background-color: #141414 !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
  color: rgba(255, 255, 255, 0.85) !important;
  border-radius: 8px;
}

:deep(.ant-input:focus) {
  border-color: #1677ff !important;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.1) !important;
}

.send-btn {
  height: 40px;
  width: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.ant-modal-content) {
  background-color: #1f1f1f;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

:deep(.ant-modal-header) {
  background-color: #1f1f1f;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px 12px 0 0;
}

:deep(.ant-modal-title) {
  color: rgba(255, 255, 255, 0.85);
  font-weight: 600;
}

:deep(.ant-modal-close) {
  color: rgba(255, 255, 255, 0.45);
}

:deep(.ant-modal-close:hover) {
  color: rgba(255, 255, 255, 0.85);
}
</style>
