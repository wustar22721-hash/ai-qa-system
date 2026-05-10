import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

/**
 * 发送消息到 RAG 知识库，返回 { answer, sources }
 * @param {string} query  - 用户问题
 * @param {Array<{role: string, content: string}>} [history] - 最近 N 轮对话历史
 */
export function sendMessage(query, history) {
  return http.post('/chat', { query, history: history || undefined }).then((res) => ({
    answer: res.data.answer,
    sources: res.data.sources || [],
  }))
}

/**
 * 流式发送消息到 RAG 知识库，通过 SSE 逐 token 推送
 * @param {string} query  - 用户问题
 * @param {Array} history - 最近 N 轮对话历史
 * @param {{onToken, onDone, onError}} callbacks
 *   onToken(text)  每次收到新 token 时调用
 *   onDone(sources) 流结束时调用，sources 为引用来源数组
 *   onError(err)   连接或解析出错时调用
 */
export async function streamChat(query, history, { onToken, onDone, onError }) {
  const controller = new AbortController()

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, history: history || undefined }),
      signal: controller.signal,
    })

    if (!response.ok) {
      onError(new Error(`HTTP ${response.status}`))
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'token') {
            onToken(event.content)
          } else if (event.type === 'done') {
            onDone(event.sources || [])
          }
        } catch {
          // 忽略 JSON 解析错误（不完整的数据行）
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      onError(err)
    }
  } finally {
    controller.abort()
  }
}

/**
 * 发送消息到 Agent，返回完整响应对象
 */
export function sendAgentMessage(query, sessionId) {
  return http.post('/agent/chat', { query, session_id: sessionId }).then((res) => res.data)
}

/**
 * 确认或取消 Agent 的待确认操作
 */
export function confirmAgentAction(sessionId, action) {
  return http.post('/agent/confirm', { session_id: sessionId, action }).then((res) => res.data)
}

/**
 * 重置 Agent 会话
 */
export function resetAgentSession(sessionId) {
  return http.post('/agent/reset', null, { params: { session_id: sessionId } }).then((res) => res.data)
}
