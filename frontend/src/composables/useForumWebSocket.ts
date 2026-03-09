import { ref, onUnmounted } from 'vue'
import { useForumStore } from '@/stores/forum'

export function useForumWebSocket(forumId: number) {
  const store = useForumStore()
  let ws: WebSocket | null = null
  const isConnected = ref(false)
  let reconnectAttempts = 0
  const maxReconnectAttempts = 10
  let heartbeatInterval: any = null
  let reconnectTimeout: any = null

  const resolveWsBase = () => {
    const raw = (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim()
    if (!raw) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      return `${protocol}//${window.location.host}`
    }
    if (raw.startsWith('ws://') || raw.startsWith('wss://')) {
      return raw.replace(/\/$/, '')
    }
    if (raw.startsWith('http://') || raw.startsWith('https://')) {
      return raw.replace(/^http/, 'ws').replace(/\/$/, '')
    }
    return raw.replace(/\/$/, '')
  }

  const clearTimers = () => {
    if (heartbeatInterval) clearInterval(heartbeatInterval)
    if (reconnectTimeout) clearTimeout(reconnectTimeout)
    heartbeatInterval = null
    reconnectTimeout = null
  }

  const connect = () => {
    return new Promise<void>((resolve) => {
        if (ws) {
            if (ws.readyState === WebSocket.OPEN) {
                resolve()
                return
            }
            if (ws.readyState === WebSocket.CONNECTING) {
                // Wait for existing connection attempt
                const checkInterval = setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        clearInterval(checkInterval)
                        resolve()
                    }
                }, 100)
                return
            }
            ws.close()
        }
        
        const wsBase = resolveWsBase()
        const wsUrl = `${wsBase}/api/v1/forums/${forumId}/ws`
        
        console.log(`[WS] Connecting to: ${wsUrl}`)
        
        try {
          ws = new WebSocket(wsUrl)
          
          ws.onopen = () => {
            console.log('[WS] Connected successfully')
            isConnected.value = true
            reconnectAttempts = 0 // Reset attempts on success
            store.fetchMessages(forumId)
            
            clearTimers()
            
            // Ping every 30s to keep alive
            heartbeatInterval = setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('ping')
                }
            }, 30000)
            resolve()
          }
          
          ws.onmessage = (event) => {
            try {
              if (event.data === 'pong') return
              
              const data = JSON.parse(event.data)
              
              if (data.type === 'new_message' && data.data) {
                 store.addMessage(data.data)
              } else if (data.type === 'message_chunk' && data.data) {
                 store.updateStreamingMessage(data.data)
              } else if (data.type === 'system_log' && data.data) {
                 store.addSystemLog(data.data)
              } else if (data.type === 'system' && data.content) {
                 store.addSystemLog({
                   timestamp: new Date().toISOString(),
                   level: 'info',
                   content: data.content,
                   source: 'System'
                 })
              }
            } catch (e) {
              console.error('[WS] Parse Error', e)
            }
          }
          
          ws.onclose = (e) => {
            console.log(`[WS] Closed (Code: ${e.code}, Reason: ${e.reason})`)
            isConnected.value = false
            clearTimers()
            
            // Don't reconnect if it was a normal closure or if max attempts reached
            if (e.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000) // Exponential backoff max 30s
                console.log(`[WS] Reconnecting in ${delay}ms (Attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})...`)
                
                reconnectTimeout = setTimeout(() => {
                    reconnectAttempts++
                    connect()
                }, delay)
            } else if (reconnectAttempts >= maxReconnectAttempts) {
                 console.error('[WS] Max reconnect attempts reached. Please refresh page.')
            }
          }
          
          ws.onerror = (e) => {
            console.error('[WS] Error:', e)
            // Resolve anyway to not block caller forever, but connection failed
            // Actually, wait for onclose/onopen? 
            // Standard onerror is followed by onclose usually.
          }
        } catch (e) {
          console.error('[WS] Connection Creation Failed', e)
          resolve()
        }
    })
  }

  const disconnect = () => {
    clearTimers()
    if (ws) {
      ws.close(1000, "Client initiated disconnect") // Normal closure
      ws = null
      isConnected.value = false
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    isConnected
  }
}
