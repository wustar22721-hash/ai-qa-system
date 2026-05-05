<script setup>
import { ref, computed } from 'vue'
import ChatView from '@/views/ChatView.vue'

const conversations = ref([
  { id: '1', title: '知识库问答' },
  { id: '2', title: '代码审查助手' },
  { id: '3', title: '文档摘要' },
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
</script>

<template>
  <el-container class="layout">
    <el-aside width="260px" class="sidebar">
      <div class="sidebar-header">
        <span class="logo-text">KBQA</span>
        <el-button class="new-btn" text @click="addConv">
          <el-icon :size="18"><Plus /></el-icon>
        </el-button>
      </div>

      <div class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentId }"
          @click="switchConv(conv.id)"
        >
          <el-icon :size="16"><ChatDotRound /></el-icon>
          <span class="conv-title">{{ conv.title }}</span>
        </div>
      </div>
    </el-aside>

    <el-main class="main-content">
      <ChatView :conversation-id="currentId" :title="currentTitle" />
    </el-main>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100%;
}

.sidebar {
  background-color: #1c1c1e;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #2d2d2f;
}

.logo-text {
  color: #ececec;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}

.new-btn {
  color: #909399;
  padding: 4px;
}

.new-btn:hover {
  color: #ececec;
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #acacac;
  font-size: 14px;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.conv-item:hover {
  background: #2a2a2d;
}

.conv-item.active {
  background: #2a2a2d;
  color: #ececec;
}

.conv-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main-content {
  background-color: #f7f7f8;
  padding: 0;
  overflow: hidden;
}
</style>
