<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">发票列表</h1>
      <div class="page-header-actions">
        <el-button @click="fetchInvoices" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="$router.push('/invoices/upload')">
          <el-icon><UploadFilled /></el-icon>
          上传发票
        </el-button>
      </div>
    </div>
    
    <!-- 筛选表单 -->
      <el-card class="filter-form">
      <template #header>
        <span class="card-header-title section-title">筛选条件</span>
      </template>
      <el-form :model="filters" :inline="false" size="default">
        <!-- 默认：销售方独占一行 -->
        <el-form-item label="销售方" class="full-width-item">
          <el-select-v2
            v-model="filters.seller_names"
            multiple
            collapse-tags
            filterable
            clearable
            placeholder="选择销售方"
            :options="sellerOptions"
            style="width: 100%"
          />
        </el-form-item>

        <!-- 默认：购方独占一行 -->
        <el-form-item label="购方" class="full-width-item">
          <el-select-v2
            v-model="filters.purchaser_names"
            multiple
            collapse-tags
            filterable
            clearable
            placeholder="选择购方"
            :options="purchaserOptions"
            style="width: 100%"
          />
        </el-form-item>

        <!-- 更多筛选项 -->
        <template v-if="showMoreFilters">
          <el-row :gutter="32" class="more-filters-row">
            <el-col :span="5">
              <el-form-item label="状态">
                <el-select v-model="filters.status" placeholder="请选择状态" clearable style="width: 100%">
                  <el-option label="全部" value="" />
                  <el-option label="处理中" value="processing" />
                  <el-option label="已完成" value="completed" />
                  <el-option label="失败" value="failed" />
                  <el-option label="已归档" value="archived" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="5">
              <el-form-item label="OCR状态">
                <el-select v-model="filters.ocr_status" placeholder="请选择OCR状态" clearable style="width: 100%">
                  <el-option label="全部" value="" />
                  <el-option label="待处理" value="pending" />
                  <el-option label="识别中" value="processing" />
                  <el-option label="成功" value="success" />
                  <el-option label="失败" value="failed" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="5">
              <el-form-item label="发票类型">
                <el-select v-model="filters.service_types" multiple collapse-tags filterable clearable placeholder="选择类型" style="width: 100%">
                  <el-option
                    v-for="t in filterOptions.service_types"
                    :key="t"
                    :label="t"
                    :value="t"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="9">
              <el-form-item label="包含重复">
                <el-switch v-model="filters.include_duplicates" />
              </el-form-item>
            </el-col>
          </el-row>
        </template>
        
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button @click="showDuplicateManager">去重管理</el-button>
          <el-button type="text" @click="showMoreFilters = !showMoreFilters">{{ showMoreFilters ? '收起' : '更多' }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 发票表格 -->
    <div class="table-container">
      <el-card>
        <template #header>
          <span class="card-header-title section-title">发票列表</span>
        </template>
        <el-table
          v-loading="loading"
          :data="invoices"
          stripe
          @selection-change="handleSelectionChange"
        >
        <el-table-column type="selection" width="55" />
        
        
        <el-table-column prop="seller_name" label="销售方" width="200">
          <template #default="{ row }">
            {{ row.seller_name || '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="purchaser_name" label="购方" width="200">
          <template #default="{ row }">
            {{ row.purchaser_name || '-' }}
          </template>
        </el-table-column>
        

        <el-table-column prop="total_amount" label="金额" width="120">
          <template #default="{ row }">
            <span :class="{ 'amount': hasValidAmount(row.amount_in_figures) }">
              {{ formatAmount(row.amount_in_figures) }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="service_type" label="消费类型" width="120">
          <template #default="{ row }">
            <span v-if="row.service_type" type="success">{{ row.service_type }}</span>
            <span v-else type="info">未知</span>
          </template>
        </el-table-column>

        
        <el-table-column prop="created_at" label="开票日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.invoice_date) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button link size="small" type="primary" @click="openDetail(row)">
                详情
              </el-button>
              <el-button
                v-if="row.ocr_status === 'failed'"
                link size="small"
                @click="retryOCR(row.id)"
              >
                重试
              </el-button>
              <el-button type="success" link size="small" @click="downloadInvoice(row.id, row.original_filename)">
                下载
              </el-button>
              <el-button type="danger" link size="small" @click="deleteInvoice(row.id)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.size"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>
    
    <InvoiceDetailDialog
      v-model="detailDialogVisible"
      :invoice="currentInvoice"
      @saved="fetchInvoices"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TagProps } from 'element-plus'
import { UploadFilled, Warning, Refresh } from '@element-plus/icons-vue'
import { useInvoiceStore } from '../../stores/invoice'
import { downloadInvoice as apiDownloadInvoice, getInvoiceFilterOptions } from '../../api/invoice'
import InvoiceDetailDialog from '../../components/InvoiceDetailDialog.vue'
import type { Invoice, InvoiceFilter } from '../../types/invoice'

const router = useRouter()
const invoiceStore = useInvoiceStore()

const loading = ref(false)
const selectedInvoices = ref<Invoice[]>([])
const showMoreFilters = ref(false)

const filters = reactive<InvoiceFilter & { include_duplicates?: boolean; seller_names?: string[]; purchaser_names?: string[]; service_types?: string[] }>({
  status: '',
  ocr_status: '',
  seller_names: [],
  purchaser_names: [],
  service_types: [],
  include_duplicates: false,
})
const filterOptions = reactive({
  sellers: [] as string[],
  purchasers: [] as string[],
  service_types: [] as string[],
})

// 为虚拟化选择器准备 options 数组
const sellerOptions = computed(() => filterOptions.sellers.map(name => ({ label: name, value: name })))
const purchaserOptions = computed(() => filterOptions.purchasers.map(name => ({ label: name, value: name })))

const fetchFilterOptions = async () => {
  try {
    const resp = await getInvoiceFilterOptions()
    filterOptions.sellers = resp.data.sellers || []
    filterOptions.purchasers = resp.data.purchasers || []
    filterOptions.service_types = resp.data.service_types || []
  } catch (e) {
    // 忽略错误，保持空选项
  }
}

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const invoices = computed(() => invoiceStore.invoices)

// 状态类型映射
const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'duplicate': 'warning',
    'archived': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败',
    'duplicate': '重复',
    'archived': '已归档'
  }
  return statusMap[status] || '未知'
}

type TagType = NonNullable<TagProps['type']>

const getOCRStatusType = (status: string): TagType => {
  const statusMap: Record<string, TagType> = {
    'pending': 'info',
    'processing': 'warning',
    'success': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

const getOCRStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'pending': '待处理',
    'processing': '识别中',
    'success': '成功',
    'failed': '失败'
  }
  return statusMap[status] || '未知'
}

// 格式化日期（仅日期部分）
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  // 如果是 ISO 字符串，直接截取前 10 位（YYYY-MM-DD）
  if (typeof dateString === 'string' && dateString.includes('T')) {
    return dateString.slice(0, 10)
  }
  // 兜底：解析为日期后按 YYYY-MM-DD 输出
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return '-'
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 格式化金额
const formatAmount = (amount: any) => {
  if (amount == null || amount === '' || isNaN(amount)) {
    return '-'
  }
  return `¥${Number(amount).toFixed(2)}`
}

// 检查金额是否有效（用于CSS样式）
const hasValidAmount = (amount: any) => {
  return amount != null && amount !== '' && !isNaN(amount)
}

// 获取发票列表
const fetchInvoices = async () => {
  loading.value = true
  try {
    await invoiceStore.fetchInvoices({
      page: pagination.page,
      size: pagination.size,
      filters
    })
    
    pagination.total = invoiceStore.pagination.total
  } catch (error) {
    ElMessage.error('获取发票列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchInvoices()
}

// 重置筛选
const handleReset = () => {
  Object.assign(filters, {
    status: '',
    ocr_status: '',
    seller_names: [],
    purchaser_names: [],
    service_types: [],
  })
  pagination.page = 1
  fetchInvoices()
}

// 选择变化
const handleSelectionChange = (selection: Invoice[]) => {
  selectedInvoices.value = selection
}

// 分页变化
const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  fetchInvoices()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchInvoices()
}

// 详情弹窗
const detailDialogVisible = ref(false)
const currentInvoice = ref<Invoice | null>(null)
const openDetail = (invoice: Invoice) => {
  currentInvoice.value = invoice
  detailDialogVisible.value = true
}

// 重试OCR
const retryOCR = async (id: string) => {
  try {
    const success = await invoiceStore.retryOCR(id)
    if (success) {
      ElMessage.success('OCR重试已启动')
      fetchInvoices()
    }
  } catch (error) {
    ElMessage.error('重试OCR失败')
  }
}

// 删除发票
const deleteInvoice = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这张发票吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const success = await invoiceStore.deleteInvoice(id)
    if (success) {
      ElMessage.success('删除成功')
      fetchInvoices()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 显示去重管理器（占位：未实现路由时给予提示或跳转列表自身）
const showDuplicateManager = () => {
  ElMessage.info('去重管理尚未实现，敬请期待')
}

onMounted(() => {
  fetchFilterOptions()
  fetchInvoices()
})


// 下载发票原始文件
const downloadInvoice = async (id: string, filename?: string) => {
  try {
    const response = await apiDownloadInvoice(id)
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `${id}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载失败')
  }
}
</script>

 

<style scoped>
.filename {
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.amount {
  font-weight: 600;
  color: var(--el-color-danger);
}

.full-width-item :deep(.el-form-item__content) {
  width: 100%;
}
</style>
