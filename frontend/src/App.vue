<template>
  <div class="chat-container">
    <el-container class="app-container">
      <el-header class="app-header">
        <h2>Text-to-SQL 智能助手</h2>
      </el-header>

      <el-main class="chat-main" ref="chatMain">
        <div class="messages-list">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message-item', msg.role]"
          >
            <div class="message-avatar">
              <el-avatar :icon="msg.role === 'user' ? User : Service" />
            </div>
            <div class="message-content">
              <div v-if="msg.role === 'user'" class="text-content">
                {{ msg.content }}
              </div>
              <div v-else class="bot-content">
                <div class="response-text" v-html="formatResponse(msg.content)"></div>
                
                <div v-if="msg.sql" class="sql-block">
                  <div class="sql-header">Generated SQL:</div>
                  <pre><code>{{ msg.sql }}</code></pre>
                </div>
                
                <div v-if="msg.error" class="error-block">
                  <el-alert :title="msg.error" type="error" :closable="false" show-icon />
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="loading" class="message-item bot loading">
            <div class="message-avatar">
              <el-avatar :icon="Service" />
            </div>
            <div class="message-content">
              <el-icon class="is-loading"><Loading /></el-icon> 
              {{ messages[messages.length - 1]?.currentNode || '正在思考中...' }}
            </div>
          </div>
        </div>
      </el-main>

      <el-footer class="app-footer" height="auto">
        <el-input
          v-model="inputQuery"
          type="textarea"
          :rows="3"
          placeholder="请输入您的问题，例如：查询研发部门有哪些员工"
          @keydown.enter.prevent="sendMessage"
        />
        <div class="footer-actions">
          <el-button type="primary" :icon="Position" :loading="loading" @click="sendMessage">
            发送
          </el-button>
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { User, Service, Position, Loading } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css' // 可以根据需要选择其他主题

// 配置 marked，使其支持 highlight.js
marked.setOptions({
  highlight: function (code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  },
  breaks: true, // 支持回车换行
  gfm: true     // 开启 GitHub 风格的 Markdown (支持表格等)
})

const messages = ref([
  {
    role: 'bot',
    content: '你好！我是 Text-to-SQL 智能助手，可以帮你将自然语言问题转化为 SQL 查询。请问有什么可以帮你的？'
  }
])
const inputQuery = ref('')
const loading = ref(false)
const chatMain = ref(null)

const formatResponse = (text) => {
  if (!text) return ''
  // 使用 marked 渲染 markdown
  return marked.parse(text)
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatMain.value && chatMain.value.$el) {
    const el = chatMain.value.$el
    el.scrollTop = el.scrollHeight
  }
}

const sendMessage = async () => {
  const query = inputQuery.value.trim()
  if (!query) return
  
  // 添加用户消息
  messages.value.push({ role: 'user', content: query })
  inputQuery.value = ''
  scrollToBottom()
  
  loading.value = true
  
  // 创建一个空的 bot 消息对象，用于逐步追加流式响应内容
  const botMessageIndex = messages.value.length
  messages.value.push({
    role: 'bot',
    content: '',
    sql: '',
    error: null,
    currentNode: ''
  })
  
  try {
    // 优先使用环境变量配置的完整地址，如果没有配置，则使用 /api 相对路径通过 Vite 代理转发
    const apiUrl = import.meta.env.VITE_API_BASE_URL ? `${import.meta.env.VITE_API_BASE_URL}/chat` : '/api/chat'
    
    // 使用 fetch 替代 axios 来处理 SSE
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify({ query: query })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      
      // 按双换行符分割 SSE 事件
      const parts = buffer.split('\n\n')
      // 保留最后一个可能不完整的部分在 buffer 中
      buffer = parts.pop()

      for (const part of parts) {
        if (part.startsWith('data: ')) {
          const dataStr = part.substring(6)
          
          if (dataStr === '[DONE]') {
            loading.value = false
            messages.value[botMessageIndex].currentNode = '完成'
            break
          }
          
          try {
            const data = JSON.parse(dataStr)
            
            if (data.error) {
              messages.value[botMessageIndex].error = data.error
              loading.value = false
              break
            }

            // 动态更新气泡状态
            const state = data.state_update
            messages.value[botMessageIndex].currentNode = `正在执行: ${data.node}`
            
            if (state.generated_sql) {
              messages.value[botMessageIndex].sql = state.generated_sql
            }
            if (state.final_response) {
              messages.value[botMessageIndex].content = state.final_response
            }
            if (state.error_message) {
              messages.value[botMessageIndex].error = state.error_message
            }
            
            scrollToBottom()
          } catch (e) {
            console.error('Failed to parse SSE data:', e, dataStr)
          }
        }
      }
    }
  } catch (error) {
    console.error('API Error:', error)
    ElMessage.error('请求失败，请检查后端服务是否启动。')
    messages.value[botMessageIndex].content = '对不起，系统遇到了一些问题，无法回答您的请求。'
    messages.value[botMessageIndex].error = error.message
  } finally {
    loading.value = false
    messages.value[botMessageIndex].currentNode = ''
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  background-color: #f5f7fa;
}

.app-container {
  width: 100%;
  max-width: 900px;
  background-color: #ffffff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #409eff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.app-header h2 {
  margin: 0;
  font-size: 20px;
}

.chat-main {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f9fafc;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 15px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-content {
  max-width: 80%;
}

.text-content, .bot-content {
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.6;
  word-break: break-all;
}

.user .text-content {
  background-color: #409eff;
  color: white;
  border-bottom-right-radius: 0;
}

.bot .bot-content {
  background-color: white;
  border: 1px solid #ebeef5;
  color: #303133;
  border-bottom-left-radius: 0;
}

/* 增强对 markdown 表格和内容的渲染样式 */
:deep(.response-text table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
:deep(.response-text th), :deep(.response-text td) {
  border: 1px solid #dcdfe6;
  padding: 8px 12px;
  text-align: left;
}
:deep(.response-text th) {
  background-color: #f5f7fa;
  font-weight: bold;
}
:deep(.response-text pre) {
  background-color: #282c34;
  color: #abb2bf;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}
:deep(.response-text code) {
  font-family: 'Courier New', Courier, monospace;
}
:deep(.response-text p) {
  margin-top: 0;
  margin-bottom: 10px;
}
:deep(.response-text p:last-child) {
  margin-bottom: 0;
}

.sql-block {
  margin-top: 10px;
  background-color: #282c34;
  border-radius: 6px;
  overflow: hidden;
}

.sql-header {
  background-color: #1d1f23;
  color: #abb2bf;
  padding: 6px 12px;
  font-size: 12px;
  font-family: monospace;
}

.sql-block pre {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
}

.sql-block code {
  color: #e5c07b;
  font-family: 'Courier New', Courier, monospace;
}

.error-block {
  margin-top: 10px;
}

.loading {
  color: #909399;
}

.app-footer {
  padding: 20px;
  border-top: 1px solid #ebeef5;
  background-color: white;
}

.footer-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
</style>
