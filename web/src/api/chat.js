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
