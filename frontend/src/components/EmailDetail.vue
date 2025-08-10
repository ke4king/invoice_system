<template>
  <div class="page-container">
    <div class="page-header">
      <h3 class="page-title">{{ email.subject || '(无主题)' }}</h3>
      <div class="page-header-actions">
        <el-button 
          size="small" 
          type="primary" 
          @click="rescanEmail"
          :loading="rescanning"
        >
          重新扫描
        </el-button>
      </div>
    </div>

    <div class="detail-content">
      <!-- 基本信息 -->
      <el-card class="info-card" header="基本信息">
        <div class="info-grid">
          <div class="info-item">
            <label>发送者:</label>
            <span>{{ email.sender }}</span>
          </div>
          <div class="info-item">
            <label>接收者:</label>
            <span>{{ email.recipient }}</span>
          </div>
          <div class="info-item">
            <label>发送时间:</label>
            <span>{{ formatDate(email.date_sent) }}</span>
          </div>
          <div class="info-item">
            <label>接收时间:</label>
            <span>{{ formatDate(email.date_received) }}</span>
          </div>
          <div class="info-item">
            <label>邮件ID:</label>
            <span class="message-id">{{ email.message_id }}</span>
          </div>
        </div>
      </el-card>

      <!-- 状态信息 -->
      <el-card class="info-card" header="状态信息">
        <div class="status-grid">
          <div class="status-item">
            <label>发票扫描状态:</label>
            <el-tag :type="(getInvoiceStatusType(email.invoice_scan_status) as any)">
              {{ getInvoiceStatusText(email.invoice_scan_status) }}
            </el-tag>
          </div>
          <div class="status-item">
            <label>处理状态:</label>
            <el-tag :type="(getProcessingStatusType(email.processing_status) as any)">
              {{ getProcessingStatusText(email.processing_status) }}
            </el-tag>
          </div>
          <div class="status-item">
            <label>发票数量:</label>
            <span class="invoice-count">{{ email.invoice_count }} 张</span>
          </div>
          <div class="status-item">
            <label>扫描时间:</label>
            <span>{{ email.scanned_at ? formatDate(email.scanned_at) : '未扫描' }}</span>
          </div>
        </div>
        
        <div v-if="email.error_message" class="error-message">
          <label>错误信息:</label>
          <el-alert 
            :title="email.error_message" 
            type="error" 
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 附件信息 -->
      <el-card header="附件信息">
        <div class="attachment-summary">
          <span>共 {{ email.attachment_count }} 个附件</span>
          <el-tag v-if="email.has_attachments" type="success" size="small">有附件</el-tag>
          <el-tag v-else type="info" size="small">无附件</el-tag>
        </div>
        
        <div v-if="email.attachment_info && email.attachment_info.length > 0" class="attachment-list">
          <div 
            v-for="(attachment, index) in email.attachment_info" 
            :key="index"
            class="attachment-item"
          >
            <div class="attachment-icon">
              <el-icon v-if="attachment.is_pdf" class="pdf-icon">
                <Document />
              </el-icon>
              <el-icon v-else class="file-icon">
                <Paperclip />
              </el-icon>
            </div>
            <div class="attachment-info">
              <div class="attachment-name">{{ attachment.filename }}</div>
              <div class="attachment-meta">
                <span>{{ attachment.content_type }}</span>
                <span>{{ formatFileSize(attachment.size) }}</span>
                <el-tag v-if="attachment.is_pdf" type="success" size="small">PDF</el-tag>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="no-attachments">
          <el-empty description="无附件" :image-size="60" />
        </div>
      </el-card>

      <!-- 扫描结果 -->
      <el-card v-if="email.scan_result" header="扫描结果">
        <div class="scan-result">
          <pre>{{ JSON.stringify(email.scan_result, null, 2) }}</pre>
        </div>
      </el-card>

      <!-- 邮件正文 -->
      <el-card header="邮件正文">
        <el-tabs v-model="activeTab" v-if="email.body_text || email.body_html">
          <el-tab-pane 
            v-if="email.body_text" 
            label="纯文本" 
            name="text"
          >
            <div class="email-body text-body">
              <pre>{{ email.body_text }}</pre>
            </div>
          </el-tab-pane>
          
          <el-tab-pane 
            v-if="email.body_html" 
            label="HTML" 
            name="html"
          >
            <div class="email-body html-body">
              <div class="html-preview" v-html="sanitizedHtml"></div>
            </div>
          </el-tab-pane>
        </el-tabs>
        
        <div v-else class="no-body">
          <el-empty description="无邮件正文" :image-size="60" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Paperclip } from '@element-plus/icons-vue'
import { batchOperationEmails } from '../api/emailList'
import type { Email } from '../types/email'

interface Props {
  email: Email
}

const props = defineProps<Props>()

const emit = defineEmits(['refresh'])

const rescanning = ref(false)
const activeTab = ref('text')

// 计算属性
const sanitizedHtml = computed(() => {
  if (!props.email.body_html) return ''
  return sanitizeHtml(props.email.body_html)
})

function sanitizeHtml(html: string): string {
  const doc = document.implementation.createHTMLDocument('')
  const div = doc.createElement('div')
  div.innerHTML = html
  // 移除危险标签
  div.querySelectorAll('script,style,iframe').forEach((el) => el.remove())
  // 移除事件属性与 javascript: 协议
  div.querySelectorAll('*').forEach((el) => {
    ;[...el.attributes].forEach((attr) => {
      const name = attr.name.toLowerCase()
      const value = attr.value
      if (name.startsWith('on')) {
        el.removeAttribute(attr.name)
      }
      if ((name === 'href' || name === 'src') && /^\s*javascript:/i.test(value)) {
        el.removeAttribute(attr.name)
      }
    })
  })
  return div.innerHTML
}

// 方法
const rescanEmail = async () => {
  try {
    rescanning.value = true
    await batchOperationEmails({
      email_ids: [props.email.id],
      operation: 'rescan'
    })
    ElMessage.success('重新扫描已启动')
    emit('refresh')
  } catch (error) {
    const err = error as any
    ElMessage.error('重新扫描失败: ' + (err?.message || '未知错误'))
  } finally {
    rescanning.value = false
  }
}

const formatDate = (dateString?: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getInvoiceStatusType = (status: string) => {
  const typeMap: Record<string, string> = {
    pending: '',
    no_invoice: 'warning',
    has_invoice: 'success'
  }
  return typeMap[status] || ''
}

const getInvoiceStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    pending: '待扫描',
    no_invoice: '无发票',
    has_invoice: '有发票'
  }
  return textMap[status] || status
}

const getProcessingStatusType = (status: string) => {
  const typeMap: Record<string, string> = {
    unprocessed: '',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || ''
}

const getProcessingStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    unprocessed: '未处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}
</script>

<style scoped>
.email-detail {
  max-height: 80vh;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--el-border-color);
}

.detail-header h3 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 18px;
  max-width: 70%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card {
  margin-bottom: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.info-item label {
  font-weight: 500;
  min-width: 80px;
  flex-shrink: 0;
}

.message-id {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-item label {
  font-weight: 500;
  min-width: 100px;
  flex-shrink: 0;
}

.invoice-count {
  font-weight: 500;
  color: var(--el-color-success);
}

.error-message {
  margin-top: 15px;
}

.error-message label {
  display: block;
  font-weight: 500;
  margin-bottom: 10px;
}

.attachment-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  font-weight: 500;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
}

.attachment-icon {
  flex-shrink: 0;
}

.pdf-icon {
  color: var(--el-color-danger);
  font-size: 20px;
}

.file-icon {
  font-size: 20px;
}

.attachment-info {
  flex: 1;
  min-width: 0;
}

.attachment-name {
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.scan-result {
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  padding: 15px;
  max-height: 300px;
  overflow-y: auto;
}

.scan-result pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.email-body {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 15px;
}

.text-body pre {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.html-preview {
  line-height: 1.6;
}

.html-preview :deep(a) {
  color: var(--el-color-primary);
  text-decoration: none;
}

.html-preview :deep(a:hover) {
  text-decoration: underline;
}
</style>