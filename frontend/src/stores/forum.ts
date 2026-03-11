import { defineStore } from 'pinia'
import request from '@/utils/request'
import { message } from 'ant-design-vue'

export interface Message {
  id: number
  forum_id: number
  persona_id: number
  moderator_id?: number | null
  speaker_name: string
  content: string
  thought?: string | null // Added thought field
  timestamp: string
}

export interface Moderator {
  id: number
  name: string
  title: string
  bio: string
  system_prompt?: string
  greeting_template?: string
  closing_template?: string
  summary_template?: string
  creator_id: number
  created_at: string
}

export interface Forum {
  id: number
  topic: string
  creator_id: number
  moderator_id?: number | null
  moderator?: Moderator | null
  status: string
  start_time: string
  summary_history: string[]
  participants?: any[]
  duration_minutes?: number
}

export interface SystemLog {
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'thought' | 'speech'
  content: string
  source?: string
}

export const useForumStore = defineStore('forum', {
  state: () => ({
    forums: [] as Forum[],
    currentForum: null as Forum | null,
    messages: [] as Message[],
    moderators: [] as Moderator[],
    systemLogs: [] as SystemLog[],
    loading: false,
    thinking: false
  }),
  actions: {
    async fetchSystemLogs(forumId: number) {
      try {
        const res = await request.get(`/forums/${forumId}/logs`)
        this.systemLogs = res.data
        
        // Restore "thinking" or "speaking" state based on last log
        if (this.systemLogs.length > 0) {
            const lastLog = this.systemLogs[this.systemLogs.length - 1]
            if (lastLog.level === 'thought' || lastLog.content.includes('正在思考')) {
                this.thinking = true
            } else {
                this.thinking = false
            }
        }
      } catch (error) {
        console.error('Failed to fetch system logs:', error)
      }
    },
    addSystemLog(log: SystemLog) {
        this.systemLogs.push(log)
    },
    updateStreamingMessage(chunk: { 
        speaker_name: string, 
        content: string, 
        persona_id: number | null, 
        moderator_id?: number | null, 
        stream_id?: string, 
        thought?: string | null,
        timestamp: string 
    }) {
        // Robust logic: Use stream_id if available to find the message
        // If stream_id is missing, fallback to last message match (legacy behavior)
        
        let targetMsg: Message | undefined
        
        if (chunk.stream_id) {
            targetMsg = this.messages.find(m => (m as any).stream_id === chunk.stream_id)
        } else {
            // Fallback: Check last message
            const lastMsg = this.messages[this.messages.length - 1]
            if (lastMsg && lastMsg.speaker_name === chunk.speaker_name && (lastMsg as any).isStreaming) {
                targetMsg = lastMsg
            }
        }
        
        if (targetMsg) {
            targetMsg.content += chunk.content
            // Thought usually comes with the first chunk or separately, update if present
            if (chunk.thought && !targetMsg.thought) {
                targetMsg.thought = chunk.thought
            }
        } else {
            // Start new streaming message
            const newMsg: Message = {
                id: Date.now(), // Temp ID, will be replaced by final message
                forum_id: this.currentForum?.id || 0,
                persona_id: chunk.persona_id || 0,
                moderator_id: chunk.moderator_id || null,
                speaker_name: chunk.speaker_name,
                content: chunk.content,
                thought: chunk.thought, // Initialize thought
                timestamp: chunk.timestamp,
            }
            ;(newMsg as any).isStreaming = true
            ;(newMsg as any).stream_id = chunk.stream_id // Store stream_id for future chunks
            this.messages.push(newMsg)
        }
    },
    addMessage(msg: Message & { stream_id?: string }) {
        // When the full message arrives (type: 'new_message'), replace the streaming one
        // Match by stream_id if available, otherwise fallback
        
        let streamingMsgIndex = -1
        
        if (msg.stream_id) {
            streamingMsgIndex = this.messages.findIndex(m => (m as any).stream_id === msg.stream_id)
        }
        
        // Fallback match if stream_id not found or not provided
        if (streamingMsgIndex === -1) {
             streamingMsgIndex = this.messages.findIndex(m => m.speaker_name === msg.speaker_name && (m as any).isStreaming)
        }
        
        if (streamingMsgIndex !== -1) {
            // Replace streaming message with the final one
            this.messages.splice(streamingMsgIndex, 1, msg)
        } else {
             // Check if message already exists by ID to prevent duplicates
             const exists = this.messages.find(m => m.id === msg.id)
             if (!exists) {
                 this.messages.push(msg)
             }
        }
        
        // Auto-scroll logic could be triggered here or in component watcher
    },
    async fetchForums() {
      // Background update if data exists
      const isBackground = this.forums.length > 0
      if (!isBackground) {
          this.loading = true
      }
      try {
        const res = await request.get('/forums/')
        this.forums = res.data
      } catch (error) {
        console.error('Failed to fetch forums:', error)
      } finally {
        this.loading = false
      }
    },
    async fetchForum(id: number) {
        // If we already have this forum loaded, skip full load or do light refresh
        if (this.currentForum && this.currentForum.id === id) {
            this.fetchMessages(id) // Background
            return
        }

        // Switching forums, clear old data first
        if (this.currentForum) {
            this.clearForumData()
        }
        
        this.loading = true
        try {
            const res = await request.get(`/forums/${id}`)
            this.currentForum = res.data
            await this.fetchMessages(id)
        } catch (error) {
            console.error(`Failed to fetch forum ${id}:`, error)
            // If failed, make sure currentForum is null so UI handles it
            this.currentForum = null
        } finally {
            this.loading = false
        }
    },
    async fetchMessages(forumId: number) {
      try {
        const res = await request.get(`/forums/${forumId}/messages`)
        this.messages = res.data
        await this.fetchSystemLogs(forumId)
      } catch (error) {
        console.error(`Failed to fetch messages for forum ${forumId}:`, error)
      }
    },
    async fetchModerators() {
      try {
        const res = await request.get('/moderators/')
        this.moderators = res.data
      } catch (error) {
        console.error('Failed to fetch moderators:', error)
        this.moderators = []
      }
    },
    async createForum(topic: string, participantIds: number[], duration: number, moderatorId?: number) {
      this.loading = true
      try {
        const normalizedParticipantIds = Array.from(
          new Set(
            participantIds
              .map(id => Number(id))
              .filter(id => Number.isInteger(id) && id > 0)
          )
        )
        const res = await request.post('/forums/', {
          topic,
          participant_ids: normalizedParticipantIds,
          moderator_id: moderatorId,
          duration_minutes: duration
        })
        message.success('论坛创建成功')
        // Optimistic update: Add to list immediately
        this.forums.unshift(res.data)
        return res.data
      } catch (error) {
        console.error('Failed to create forum:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async startForum(id: number) {
      try {
        await request.post(`/forums/${id}/start`)
        message.success('论坛已开始')
        if (this.currentForum && this.currentForum.id === id) {
            this.currentForum.status = 'running'
        }
      } catch (error) {
        console.error('Failed to start forum:', error)
        message.error('启动失败')
      }
    },
    async deleteForum(id: number) {
      // Optimistic update: Remove locally first
      const previousForums = [...this.forums]
      const previousCurrentForum = this.currentForum
      
      this.forums = this.forums.filter(f => f.id !== id)
      
      // If we are deleting the current forum, we should probably stop it first?
      // But delete endpoint handles cleanup.
      
      if (this.currentForum && this.currentForum.id === id) {
           this.currentForum = null
      }
      
      try {
        // Try to stop first if it's running? 
        // Backend delete should handle it, but let's be safe
        // Actually, backend delete_forum endpoint does cleanup tasks.
        await request.delete(`/forums/${id}`)
      } catch (error) {
        console.error('Failed to delete forum:', error)
        // Rollback on failure
        this.forums = previousForums
        this.currentForum = previousCurrentForum
        throw error
      }
    },
    // New Action: Stop Forum
    async stopForum(id: number) {
        try {
            await request.post(`/forums/${id}/stop`)
            // Update local status if applicable
            const f = this.forums.find(f => f.id === id)
            if (f) f.status = 'closed'
            if (this.currentForum && this.currentForum.id === id) {
                this.currentForum.status = 'closed'
            }
            message.success('论坛已停止')
        } catch (error) {
            console.error('Failed to stop forum:', error)
            message.error('停止失败')
        }
    },
    leaveForum() {
      // Don't clear messages immediately to prevent flicker when switching
      // But clearing currentForum is fine
      // Actually, clearing messages is safer to avoid showing wrong forum data
      // MODIFIED: Don't clear if we are just navigating back but might return (keep cache)
      // But user asked "即使用户点击返回，页面也不会卸载，以便不重复读取"
      // So we should NOT clear messages here.
      
      // this.messages = [] // Keep messages in store
      // this.systemLogs = [] // Keep logs
      
      // But if we enter ANOTHER forum, we must clear.
      // fetchForum() handles clearing: `this.currentForum = null` and re-fetching.
      
      // However, we should stop thinking state?
      this.thinking = false
      this.loading = false
      
      // We only clear currentForum ref but keep data until overwritten?
      // No, if we clear currentForum, UI might break if it relies on it.
      // Let's keep currentForum too, but maybe mark as "inactive"?
      // The requirement says: "user current executing forum, page won't unload".
      // This implies keeping the state.
      
      // So leaveForum should be minimal.
    },
    
    // New Action: Clear Forum Data (explicitly called when needed, e.g. entering NEW forum)
    clearForumData() {
        this.messages = []
        this.systemLogs = []
        this.currentForum = null
        this.thinking = false
    }
  }
})
