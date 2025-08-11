<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统日志</h1>
      <div class="page-header-actions">
        <el-button @click="fetchLogs" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 筛选器 -->
    <el-card class="filter-form">
      <template #header>
        <span class="card-header-title">筛选条件</span>
      </template>
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="日志级别">
          <el-select v-model="filters.log_level" placeholder="全部" clearable style="width: 120px">
            <el-option label="信息" value="INFO" />
            <el-option label="警告" value="WARNING" />
            <el-option label="错误" value="ERROR" />
            <el-option label="调试" value="DEBUG" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="日志类型">
          <el-select v-model="filters.log_type" placeholder="全部" clearable style="width: 150px">
            <el-option label="用户操作" value="user_action" />
            <el-option label="系统事件" value="system_event" />
            <el-option label="发票处理" value="invoice_processing" />
            <el-option label="邮件处理" value="email_processing" />
            <el-option label="OCR识别" value="ocr_processing" />
            <el-option label="文件上传" value="file_upload" />
            <el-option label="导出操作" value="export_operation" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 350px"
          />
        </el-form-item>
        
        <el-form-item label="搜索">
          <el-input
            v-model="filters.search"
            placeholder="搜索消息内容"
            clearable
            style="width: 200px"
          >
            <template #suffix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="loading">
            搜索
          </el-button>
          
          <el-dropdown @command="handleExport" style="margin-left: 12px;">
            <el-button>
              导出 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="csv">导出CSV</el-dropdown-item>
                <el-dropdown-item command="excel">导出Excel</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志列表 -->
    <div class="table-container">
      <el-card>
        <template #header>
          <span class="card-header-title">日志列表</span>
        </template>
        <el-table
          :data="logs"
          v-loading="loading"
          border
          stripe
        >
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.log_level)" size="small">
              {{ row.log_level }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ getTypeText(row.log_type) }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip />
        
        <el-table-column label="资源" width="150">
          <template #default="{ row }">
            <span v-if="row.resource_type">
              {{ row.resource_type }}
              <span v-if="row.resource_id" class="text-muted">#{{ row.resource_id }}</span>
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        
        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewLogDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
        </el-table>
        
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.current"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="pagination.total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 日志详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="日志详情"
      width="800px"
      :close-on-click-modal="false"
    >
      <div v-if="selectedLog" class="log-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="日志ID">{{ selectedLog.id }}</el-descriptions-item>
          <el-descriptions-item label="日志级别">
            <el-tag :type="getLevelType(selectedLog.log_level)" size="small">
              {{ selectedLog.log_level }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="日志类型">
            <el-tag type="info" size="small">{{ getTypeText(selectedLog.log_type) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(selectedLog.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="资源类型">{{ selectedLog.resource_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="资源ID">{{ selectedLog.resource_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ selectedLog.ip_address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="用户代理" :span="2">
            <div class="user-agent">{{ selectedLog.user_agent || '-' }}</div>
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="mt-16">
          <h4>消息内容</h4>
          <el-input
            :model-value="selectedLog.message"
            type="textarea"
            :rows="3"
            readonly
            class="mt-8"
          />
        </div>
        
        <div v-if="selectedLog.details" class="mt-16">
          <h4>详细信息</h4>
          <el-input
            :model-value="formatDetails(selectedLog.details)"
            type="textarea"
            :rows="8"
            readonly
            class="mt-8"
          />
        </div>
      </div>
      
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, ArrowDown, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getLogs, exportLogsCSV, exportLogsExcel } from '@/api/logs'
import type { LogItem } from '@/types/logs'

const loading = ref(false)
const logs = ref<LogItem[]>([])
const dateRange = ref<string[]>([])
const detailVisible = ref(false)
const selectedLog = ref<LogItem | null>(null)

// 分页配置
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 筛选条件
const filters = reactive({
  log_level: '',
  log_type: '',
  search: ''
})

const getLevelType = (level: string) => {
  switch (level) {
    case 'INFO':
      return 'success'
    case 'WARNING':
      return 'warning'
    case 'ERROR':
      return 'danger'
    case 'DEBUG':
      return 'info'
    default:
      return 'info'
  }
}

const getTypeText = (type: string) => {
  const typeMap: Record<string, string> = {
    'user_action': '用户操作',
    'system_event': '系统事件',
    'invoice_processing': '发票处理',
    'email_processing': '邮件处理',
    'ocr_processing': 'OCR识别',
    'file_upload': '文件上传',
    'export_operation': '导出操作'
  }
  return typeMap[type] || type
}

const formatDateTime = (dateTime: string) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

const formatDetails = (details: any) => {
  if (!details) return ''
  return JSON.stringify(details, null, 2)
}

const handleSearch = () => {
  pagination.current = 1
  fetchLogs()
}

const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  fetchLogs()
}

const handleCurrentChange = (page: number) => {
  pagination.current = page
  fetchLogs()
}

const viewLogDetail = (log: LogItem) => {
  selectedLog.value = log
  detailVisible.value = true
}

const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

const handleExport = async (command: string) => {
  const exportParams = {
    log_level: filters.log_level,
    log_type: filters.log_type,
    search: filters.search,
    date_from: dateRange.value?.[0],
    date_to: dateRange.value?.[1],
    limit: 10000
  }
  try {
    if (command === 'csv') {
      const blob = await exportLogsCSV(exportParams)
      downloadBlob(blob, `system_logs_${Date.now()}.csv`)
    } else if (command === 'excel') {
      const blob = await exportLogsExcel(exportParams)
      downloadBlob(blob, `system_logs_${Date.now()}.xlsx`)
    }
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

// 获取日志数据
const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      pageSize: pagination.pageSize,
      level: filters.log_level,
      module: filters.log_type,
      keyword: filters.search,
      startDate: dateRange.value?.[0],
      endDate: dateRange.value?.[1]
    }
    
    const response = await getLogs(params)
    
    if (response && response.data) {
      logs.value = response.data as LogItem[]
      pagination.total = (response as any).total || 0
    } else {
      logs.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('获取日志列表失败:', error)
    ElMessage.error('获取日志列表失败')
    logs.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

// 初始化
onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.user-agent {
  word-break: break-all;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.log-detail h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
} 
.log-title {
  font-size: var(--font-size-lg);
  font-weight: 500;
  color: var(--el-color-primary);
  margin: 0;
}
</style>