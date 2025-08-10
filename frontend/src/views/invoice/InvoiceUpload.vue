<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">发票上传</h1>
    </div>
    
    <el-card>
      <el-row :gutter="20" class="upload-grid">
        <el-col :xs="24" :md="14" class="upload-col">
          <el-upload
              ref="uploadRef"
              class="upload-surface"
              drag
              :action="uploadUrl"
              :headers="uploadHeaders"
              :before-upload="beforeUpload"
              :on-success="handleSuccess"
              :on-error="handleError"
              :show-file-list="false"
              :disabled="uploadDisabled"
              accept=".pdf"
            >
              <el-icon class="el-icon--upload">
                <upload-filled />
              </el-icon>
              <div class="el-upload__text">
                将 PDF 文件拖到此处，或<em> 点击上传</em>
                <div class="el-upload__tip upload-tips">
                  <el-tag size="small" effect="light">PDF</el-tag>
                  <el-tag size="small" effect="light">≤ 10MB</el-tag>
                  <el-tag size="small" effect="light">推荐单页</el-tag>
                </div>
              </div>
          </el-upload>
        </el-col>
        <el-col :xs="24" :md="10" class="guides-col">
          <div class="guides-pane">
            <div class="guides-card">
              <div class="guides-title">上传须知</div>
              <ul class="guides-list">
                <li>仅支持 PDF 格式，大小不超过 10MB。</li>
                <li>建议上传清晰、完整的单页发票，以提升识别准确率。</li>
                <li>上传后系统会自动启动 OCR 识别，识别完成后可在列表中查看。</li>
              </ul>
            </div>

            <div v-if="uploadedFiles.length > 0" class="recent-card">
              <div class="guides-title">最近上传</div>
              <div class="upload-list">
                <div
                  v-for="file in uploadedFiles"
                  :key="file.id"
                  class="upload-item"
                >
                  <div class="file-info">
                    <el-icon><Document /></el-icon>
                    <span class="filename">{{ file.filename }}</span>
                  </div>
                  <div class="file-status">
                    <el-tag :type="getStatusType(file.status)">
                      {{ getStatusText(file.status) }}
                    </el-tag>
                  </div>
                  <div class="file-actions">
                    <el-button 
                      v-if="file.id" 
                      size="small" 
                      @click="viewInvoice(file.id)"
                    >
                      查看
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadProps, type UploadRawFile, type TagProps } from 'element-plus'
import { UploadFilled, Document, ArrowLeft } from '@element-plus/icons-vue'
  import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()

interface UploadedFile {
  id: string
  filename: string
  status: string
  message: string
}

const uploadRef = ref()
const uploadedFiles = ref<UploadedFile[]>([])
const uploadDisabled = ref(false)

const uploadUrl = computed(() => '/api/v1/invoices/upload')
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${userStore.token}`
}))

const beforeUpload: UploadProps['beforeUpload'] = (rawFile: UploadRawFile) => {
  // 检查文件类型
  if (!rawFile.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.error('只能上传PDF文件')
    return false
  }
  
  // 检查文件大小 (10MB)
  if (rawFile.size > 10 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过10MB')
    return false
  }
  
  return true
}

const handleSuccess = (response: any, uploadFile: any) => {
  ElMessage.success('发票上传成功，正在进行OCR识别')
  
  uploadedFiles.value.unshift({
    id: response.id,
    filename: uploadFile.name,
    status: response.status,
    message: response.message
  })
  
  // 3秒后跳转到发票列表
  setTimeout(() => {
    router.push('/invoices')
  }, 3000)
}

const handleError: UploadProps['onError'] = (error: any, uploadFile: any) => {
  // 优先从响应体读取后端返回
  const resp = uploadFile?.response
  const detail = (resp && typeof resp === 'object') ? (resp.detail || resp.message) : undefined
  const rawMsg = typeof detail === 'object' ? detail?.message : detail
  
  // 识别409重复
  const isConflict = (error?.status === 409) || (error?.message?.includes?.('409')) || (rawMsg?.includes?.('重复'))
  if (isConflict) {
    // 提取已存在发票ID供跳转
    const existingId = (
      (typeof detail === 'object' && detail?.existing_invoice_id) ||
      resp?.existing_invoice_id ||
      error?.response?.data?.detail?.existing_invoice_id ||
      error?.response?.data?.existing_invoice_id ||
      undefined
    )

    if (existingId) {
      ElMessageBox.confirm(
        rawMsg || '该发票已存在，是否前往查看？',
        '提示',
        { confirmButtonText: '查看', cancelButtonText: '取消', type: 'warning' }
      ).then(() => {
        router.push(`/invoices/${existingId}`)
      }).catch(() => {/* 用户取消 */})
    } else {
      ElMessage.warning(rawMsg || '该发票已存在，无需重复上传')
    }
    return
  }

  console.error('上传失败:', error)
  ElMessage.error(rawMsg || '发票上传失败，请重试')
}

type TagType = NonNullable<TagProps['type']>
const getStatusType = (status: string): TagType => {
  const statusMap: Record<string, TagType> = {
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return statusMap[status] || '未知'
}

const viewInvoice = (id: string) => {
  router.push(`/invoices/${id}`)
}
</script>

<style scoped>
.upload-grid { align-items: flex-start; }


.upload-surface {
  margin-bottom: 8px;
  /* remove outer frame from el-upload root to avoid double borders */
  border: none !important;
  background: transparent;
  box-shadow: none;
}

/* Ensure the drag box aligns visually with the guides card */
.upload-col :deep(.el-upload),
.upload-col :deep(.el-upload-dragger) {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Drag area visual */

:deep(.el-upload-dragger) {
  width: 100%;
  max-width: 620px;
  height: 320px;
  border-radius: 12px;
  margin: 0 auto;
  background-color: var(--el-fill-color-light);
  border: 1.5px dashed var(--el-border-color);
  box-shadow: 0 2px 8px 0 rgb(0 0 0 / 4%);
  transition: border-color .2s ease, background-color .2s ease, box-shadow .2s ease;
  padding: 20px 24px;
}

/* Subtle emphasis on hover and while dragging */
.upload-surface :deep(.el-upload-dragger:hover),
.upload-surface :deep(.is-dragover .el-upload-dragger) {
  border-color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
  box-shadow: 0 6px 18px 0 rgb(0 0 0 / 8%);
}

/* Accent the upload icon and text slightly */
.upload-surface :deep(.el-icon--upload) {
  color: var(--el-color-primary);
}
.upload-surface :deep(.el-upload__text) {
  color: var(--el-text-color-regular);
}

.upload-tips { display: flex; gap: 8px; justify-content: center; margin-top: 12px; flex-wrap: wrap; }
.muted { color: var(--el-text-color-secondary); margin-top: 6px; }

.guides-pane { display: flex; flex-direction: column; gap: 16px; }
.guides-card, .recent-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px 18px;
}
.guides-title { font-weight: 600; margin-bottom: 10px; color: var(--el-text-color-primary); }
.guides-list { margin: 0; padding-left: 16px; color: var(--el-text-color-regular); }
.guides-list li { margin-bottom: 6px; }

.upload-list { display: flex; flex-direction: column; gap: 8px; }
.upload-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.file-info { display: flex; align-items: center; gap: 8px; }
.filename { font-size: 14px; color: var(--el-text-color-primary); }

@media (max-width: 768px) {
  :deep(.el-upload-dragger) { height: 220px; }
}
</style>