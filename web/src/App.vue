<script setup>
import { ref, computed } from 'vue'
import ChatView from '@/views/ChatView.vue'

const conversations = ref([
  { id: '1', title: '知识库问答' },
])

const currentId = ref('1')

const currentTitle = computed(() =>
  conversations.value.find((c) => c.id === currentId.value)?.title || ''
)

function switchConv(id) {
  currentId.value = id
}

function addConv() {
  const id = String(Date.now())
  conversations.value.push({ id, title: '新对话' })
  currentId.value = id
}

function deleteConv(id, e) {
  e.stopPropagation()
  const idx = conversations.value.findIndex(c => c.id === id)
  if (idx === -1) return
  conversations.value.splice(idx, 1)
  if (currentId.value === id) {
    currentId.value = conversations.value[0]?.id || ''
  }
}

function renameConv(newTitle) {
  const conv = conversations.value.find(c => c.id === currentId.value)
  if (conv) {
    conv.title = newTitle
  }
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo-row">
          <span class="logo-icon">✦</span>
          <span class="logo-text">KBQA</span>
        </div>
        <button class="new-chat-btn" @click="addConv" title="新对话">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>

      <nav class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentId }"
          @click="switchConv(conv.id)"
        >
          <svg class="conv-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span class="conv-title">{{ conv.title }}</span>
          <button class="conv-delete" @click="deleteConv(conv.id, $event)" title="删除对话">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              <line x1="10" y1="11" x2="10" y2="17" />
              <line x1="14" y1="11" x2="14" y2="17" />
            </svg>
          </button>
        </div>
      </nav>

      <div class="sidebar-footer">
        <span class="footer-text">飞书知识库 · RAG 问答</span>
      </div>
    </aside>

    <main class="main-panel">
      <ChatView
        :conversation-id="currentId"
        :title="currentTitle"
        @rename-conversation="renameConv"
      />
    </main>
  </div>
</template>

<style>
/* ── 全局重置（替换 style.css 的内容） ── */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial,
    'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: #f0f2f5;
}

/* ── 滚动条 ── */
::-webkit-scrollbar {
  width: 5px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>

<style scoped>
/* ── Shell ── */
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f6fa 0%, #eef1f6 100%);
}

/* ── 侧边栏 ── */
.sidebar {
  width: 260px;
  min-width: 260px;
  background: #1a1a1e;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 24px rgba(0, 0, 0, 0.08);
  z-index: 10;
  position: relative;
}

.sidebar-header {
  padding: 20px 18px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 9px;
  color: #fff;
  font-size: 15px;
}

.logo-text {
  color: #ececec;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.new-chat-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid #3a3a3f;
  border-radius: 8px;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.15s;
}
.new-chat-btn:hover {
  background: #2a2a30;
  color: #e5e7eb;
  border-color: #52525b;
}

/* ── 会话列表 ── */
.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 10px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 10px;
  cursor: pointer;
  color: #a1a1aa;
  font-size: 13.5px;
  transition: all 0.12s;
  margin-bottom: 1px;
}
.conv-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #d4d4d8;
}
.conv-item.active {
  background: rgba(255, 255, 255, 0.08);
  color: #f4f4f5;
}

.conv-icon {
  flex-shrink: 0;
  opacity: 0.5;
}
.conv-item.active .conv-icon {
  opacity: 0.85;
}

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-delete {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #52525b;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.12s, background 0.12s, color 0.12s;
}
.conv-item:hover .conv-delete {
  opacity: 1;
}
.conv-delete:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

/* ── 侧边栏底部 ── */
.sidebar-footer {
  padding: 14px 18px;
  border-top: 1px solid #27272a;
}
.footer-text {
  font-size: 11px;
  color: #52525b;
}

/* ── 主面板 ── */
.main-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
</style>
