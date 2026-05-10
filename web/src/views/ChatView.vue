<script setup>
import { ref, nextTick, watch, computed } from 'vue'
import { streamChat } from '@/api/chat'

const props = defineProps({
  conversationId: { type: String, required: true },
  title: { type: String, default: '' },
})

const emit = defineEmits(['rename-conversation'])

const messageMap = ref({})
const expandedMaps = ref({})
const inputText = ref('')
const loading = ref(false)
const listRef = ref(null)

const messageList = computed(() => messageMap.value[props.conversationId] || [])
const expandedMap = computed(() => expandedMaps.value[props.conversationId] || {})

function ensureConv() {
  if (!messageMap.value[props.conversationId]) {
    messageMap.value[props.conversationId] = []
    expandedMaps.value[props.conversationId] = {}
  }
}

function toggleSource(msgIdx, srcIdx) {
  ensureConv()
  const key = `${msgIdx}-${srcIdx}`
  expandedMaps.value[props.conversationId][key] = !expandedMaps.value[props.conversationId][key]
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  ensureConv()
  const isFirstMessage = messageMap.value[props.conversationId].length === 0
  messageMap.value[props.conversationId].push({ role: 'user', content: text })

  // 首次提问时自动命名会话
  if (isFirstMessage && props.title === '新对话' || isFirstMessage && !props.title) {
    const name = text.length > 25 ? text.slice(0, 25) + '...' : text
    emit('rename-conversation', name)
  }

  inputText.value = ''
  scrollToBottom()

  // 取最近 3 轮对话（6 条，不含当前消息）作为改写上下文
  const prevMsgs = messageMap.value[props.conversationId].slice(0, -1)
  const history = prevMsgs.slice(-6).map(({ role, content }) => ({ role, content }))

  // 插入空的 assistant 消息，后续逐 token 填充
  const msgs = messageMap.value[props.conversationId]
  msgs.push({ role: 'assistant', content: '' })
  const aiMsg = msgs[msgs.length - 1]

  loading.value = true

  await streamChat(text, history, {
    onToken(token) {
      aiMsg.content += token
      loading.value = false  // 收到第一个 token 就结束 loading
      scrollToBottom()
    },
    onDone(sources) {
      aiMsg.sources = sources
      loading.value = false
      scrollToBottom()
    },
    onError(_err) {
      if (!aiMsg.content) {
        aiMsg.content = '请求失败，请稍后重试'
      }
      loading.value = false
    },
  })
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

watch(() => props.conversationId, () => {
  ensureConv()
  scrollToBottom()
})

watch(messageList, scrollToBottom, { deep: true })
</script>

<template>
  <div class="chat-root">
    <!-- ── 顶部栏（弱化） ── -->
    <header class="chat-topbar">
      <span class="topbar-title">{{ title || '知识库问答' }}</span>
      <span class="topbar-subtitle">基于飞书帮助文档 · {{ messageList.length }} 条消息</span>
    </header>

    <!-- ── 消息列表 ── -->
    <div ref="listRef" class="chat-messages">
      <!-- 空状态欢迎页 -->
      <div v-if="messageList.length === 0 && !loading" class="welcome">
        <div class="welcome-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            <line x1="9" y1="10" x2="15" y2="10" />
            <line x1="12" y1="7" x2="12" y2="13" />
          </svg>
        </div>
        <h2 class="welcome-heading">飞书知识库 AI 助手</h2>
        <p class="welcome-desc">基于飞书帮助文档的智能问答系统，随时问我飞书的任何功能</p>
        <div class="welcome-hints">
          <button class="hint-chip" @click="inputText = '如何创建飞书群组'; handleSend()">如何创建飞书群组？</button>
          <button class="hint-chip" @click="inputText = '怎么设置考勤打卡规则'; handleSend()">怎么设置考勤打卡规则？</button>
          <button class="hint-chip" @click="inputText = '视频会议怎么录制'; handleSend()">视频会议怎么录制？</button>
          <button class="hint-chip" @click="inputText = '飞书管理后台如何添加管理员'; handleSend()">如何添加管理员？</button>
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

        <div class="msg-bubble" :class="msg.role">
          <div class="msg-content">{{ msg.content }}</div>

          <!-- Sources（折叠，弱化） -->
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
              <div
                v-for="(src, i) in msg.sources"
                :key="i"
                class="source-item"
                @click="toggleSource(idx, i)"
              >
                <div class="source-item-header">
                  <svg class="source-doc-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span class="source-file">{{ src.file }}</span>
                  <svg class="source-chevron-sm" :class="{ open: expandedMap[`${idx}-${i}`] }" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </div>
                <div v-show="expandedMap[`${idx}-${i}`]" class="source-content">
                  {{ src.content }}
                </div>
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

    <!-- ── 输入区域（固定底部，浮层感） ── -->
    <footer class="chat-input-area">
      <div class="input-shell">
        <textarea
          v-model="inputText"
          class="input-field"
          placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
          :rows="1"
          @keydown="handleKeydown"
          ref="inputRef"
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
      <p class="input-hint">KBQA 基于飞书帮助文档，答案仅供参考</p>
    </footer>
  </div>
</template>

<style scoped>
/* ══════════════════════════════════════════════════════════════
   Phase 1: 整体布局
   ══════════════════════════════════════════════════════════════ */

.chat-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8f9fb;
}

/* ── 顶部栏（弱化） ── */
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
.topbar-subtitle {
  font-size: 11.5px;
  color: #9ca3af;
}

/* ── 消息列表区 ── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  padding: 32px 0 16px;
}

/* ── 空状态欢迎页 ── */
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
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
  border-radius: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.08);
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
  border-color: #6366f1;
  color: #6366f1;
  background: #f5f3ff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.08);
}

/* ── 消息行 ── */
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
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ── Avatar ── */
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
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}
.avatar-user {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

/* ══════════════════════════════════════════════════════════════
   Phase 2: 消息气泡
   ══════════════════════════════════════════════════════════════ */

.msg-bubble {
  max-width: 78%;
  padding: 14px 20px;
  border-radius: 22px;
  font-size: 15px;
  line-height: 1.78;
  word-break: break-word;
  transition: box-shadow 0.2s;
}

/* AI 气泡：白底 + 浅阴影 */
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

/* 用户气泡：蓝色渐变 */
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

/* ══════════════════════════════════════════════════════════════
   Phase 3: Sources 区域（弱化、折叠）
   ══════════════════════════════════════════════════════════════ */

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
.sources-toggle:hover {
  color: #6b7280;
}
.sources-chevron {
  transition: transform 0.2s;
  opacity: 0.5;
}
.sources-chevron.open {
  transform: rotate(180deg);
}

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
  cursor: pointer;
  transition: all 0.15s;
}
.source-item:hover {
  background: #f3f4f6;
  border-color: #e5e7eb;
}

.source-item-header {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  font-size: 11.5px;
  color: #6b7280;
}
.source-doc-icon {
  flex-shrink: 0;
  opacity: 0.45;
}
.source-file {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-chevron-sm {
  flex-shrink: 0;
  opacity: 0.4;
  transition: transform 0.2s;
}
.source-chevron-sm.open {
  transform: rotate(180deg);
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

/* ══════════════════════════════════════════════════════════════
   Phase 4: 输入区域（浮层、大圆角）
   ══════════════════════════════════════════════════════════════ */

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
  border-color: #a5b4fc;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.10), 0 0 0 3px rgba(99, 102, 241, 0.06);
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
.input-field::placeholder {
  color: #c4c7cd;
}

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
  background: linear-gradient(135deg, #6366f1, #4f6ef6);
  color: #fff;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.3);
}
.send-btn.active:hover {
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
  transform: scale(1.05);
}
.send-btn:disabled {
  cursor: not-allowed;
}

.spinner {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.input-hint {
  text-align: center;
  margin-top: 8px;
  font-size: 11px;
  color: #c4c7cd;
}

/* ══════════════════════════════════════════════════════════════
   Phase 5: Loading 动画（typing dots）
   ══════════════════════════════════════════════════════════════ */

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
  0%, 60%, 100% {
    transform: translateY(0);
    background: #d1d5db;
  }
  30% {
    transform: translateY(-8px);
    background: #6366f1;
  }
}

/* Avatar 呼吸动画 */
.avatar-ai.breathing {
  animation: avatarBreath 2s ease-in-out infinite;
}
@keyframes avatarBreath {
  0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.3); }
  50%      { box-shadow: 0 0 0 8px rgba(99, 102, 241, 0); }
}

/* ══════════════════════════════════════════════════════════════
   Phase 6: Markdown 细节美化
   ══════════════════════════════════════════════════════════════ */

/* 针对 AI 气泡内 markdown 样式的深层定制 */
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

.msg-bubble.assistant :deep(p) {
  margin: 0 0 8px;
}
.msg-bubble.assistant :deep(ul),
.msg-bubble.assistant :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}
.msg-bubble.assistant :deep(li) {
  margin-bottom: 4px;
}

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
  border-left: 3px solid #6366f1;
  padding-left: 14px;
  margin: 10px 0;
  color: #6b7280;
}

.msg-bubble.assistant :deep(strong) {
  color: #111827;
  font-weight: 600;
}

.msg-bubble.assistant :deep(a) {
  color: #6366f1;
  text-decoration: none;
}
.msg-bubble.assistant :deep(a:hover) {
  text-decoration: underline;
}
</style>
