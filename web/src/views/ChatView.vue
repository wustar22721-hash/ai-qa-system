<script setup>
import { ref, nextTick, watch, computed } from 'vue'
import { sendMessage } from '@/api/chat'

const props = defineProps({
  conversationId: { type: String, required: true },
  title: { type: String, default: '' },
})

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
  messageMap.value[props.conversationId].push({ role: 'user', content: text })
  inputText.value = ''
  scrollToBottom()

  loading.value = true
  try {
    const { answer, sources } = await sendMessage(text)
    messageMap.value[props.conversationId].push({ role: 'assistant', content: answer, sources })
  } catch (e) {
    const msg = e?.code === 'ECONNABORTED'
      ? '请求超时，AI 正在生成中，请稍后重试'
      : '请求失败，请稍后重试'
    messageMap.value[props.conversationId].push({ role: 'assistant', content: msg })
  } finally {
    loading.value = false
    scrollToBottom()
  }
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
  <div class="chat-container">
    <div class="chat-header">
      <span>{{ title }}</span>
    </div>

    <div ref="listRef" class="chat-list">
      <div
        v-for="(msg, idx) in messageList"
        :key="idx"
        class="message-row"
        :class="msg.role"
      >
        <div class="message-avatar">
          <el-avatar :size="32" v-if="msg.role === 'assistant'">
            <el-icon :size="18"><Cpu /></el-icon>
          </el-avatar>
        </div>
        <div class="message-bubble" :class="msg.role">
          <div class="message-text">{{ msg.content }}</div>
          <div v-if="msg.sources && msg.sources.length" class="message-sources">
            <el-divider />
            <div class="sources-title">
              <el-icon :size="14"><FolderOpened /></el-icon>
              <span>参考来源 ({{ msg.sources.length }})</span>
            </div>
            <el-card
              v-for="(src, i) in msg.sources"
              :key="i"
              class="source-card"
              shadow="none"
              @click="toggleSource(idx, i)"
            >
              <div class="source-header">
                <el-icon :size="14"><Document /></el-icon>
                <span class="source-file">{{ src.file }}</span>
                <el-icon class="source-arrow" :class="{ expanded: expandedMap[`${idx}-${i}`] }">
                  <ArrowDown />
                </el-icon>
              </div>
              <div v-show="expandedMap[`${idx}-${i}`]" class="source-body">
                {{ src.content }}
              </div>
            </el-card>
          </div>
        </div>
        <div class="message-avatar" v-if="msg.role === 'user'">
          <el-avatar :size="32">
            <el-icon :size="18"><UserFilled /></el-icon>
          </el-avatar>
        </div>
      </div>

      <div v-if="loading" class="message-row assistant">
        <div class="message-avatar">
          <el-avatar :size="32">
            <el-icon :size="18"><Cpu /></el-icon>
          </el-avatar>
        </div>
        <div class="message-bubble assistant typing">
          <span class="typing-text">AI 正在思考...</span>
        </div>
      </div>
    </div>

    <div class="chat-footer">
      <div class="input-wrapper">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行"
          @keydown="handleKeydown"
          resize="none"
        />
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!inputText.trim() || loading"
          @click="handleSend"
        >
          <el-icon v-if="!loading"><Promotion /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f7f7f8;
}

.chat-header {
  height: 48px;
  min-height: 48px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 14px;
  font-weight: 500;
  color: #555;
  background: #fff;
  border-bottom: 1px solid #e5e5e6;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  padding: 20px 0;
}

.message-row {
  display: flex;
  align-items: flex-start;
  max-width: 820px;
  margin: 0 auto 20px;
  padding: 0 24px;
  gap: 14px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-avatar {
  flex-shrink: 0;
  margin-top: 2px;
}

.message-bubble {
  max-width: 75%;
  padding: 12px 18px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}

.message-bubble.assistant {
  background: #fff;
  color: #1f2937;
  border: 1px solid #ededee;
  border-top-left-radius: 6px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.message-bubble.user {
  background: #1d6ef5;
  color: #fff;
  border-top-right-radius: 6px;
  box-shadow: 0 1px 3px rgba(29,110,245,0.25);
}

.message-text {
  white-space: pre-wrap;
}

.message-sources {
  margin-top: 10px;
}

.message-sources :deep(.el-divider) {
  margin: 10px 0 12px;
  border-color: #e5e7eb;
}

.sources-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.source-card {
  margin-bottom: 6px;
  cursor: pointer;
  border-radius: 8px;
  border: 1px solid #ebebee;
}

.source-card:last-child {
  margin-bottom: 0;
}

.source-card :deep(.el-card__body) {
  padding: 10px 14px;
}

.source-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #1d6ef5;
  font-weight: 500;
}

.source-arrow {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
  transition: transform 0.2s;
}

.source-arrow.expanded {
  transform: rotate(180deg);
}

.source-body {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f0f0f1;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.55;
  white-space: pre-wrap;
}

.message-bubble.typing {
  display: flex;
  align-items: center;
}

.typing-text {
  color: #909399;
  font-size: 13px;
  animation: blink 1.2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.chat-footer {
  padding: 12px 24px 20px;
  background: #fff;
  border-top: 1px solid #e5e5e6;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  max-width: 800px;
  margin: 0 auto;
}

:deep(.input-wrapper .el-textarea__inner) {
  border-radius: 12px;
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.5;
  background: #f7f7f8;
  border-color: #e0e0e1;
}

:deep(.input-wrapper .el-textarea__inner:focus) {
  border-color: #1d6ef5;
  box-shadow: 0 0 0 2px rgba(29,110,245,0.12);
}

:deep(.input-wrapper .el-button--primary) {
  border-radius: 10px;
  min-width: 38px;
  height: 38px;
}
</style>
