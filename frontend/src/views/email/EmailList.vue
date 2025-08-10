<template>
  <div class="email-list-page">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">邮件列表</h1>
        <div class="page-header-actions">
          <el-button @click="refreshData" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button type="primary" @click="showBatchOperations = !showBatchOperations">
            <el-icon><Operation /></el-icon>
            批量操作
          </el-button>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="stats-grid mb-20" v-if="statistics">
        <div class="stat-card">
          <div class="stat-number">{{ statistics.total_emails }}</div>
          <div class="stat-label">总邮件</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ statistics.emails_with_attachments }}</div>
          <div class="stat-label">有附件</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ statistics.emails_with_invoices }}</div>
          <div class="stat-label">检测到发票</div>
          <div class="stat-change positive">{{ statistics.invoice_detection_rate }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ statistics.emails_without_invoices }}</div>
          <div class="stat-label">未检测到发票</div>
        </div>
      </div>

      <!-- 筛选器 -->
      <el-card class="filter-form">
        <template #header>
          <span class="card-header-title section-title">筛选条件</span>
        </template>
        <el-form :model="filters" inline size="default">
          <el-form-item label="扫描状态">
            <el-select v-model="filters.invoice_scan_status" placeholder="全部" clearable>
              <el-option label="待扫描" value="pending" />
              <!-- 移除已扫描选项，统一由处理状态展示 -->
              <el-option label="无发票" value="no_invoice" />
              <el-option label="有发票" value="has_invoice" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="处理状态">
            <el-select v-model="filters.processing_status" placeholder="全部" clearable>
              <el-option label="未处理" value="unprocessed" />
              <el-option label="处理中" value="processing" />
              <el-option label="已完成" value="completed" />
              <el-option label="处理失败" value="failed" />
            </el-select>
          </el-form-item>
        
          
          <el-form-item label="主题">
            <el-input v-model="filters.subject" placeholder="输入主题关键词" clearable />
          </el-form-item>
          
          
          <el-form-item label="发票">
            <el-select v-model="filters.has_invoice" placeholder="全部" clearable>
              <el-option label="有发票" :value="true" />
              <el-option label="无发票" :value="false" />
            </el-select>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="searchEmails">搜索</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 批量操作面板 -->
      <el-card v-if="showBatchOperations" class="batch-operations">
          <template #header>
            <span class="card-header-title section-title">批量操作</span>
          </template>
        <div class="batch-content">
          <el-alert 
            :title="`已选择 ${selectedEmails.length} 封邮件`"
            type="info"
            :closable="false"
            show-icon
            class="mb-16"
          />
          <div class="action-buttons">
            <el-button 
              @click="batchRescan" 
              :disabled="selectedEmails.length === 0"
              :loading="batchLoading"
            >
              重新扫描
            </el-button>
            <el-button 
              type="danger" 
              @click="batchDelete" 
              :disabled="selectedEmails.length === 0"
              :loading="batchLoading"
            >
              删除记录
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 邮件列表 -->
      <div class="table-container">
        <el-card>
          <template #header>
            <span class="card-header-title section-title">邮件列表</span>
          </template>
          <el-table 
            :data="emails" 
            v-loading="loading"
            @selection-change="handleSelectionChange"
            row-key="id"
            stripe
          >
          <el-table-column type="selection" width="55" />
          
          <el-table-column label="主题" min-width="200">
            <template #default="{ row }">
              <div class="email-subject">
                <span class="subject-text" :title="row.subject">
                  {{ row.subject || '(无主题)' }}
                </span>
                <div class="email-meta">
                  <span class="sender">{{ row.sender }}</span>
                  <span class="date">{{ formatDate(row.date_sent) }}</span>
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="附件" width="80" align="center">
            <template #default="{ row }">
              <el-icon v-if="row.has_attachments" class="attachment-icon">
                <Paperclip />
              </el-icon>
              <span v-if="row.attachment_count > 0" class="attachment-count">
                {{ row.attachment_count }}
              </span>
            </template>
          </el-table-column>
          
          <el-table-column label="发票状态" width="120">
            <template #default="{ row }">
              <el-tag 
                :type="getInvoiceStatusType(row.invoice_scan_status)"
                size="small"
              >
                {{ getInvoiceStatusText(row.invoice_scan_status) }}
              </el-tag>
              <div v-if="row.invoice_count > 0" class="invoice-count">
                {{ row.invoice_count }} 张发票
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="处理状态" width="100">
            <template #default="{ row }">
              <el-tag 
                :type="getProcessingStatusType(row.processing_status)"
                size="small"
              >
                {{ getProcessingStatusText(row.processing_status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column label="扫描时间" width="150">
            <template #default="{ row }">
              <span v-if="row.scanned_at">{{ formatDate(row.scanned_at) }}</span>
              <span v-else class="text-muted">未扫描</span>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" link @click="viewEmailDetail(row)">
                  详情
                </el-button>
                <el-button 
                  size="small" 
                  type="primary" link
                  @click="rescanEmail(row)"
                  :loading="row.rescanning"
                >
                  重扫
                </el-button>
              </div>
            </template>
          </el-table-column>
          </el-table>
          
          <div class="pagination-container">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.size"
              :page-sizes="[10, 20, 50, 100]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </el-card>
      </div>

      <!-- 邮件详情对话框 -->
      <el-dialog 
        v-model="detailDialogVisible" 
        title="邮件详情" 
        width="80%"
        :before-close="closeDetailDialog"
      >
        <EmailDetail 
          v-if="selectedEmail" 
          :email="selectedEmail"
          @refresh="refreshData"
        />
      </el-dialog>
    </div>
  </div>
  
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Operation, Paperclip } from '@element-plus/icons-vue'
import EmailDetail from '../../components/EmailDetail.vue'
import { 
  getEmails, 
  getEmailStatistics, 
  batchOperationEmails 
} from '../../api/emailList'
import type { Email, EmailStatistics } from '../../types/email'
type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined

// 响应式数据
const loading = ref(false)
const batchLoading = ref(false)
const showBatchOperations = ref(false)
const detailDialogVisible = ref(false)
const selectedEmail = ref<Email | null>(null)
const selectedEmails = ref<Email[]>([])

const emails = ref<Email[]>([])
const statistics = ref<EmailStatistics | null>(null)

const filters = reactive({
  invoice_scan_status: '',
  processing_status: '',
  sender: '',
  subject: '',
  has_attachments: null as null | boolean,
  has_invoice: null as null | boolean
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 计算属性
const hasFilters = computed(() => {
  return Object.values(filters).some(value => value !== '' && value !== null)
})

// 方法
const loadEmails = async () => {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: pagination.page,
      size: pagination.size,
      ...filters
    }
    
    // 移除空值
    Object.keys(params).forEach(key => {
      const k = key as keyof typeof params
      if (params[k] === '' || params[k] === null) {
        delete params[k]
      }
    })
    
    const response = await getEmails(params)
    emails.value = response.data.emails
    pagination.total = response.data.total
  } catch (error: any) {
    ElMessage.error('加载邮件列表失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    const response = await getEmailStatistics()
    statistics.value = response.data
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

const refreshData = async () => {
  await Promise.all([loadEmails(), loadStatistics()])
}

const searchEmails = () => {
  pagination.page = 1
  loadEmails()
}

const resetFilters = () => {
  filters.invoice_scan_status = ''
  filters.processing_status = ''
  filters.sender = ''
  filters.subject = ''
  filters.has_attachments = null
  filters.has_invoice = null
  pagination.page = 1
  loadEmails()
}

const handleSelectionChange = (selection: Email[]) => {
  selectedEmails.value = selection
}

const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  loadEmails()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadEmails()
}

const viewEmailDetail = (email: Email) => {
  selectedEmail.value = email
  detailDialogVisible.value = true
}

const closeDetailDialog = () => {
  detailDialogVisible.value = false
  selectedEmail.value = null
}

const rescanEmail = async (email: Email & { rescanning?: boolean }) => {
  try {
    email.rescanning = true
    await batchOperationEmails({
      email_ids: [email.id],
      operation: 'rescan'
    })
    ElMessage.success('重新扫描已启动')
    await loadEmails()
  } catch (error: any) {
    ElMessage.error('重新扫描失败: ' + error.message)
  } finally {
    email.rescanning = false
  }
}

const batchRescan = async () => {
  if (selectedEmails.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要重新扫描选中的 ${selectedEmails.value.length} 封邮件吗？`,
      '确认操作',
      { type: 'warning' }
    )
    
    batchLoading.value = true
    const emailIds = selectedEmails.value.map(email => email.id)
    
    const response = await batchOperationEmails({
      email_ids: emailIds,
      operation: 'rescan'
    })
    
    ElMessage.success(response.data?.message || '操作成功')
    selectedEmails.value = []
    await loadEmails()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('批量重新扫描失败: ' + error.message)
    }
  } finally {
    batchLoading.value = false
  }
}

const batchDelete = async () => {
  if (selectedEmails.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedEmails.value.length} 封邮件记录吗？此操作不可恢复！`,
      '确认删除',
      { type: 'warning' }
    )
    
    batchLoading.value = true
    const emailIds = selectedEmails.value.map(email => email.id)
    
    const response = await batchOperationEmails({
      email_ids: emailIds,
      operation: 'delete'
    })
    
    ElMessage.success(response.data?.message || '操作成功')
    selectedEmails.value = []
    await refreshData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败: ' + error.message)
    }
  } finally {
    batchLoading.value = false
  }
}

// 状态相关方法
const getInvoiceStatusType = (status: string): TagType => {
  const typeMap: Record<string, TagType> = {
    'pending': undefined,
    'no_invoice': 'warning',
    'has_invoice': 'success'
  }
  return typeMap[status]
}

const getInvoiceStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    'pending': '待扫描',
    'no_invoice': '无发票',
    'has_invoice': '有发票'
  }
  return textMap[status] || status
}

const getProcessingStatusType = (status: string): TagType => {
  const typeMap: Record<string, TagType> = {
    'unprocessed': undefined,
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return typeMap[status]
}

const getProcessingStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    'unprocessed': '未处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return textMap[status] || status
}

const formatDate = (dateString: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.email-list-page {
  height: 100%;
}

.email-subject {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.subject-text {
  font-weight: 500;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.attachment-icon {
  color: var(--el-color-primary);
}

.attachment-count {
  margin-left: 4px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.invoice-count {
  font-size: 12px;
  color: var(--el-color-success);
  margin-top: 2px;
}

.batch-content {
  text-align: center;
}

.stat-change.positive {
  color: var(--el-color-success);
  font-size: 12px;
  margin-top: 4px;
}
</style>