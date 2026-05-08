<script setup>
import { ref, nextTick, watch, computed, onMounted } from 'vue'
import { sendAgentMessage, confirmAgentAction, resetAgentSession } from '@/api/chat'

const props = defineProps({
  conversationId: { type: String, required: true },
  title: { type: String, default: '' },
})

const emit = defineEmits(['rename-conversation'])

// ── 状态 ──
const messageMap = ref({})
const inputText = ref('')
const loading = ref(false)
const listRef = ref(null)
const confirmingId = ref(null) // 正在确认中的消息索引

const messageList = computed(() => messageMap.value[props.conversationId] || [])

// session_id：前端生成，存 localStorage
const SESSION_KEY = 'agent_session_id'

function getSessionId() {
  let sid = localStorage.getItem(SESSION_KEY)
  if (!sid) {
    sid = 'sid-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem(SESSION_KEY, sid)
  }
  return sid
}

function ensureConv() {
  if (!messageMap.value[props.conversationId]) {
    messageMap.value[props.conversationId] = []
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

// ── 发送消息 ──
async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  ensureConv()
  const isFirstMessage = messageMap.value[props.conversationId].length === 0
  messageMap.value[props.conversationId].push({ role: 'user', content: text })

  if (isFirstMessage) {
    const name = text.length > 25 ? text.slice(0, 25) + '...' : text
    emit('rename-conversation', name)
  }

  inputText.value = ''
  scrollToBottom()
  loading.value = true

  try {
    const data = await sendAgentMessage(text, getSessionId())
    messageMap.value[props.conversationId].push({
      role: 'assistant',
      content: data.content || '',
      agentType: data.type,       // 'response' | 'confirmation_needed' | 'error'
      tool: data.tool || null,
      args: data.args || null,
      sources: data.sources || [],
    })
  } catch (e) {
    const msg = e?.code === 'ECONNABORTED'
      ? '请求超时，请稍后重试'
      : '请求失败，请稍后重试'
    messageMap.value[props.conversationId].push({ role: 'assistant', content: msg, agentType: 'error' })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// ── 确认 / 取消 ──
async function handleConfirm(msgIdx) {
  const msg = messageList.value[msgIdx]
  if (!msg || msg.agentType !== 'confirmation_needed') return

  confirmingId.value = msgIdx
  try {
    const data = await confirmAgentAction(getSessionId(), 'confirm')
    // 替换确认消息为最终结果
    messageMap.value[props.conversationId][msgIdx] = {
      role: 'assistant',
      content: data.content || '操作已完成',
      agentType: 'response',
      tool: null,
      args: null,
      sources: [],
    }
  } catch (e) {
    messageMap.value[props.conversationId].push({
      role: 'assistant',
      content: '确认操作失败，请重试',
      agentType: 'error',
    })
  } finally {
    confirmingId.value = null
  }
}

async function handleCancel(msgIdx) {
  const msg = messageList.value[msgIdx]
  if (!msg || msg.agentType !== 'confirmation_needed') return

  confirmingId.value = msgIdx
  try {
    const data = await confirmAgentAction(getSessionId(), 'cancel')
    messageMap.value[props.conversationId][msgIdx] = {
      role: 'assistant',
      content: data.content || '操作已取消',
      agentType: 'response',
      tool: null,
      args: null,
      sources: [],
    }
  } catch (e) {
    messageMap.value[props.conversationId].push({
      role: 'assistant',
      content: '取消失败，请重试',
      agentType: 'error',
    })
  } finally {
    confirmingId.value = null
  }
}

// ── 重置会话 ──
async function handleReset() {
  try {
    await resetAgentSession(getSessionId())
  } catch (e) {
    // 即使请求失败也清除本地状态
  }
  messageMap.value[props.conversationId] = []
  localStorage.removeItem(SESSION_KEY)
  // 生成新 session_id
  const sid = 'sid-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8)
  localStorage.setItem(SESSION_KEY, sid)
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// ── 格式化参数 ──
function formatArgs(args) {
  if (!args) return ''
  const labels = {
    title: '标题', description: '描述', assignee: '指派给',
    priority: '紧急程度', user: '收件人', message: '消息', name: '姓名',
  }
  return Object.entries(args)
    .map(([k, v]) => `${labels[k] || k}: ${v}`)
    .join('\n')
}

watch(() => props.conversationId, () => {
  ensureConv()
  scrollToBottom()
})

watch(messageList, scrollToBottom, { deep: true })

onMounted(() => {
  ensureConv()
})
</script>

<template>
  <div class="chat-root">
    <!-- ── 顶部栏 ── -->
    <header class="chat-topbar">
      <span class="topbar-title">{{ title || '智能助手' }}</span>
      <div class="topbar-actions">
        <span class="topbar-subtitle">Agent 模式 · {{ messageList.length }} 条消息</span>
        <button class="reset-btn" @click="handleReset" title="重置会话">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <polyline points="1 4 1 10 7 10" />
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
          </svg>
        </button>
      </div>
    </header>

    <!-- ── 消息列表 ── -->
    <div ref="listRef" class="chat-messages">
      <!-- 空状态欢迎页 -->
      <div v-if="messageList.length === 0 && !loading" class="welcome">
        <div class="welcome-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
        </div>
        <h2 class="welcome-heading">智能助手 Agent</h2>
        <p class="welcome-desc">我可以帮你创建工单、查询员工信息、发送通知。也可以回答知识库问题。</p>
        <div class="welcome-hints">
          <button class="hint-chip" @click="inputText = '帮我创建一个打印机故障的工单'; handleSend()">创建打印机故障工单</button>
          <button class="hint-chip" @click="inputText = '查询张三的员工信息'; handleSend()">查询员工信息</button>
          <button class="hint-chip" @click="inputText = '给李四发送通知：明天下午2点开会'; handleSend()">发送会议通知</button>
          <button class="hint-chip" @click="inputText = '飞书会议怎么开启字幕'; handleSend()">飞书会议怎么开启字幕？</button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div
        v-for="(msg, idx) in messageList"
        :key="idx"
        class="msg-row"
        :class="msg.role"
      >
        <div class="msg-avatar" v-if="msg.role === 'assistant'">
          <div class="avatar-ai">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
        </div>

        <div class="msg-bubble" :class="[msg.role, msg.agentType === 'error' ? 'error' : '']">
          <div class="msg-content">{{ msg.content }}</div>

          <!-- 工具调用信息 -->
          <div v-if="msg.tool" class="msg-tool-info">
            <div class="tool-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
              <span>{{ msg.tool }}</span>
            </div>
            <pre class="tool-args" v-if="msg.args">{{ formatArgs(msg.args) }}</pre>
          </div>

          <!-- 确认按钮 -->
          <div v-if="msg.agentType === 'confirmation_needed'" class="confirm-actions">
            <button
              class="confirm-btn confirm-yes"
              :disabled="confirmingId === idx"
              @click="handleConfirm(idx)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              同意
            </button>
            <button
              class="confirm-btn confirm-no"
              :disabled="confirmingId === idx"
              @click="handleCancel(idx)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              取消
            </button>
          </div>

          <!-- Sources（知识库模式） -->
          <div v-if="msg.sources && msg.sources.length" class="msg-sources">
            <button class="sources-toggle" @click="msg._srcOpen = !msg._srcOpen">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>参考来源 · {{ msg.sources.length }} 篇文档</span>
              <svg class="sources-chevron" :class="{ open: msg._srcOpen }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            <div v-show="msg._srcOpen" class="sources-list">
              <div v-for="(src, i) in msg.sources" :key="i" class="source-item">
                <div class="source-item-header">
                  <svg class="source-doc-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span class="source-file">{{ src.file }}</span>
                </div>
                <div class="source-content">{{ src.content }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="msg-avatar" v-if="msg.role === 'user'">
          <div class="avatar-user">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="msg-row assistant">
        <div class="msg-avatar">
          <div class="avatar-ai breathing">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
        </div>
        <div class="msg-bubble assistant loading-bubble">
          <div class="typing-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 输入区域 ── -->
    <footer class="chat-input-area">
      <div class="input-shell">
        <textarea
          v-model="inputText"
          class="input-field"
          placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
          :rows="1"
          @keydown="handleKeydown"
        ></textarea>
        <button
          class="send-btn"
          :class="{ active: inputText.trim() && !loading }"
          :disabled="!inputText.trim() || loading"
          @click="handleSend"
        >
          <svg v-if="!loading" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
          <svg v-else class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.2" />
            <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round" />
          </svg>
        </button>
      </div>
      <p class="input-hint">智能助手 · 支持创建工单、查询员工、发送通知、知识问答</p>
    </footer>
  </div>
</template>

<style scoped>
/* ══════════════════════════════════════════════════════════════
   Layout (same as ChatView.vue)
   ══════════════════════════════════════════════════════════════ */

.chat-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8f9fb;
}

.chat-topbar {
  height: 48px;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  z-index: 5;
}
.topbar-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #374151;
}
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.topbar-subtitle {
  font-size: 11.5px;
  color: #9ca3af;
}
.reset-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.15s;
}
.reset-btn:hover {
  color: #6366f1;
  border-color: #c7d2fe;
  background: #f5f3ff;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  padding: 32px 0 16px;
}

/* ── Welcome ── */
.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px 40px;
  text-align: center;
}
.welcome-icon {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-radius: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.12);
}
.welcome-heading {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
  letter-spacing: -0.3px;
}
.welcome-desc {
  font-size: 14px;
  color: #9ca3af;
  margin-bottom: 28px;
  max-width: 400px;
}
.welcome-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 500px;
}
.hint-chip {
  padding: 9px 16px;
  border-radius: 20px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #4b5563;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.hint-chip:hover {
  border-color: #f59e0b;
  color: #f59e0b;
  background: #fffbeb;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.08);
}

/* ── Messages ── */
.msg-row {
  display: flex;
  align-items: flex-start;
  max-width: 900px;
  margin: 0 auto 28px;
  padding: 0 32px;
  gap: 14px;
  animation: msgFadeIn 0.28s ease-out;
}
.msg-row.user {
  justify-content: flex-end;
}
@keyframes msgFadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

.msg-avatar {
  flex-shrink: 0;
}
.avatar-ai,
.avatar-user {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  color: #fff;
}
.avatar-ai {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}
.avatar-user {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

/* ── Bubbles ── */
.msg-bubble {
  max-width: 78%;
  padding: 14px 20px;
  border-radius: 22px;
  font-size: 15px;
  line-height: 1.78;
  word-break: break-word;
  transition: box-shadow 0.2s;
}
.msg-bubble.assistant {
  background: #ffffff;
  color: #1f2937;
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-top-left-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.03);
}
.msg-bubble.assistant:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.msg-bubble.assistant.error {
  border-color: rgba(239, 68, 68, 0.2);
  background: #fef2f2;
}
.msg-bubble.user {
  background: linear-gradient(135deg, #4f6ef6 0%, #3b82f6 100%);
  color: #fff;
  border-top-right-radius: 8px;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
}
.msg-bubble.user:hover {
  box-shadow: 0 3px 14px rgba(59, 130, 246, 0.32);
}
.msg-content {
  white-space: pre-wrap;
}

/* ── Tool info ── */
.msg-tool-info {
  margin-top: 10px;
  padding: 10px 14px;
  background: #fefce8;
  border: 1px solid #fde68a;
  border-radius: 10px;
}
.tool-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #92400e;
  margin-bottom: 6px;
}
.tool-args {
  font-size: 12px;
  color: #78716c;
  white-space: pre-wrap;
  margin: 0;
  font-family: inherit;
}

/* ── Confirm buttons ── */
.confirm-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}
.confirm-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 20px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.confirm-yes {
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
}
.confirm-yes:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
  transform: translateY(-1px);
}
.confirm-no {
  background: #fff;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}
.confirm-no:hover:not(:disabled) {
  border-color: #fca5a5;
  color: #ef4444;
  background: #fef2f2;
}

/* ── Sources ── */
.msg-sources {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f3f4f6;
}
.sources-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 0;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: #9ca3af;
  transition: color 0.15s;
}
.sources-toggle:hover { color: #6b7280; }
.sources-chevron {
  transition: transform 0.2s;
  opacity: 0.5;
}
.sources-chevron.open { transform: rotate(180deg); }
.sources-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  animation: srcFadeIn 0.2s ease-out;
}
@keyframes srcFadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.source-item {
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 8px;
}
.source-item-header {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  font-size: 11.5px;
  color: #6b7280;
}
.source-doc-icon { flex-shrink: 0; opacity: 0.45; }
.source-file {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-content {
  padding: 0 12px 10px;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
}

/* ── Input area ── */
.chat-input-area {
  padding: 12px 24px 20px;
  background: linear-gradient(to top, #f8f9fb 80%, transparent);
  position: relative;
  z-index: 5;
}
.input-shell {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #fff;
  border-radius: 24px;
  padding: 7px 8px 7px 18px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.03);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-shell:focus-within {
  border-color: #fbbf24;
  box-shadow: 0 4px 24px rgba(245, 158, 11, 0.10), 0 0 0 3px rgba(245, 158, 11, 0.06);
}
.input-field {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 14.5px;
  line-height: 1.55;
  padding: 7px 0;
  font-family: inherit;
  color: #1f2937;
  background: transparent;
  min-height: 40px;
  max-height: 140px;
}
.input-field::placeholder { color: #c4c7cd; }
.send-btn {
  width: 38px;
  height: 38px;
  min-width: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: #e5e7eb;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s;
}
.send-btn.active {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  box-shadow: 0 2px 10px rgba(245, 158, 11, 0.3);
}
.send-btn.active:hover {
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.4);
  transform: scale(1.05);
}
.send-btn:disabled { cursor: not-allowed; }
.spinner { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.input-hint {
  text-align: center;
  margin-top: 8px;
  font-size: 11px;
  color: #c4c7cd;
}

/* ── Loading ── */
.loading-bubble {
  min-height: 48px;
  display: flex;
  align-items: center;
}
.typing-dots {
  display: flex;
  gap: 5px;
  align-items: center;
  padding: 4px 0;
}
.typing-dots .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #d1d5db;
  animation: dotBounce 1.3s ease-in-out infinite;
}
.typing-dots .dot:nth-child(1) { animation-delay: 0s; }
.typing-dots .dot:nth-child(2) { animation-delay: 0.15s; }
.typing-dots .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); background: #d1d5db; }
  30% { transform: translateY(-8px); background: #f59e0b; }
}
.avatar-ai.breathing {
  animation: avatarBreath 2s ease-in-out infinite;
}
@keyframes avatarBreath {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.3); }
  50%      { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
}

/* ── Markdown ── */
.msg-bubble.assistant :deep(h1),
.msg-bubble.assistant :deep(h2),
.msg-bubble.assistant :deep(h3) {
  margin: 16px 0 8px;
  font-weight: 600;
  color: #111827;
}
.msg-bubble.assistant :deep(h1) { font-size: 18px; }
.msg-bubble.assistant :deep(h2) { font-size: 16px; }
.msg-bubble.assistant :deep(h3) { font-size: 15px; }
.msg-bubble.assistant :deep(p) { margin: 0 0 8px; }
.msg-bubble.assistant :deep(ul),
.msg-bubble.assistant :deep(ol) { padding-left: 20px; margin: 8px 0; }
.msg-bubble.assistant :deep(li) { margin-bottom: 4px; }
.msg-bubble.assistant :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13.5px;
  color: #e11d48;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}
.msg-bubble.assistant :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 14px 18px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 12px 0;
  font-size: 13px;
  line-height: 1.6;
}
.msg-bubble.assistant :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
  font-size: inherit;
}
.msg-bubble.assistant :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}
.msg-bubble.assistant :deep(th),
.msg-bubble.assistant :deep(td) {
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  text-align: left;
}
.msg-bubble.assistant :deep(th) {
  background: #f9fafb;
  font-weight: 600;
  color: #374151;
}
.msg-bubble.assistant :deep(blockquote) {
  border-left: 3px solid #f59e0b;
  padding-left: 14px;
  margin: 10px 0;
  color: #6b7280;
}
.msg-bubble.assistant :deep(strong) {
  color: #111827;
  font-weight: 600;
}
.msg-bubble.assistant :deep(a) {
  color: #f59e0b;
  text-decoration: none;
}
.msg-bubble.assistant :deep(a:hover) { text-decoration: underline; }
</style>
