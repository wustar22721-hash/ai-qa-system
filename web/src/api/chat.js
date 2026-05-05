import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

/**
 * 发送消息，返回 { answer, sources }
 */
export function sendMessage(query) {
  return http.post('/chat', { query }).then((res) => ({
    answer: res.data.answer,
    sources: res.data.sources || [],
  }))
}
