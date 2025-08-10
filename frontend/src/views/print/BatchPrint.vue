<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">批量打印</h1>
      <div class="page-header-actions">
        <el-button @click="refreshSelectedInvoices" :loading="invoiceStore.loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <!-- 发票选择区域 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="section-title">选择发票</span>
              <div class="header-actions">
                <el-button size="small" @click="selectAll">全选</el-button>
                <el-button size="small" @click="clearSelection">清空</el-button>
                <el-button 
                  size="small" 
                  type="primary" 
                  :disabled="selectedInvoices.length === 0"
                  @click="refreshSelectedInvoices"
                >
                  刷新选中项
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="invoice-selection">
            <!-- 筛选条件 -->
            <div class="filter-section mb-20">
              <el-form :model="filters" :inline="true" size="small">
                <el-form-item label="状态">
                  <el-select v-model="filters.status" placeholder="选择状态" clearable>
                    <el-option label="全部" value="" />
                    <el-option label="已完成" value="completed" />
                    <el-option label="处理中" value="processing" />
                  </el-select>
                </el-form-item>
                
                <el-form-item label="销售方">
                  <el-input
                    v-model="filters.seller_name"
                    placeholder="输入销售方名称"
                    clearable
                    class="w-180"
                  />
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="handleSearch">查询</el-button>
                </el-form-item>
              </el-form>
            </div>
            
            <!-- 发票列表（仅列表区域可滚动） -->
            <div class="invoice-list" v-loading="invoiceStore.loading">
              <div v-if="availableInvoices.length === 0" class="empty-state">
                <el-empty description="没有可打印的发票" />
              </div>
              
              <div v-else class="invoice-items">
                <div
                  v-for="invoice in availableInvoices"
                  :key="invoice.id"
                  class="invoice-item"
                  :class="{ selected: isSelected(invoice.id) }"
                  @click="toggleSelection(invoice.id)"
                >
                  
                  <div class="invoice-info">
                    <div class="invoice-title">
                      {{ invoice.seller_name || '未知销售方' }}
                    </div>
                    <div class="invoice-meta">
                      <span class="filename">{{ invoice.original_filename }}</span>
                      <span class="amount">¥{{ invoice.total_amount || 0 }}</span>
                    </div>
                    <div class="invoice-status">
                      <el-tag size="small" :type="getStatusType(invoice.status) as any">
                        {{ getStatusText(invoice.status) }}
                      </el-tag>
                      <span class="service-type">{{ invoice.service_type || '未分类' }}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 分页 -->
              <div class="pagination-wrapper" v-if="pagination.total > 0">
                <el-pagination
                  v-model:current-page="pagination.page"
                  v-model:page-size="pagination.size"
                  :total="pagination.total"
                  :page-sizes="[10, 20, 50]"
                  layout="total, sizes, prev, pager, next"
                  small
                  @size-change="handleSizeChange"
                  @current-change="handleCurrentChange"
                />
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 打印配置区域 -->
      <el-col :span="10">
        <el-card class="sticky-card">
          <template #header>
            <span class="section-title">打印配置</span>
          </template>
          
          <div class="print-config">
            <!-- 选中的发票统计 -->
            <div class="selection-summary mb-20">
              <el-alert
                :title="`已选择 ${selectedInvoices.length} 张发票`"
                type="info"
                :closable="false"
                show-icon
              />
            </div>
            
            <!-- 打印设置表单 -->
            <el-form
              ref="printFormRef"
              :model="printConfig"
              :rules="printRules"
              label-width="100px"
              size="default"
            >
              <el-form-item label="发票类型" prop="invoice_type">
                <el-select v-model="printConfig.invoice_type" class="w-full">
                  <el-option
                    v-for="type in printStore.invoiceTypes"
                    :key="type.value"
                    :label="type.label"
                    :value="type.value"
                  >
                    <div>
                      <div>{{ type.label }}</div>
                      <div class="option-desc">{{ type.description }}</div>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              
              <el-form-item label="打印布局" prop="layout">
                <el-select v-model="printConfig.layout" class="w-full">
                  <el-option
                    v-for="layout in availableLayouts"
                    :key="layout.value"
                    :label="layout.label"
                    :value="layout.value"
                  >
                    <div>
                      <div>{{ layout.label }}</div>
                      <div class="option-desc">{{ layout.description }}</div>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              
              <el-form-item label="显示选项">
                <el-checkbox v-model="printConfig.show_dividers">
                  显示分割线
                </el-checkbox>
                <el-checkbox v-model="printConfig.sort_by_type">
                  按消费类型排序
                </el-checkbox>
                <el-checkbox v-model="printConfig.update_status">
                  打印后将状态标记为“已打印”
                </el-checkbox>
              </el-form-item>
            </el-form>
            
            <!-- 预览信息 -->
            <div v-if="printStore.hasPreviewData" class="preview-info mb-20">
              <el-descriptions title="打印预览" :column="1" size="small" border>
                <el-descriptions-item label="发票总数">
                  {{ printStore.previewData?.total_invoices }}
                </el-descriptions-item>
                <el-descriptions-item label="预计页数">
                  {{ printStore.previewData?.total_pages }}
                </el-descriptions-item>
                <el-descriptions-item label="布局信息">
                  {{ printStore.previewData?.layout_info }}
                </el-descriptions-item>
              </el-descriptions>
              
              <div v-if="printStore.previewData?.invoices_by_type" class="type-summary mt-10">
                <div class="summary-title">按类型统计：</div>
                <el-tag
                  v-for="(count, type) in printStore.previewData.invoices_by_type"
                  :key="type"
                  size="small"
                  class="type-tag"
                >
                  {{ type }}: {{ count }}张
                </el-tag>
              </div>
            </div>
            
            <!-- 操作按钮 -->
            <div class="action-buttons">
              <el-button
                type="info"
                :loading="printStore.loading"
                :disabled="selectedInvoices.length === 0"
                @click="handlePreview"
              >
                预览
              </el-button>
              
              <el-button
                type="primary"
                :loading="printStore.loading"
                :disabled="selectedInvoices.length === 0"
                @click="handlePrint"
              >
                生成PDF
              </el-button>
              
              <el-button
                :loading="printStore.loading"
                :disabled="selectedInvoices.length === 0"
                @click="handleBrowserPrint"
              >
                浏览器打印
              </el-button>
            </div>
          </div>
        </el-card>
        
        <!-- 批量状态更新 -->
        <el-card class="mt-20 sticky-card">
          <template #header>
            <span class="section-title">批量操作</span>
          </template>
          
          <div class="batch-operations">
            <el-form :inline="true" size="small">
              <el-form-item label="更新状态">
                <el-select v-model="batchStatus" placeholder="选择状态" class="w-120"
                >
                  <el-option
                    v-for="status in printStore.statusOptions"
                    :key="status.value"
                    :label="status.label"
                    :value="status.value"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item>
                <el-button
                  size="small"
                  :disabled="selectedInvoices.length === 0 || !batchStatus"
                  @click="handleBatchStatusUpdate"
                >
                  批量更新
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useInvoiceStore } from '../../stores/invoice'
import { usePrintStore } from '../../stores/print'
import type { Invoice } from '../../types/invoice'

const invoiceStore = useInvoiceStore()
const printStore = usePrintStore()

const selectedInvoices = ref<string[]>([])
const batchStatus = ref('')
const printFormRef = ref<FormInstance>()

const filters = reactive({
  status: '',
  seller_name: ''
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const printConfig = reactive({
  layout: '4_per_page',
  invoice_type: 'normal',
  show_dividers: true,
  sort_by_type: true,
  update_status: false
})

const printRules: FormRules = {
  layout: [
    { required: true, message: '请选择打印布局', trigger: 'change' }
  ],
  invoice_type: [
    { required: true, message: '请选择发票类型', trigger: 'change' }
  ]
}

// 计算属性
const availableInvoices = computed(() => invoiceStore.invoices)

// 根据发票类型过滤可用布局
const availableLayouts = computed(() => {
  return printStore.getLayoutsForType(printConfig.invoice_type)
})

// 监听发票类型变化，自动调整布局选项
watch(() => printConfig.invoice_type, (newType) => {
  const layouts = printStore.getLayoutsForType(newType)
  if (layouts.length > 0 && !layouts.some(l => l.value === printConfig.layout)) {
    // 如果当前布局不支持新类型，选择第一个可用布局
    printConfig.layout = layouts[0].value
  }
})

// 方法
const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'printed': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败',
    'printed': '已打印'
  }
  return statusMap[status] || '未知'
}

const isSelected = (invoiceId: string) => {
  return selectedInvoices.value.includes(invoiceId)
}

const toggleSelection = (invoiceId: string) => {
  const index = selectedInvoices.value.indexOf(invoiceId)
  if (index > -1) {
    selectedInvoices.value.splice(index, 1)
  } else {
    selectedInvoices.value.push(invoiceId)
  }
}

const selectAll = () => {
  selectedInvoices.value = availableInvoices.value.map(invoice => invoice.id)
}

const clearSelection = () => {
  selectedInvoices.value = []
}

const refreshSelectedInvoices = async () => {
  await fetchInvoices()
}

const handleSearch = () => {
  pagination.page = 1
  fetchInvoices()
}

const handleSizeChange = (size: number) => {
  pagination.size = size
  pagination.page = 1
  fetchInvoices()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchInvoices()
}

const fetchInvoices = async () => {
  try {
    await invoiceStore.fetchInvoices({
      page: pagination.page,
      size: pagination.size,
      filters
    })
    pagination.total = invoiceStore.pagination.total
  } catch (error) {
    ElMessage.error('获取发票列表失败')
  }
}

const handlePreview = async () => {
  if (selectedInvoices.value.length === 0) {
    ElMessage.warning('请选择要打印的发票')
    return
  }
  
  try {
    const success = await printStore.previewPrint({
      invoice_ids: selectedInvoices.value,
      layout: printConfig.layout,
      invoice_type: printConfig.invoice_type,
      sort_by_type: printConfig.sort_by_type
    })
    
    if (success) {
      ElMessage.success('预览生成成功')
    } else {
      ElMessage.error('预览生成失败')
    }
  } catch (error) {
    ElMessage.error('预览失败')
  }
}

const handlePrint = async () => {
  if (!printFormRef.value) return
  
  try {
    await printFormRef.value.validate()
    
    if (selectedInvoices.value.length === 0) {
      ElMessage.warning('请选择要打印的发票')
      return
    }
    
    const blob = await printStore.generatePrint({
      invoice_ids: selectedInvoices.value,
      layout: printConfig.layout,
      invoice_type: printConfig.invoice_type,
      show_dividers: printConfig.show_dividers,
      sort_by_type: printConfig.sort_by_type,
      update_status: printConfig.update_status
    })
    
    if (blob) {
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')
      const filename = `发票批量打印_${timestamp}.pdf`
      printStore.downloadPDF(blob, filename)
      
      ElMessage.success('PDF生成成功')
      
      // 如果更新了状态，刷新列表
      if (printConfig.update_status) {
        fetchInvoices()
      }
    } else {
      ElMessage.error('PDF生成失败')
    }
  } catch (error) {
    ElMessage.error('打印失败')
  }
}

const handleBrowserPrint = async () => {
  if (!printFormRef.value) return
  
  try {
    await printFormRef.value.validate()
    
    if (selectedInvoices.value.length === 0) {
      ElMessage.warning('请选择要打印的发票')
      return
    }
    
    const pdfUrl = await printStore.generatePrintForBrowser({
      invoice_ids: selectedInvoices.value,
      layout: printConfig.layout,
      invoice_type: printConfig.invoice_type,
      show_dividers: printConfig.show_dividers,
      sort_by_type: printConfig.sort_by_type,
      update_status: printConfig.update_status
    })
    
    if (pdfUrl) {
      // 调用浏览器打印API
      printStore.printPDFInBrowser(pdfUrl)
      
      ElMessage.success('PDF已在新窗口中打开，请确认打印')
      
      // 如果更新了状态，刷新列表
      if (printConfig.update_status) {
        fetchInvoices()
      }
      
      // 清理URL资源（延迟清理，确保打印完成）
      setTimeout(() => {
        window.URL.revokeObjectURL(pdfUrl)
      }, 60000)
    } else {
      ElMessage.error('生成预览PDF失败')
    }
  } catch (error) {
    ElMessage.error('浏览器打印失败')
  }
}

const handleBatchStatusUpdate = async () => {
  if (selectedInvoices.value.length === 0) {
    ElMessage.warning('请选择要更新的发票')
    return
  }
  
  if (!batchStatus.value) {
    ElMessage.warning('请选择要更新的状态')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要将选中的 ${selectedInvoices.value.length} 张发票状态更新为"${batchStatus.value}"吗？`,
      '批量更新确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const success = await printStore.updateStatus({
      invoice_ids: selectedInvoices.value,
      status: batchStatus.value
    })
    
    if (success) {
      ElMessage.success('批量更新成功')
      fetchInvoices()
    } else {
      ElMessage.error('批量更新失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量更新失败')
    }
  }
}

onMounted(async () => {
  // 初始化数据
  await Promise.all([
    printStore.fetchLayouts(),
    printStore.fetchStatusOptions(),
    fetchInvoices()
  ])
})
</script>

<style scoped>
.page-container { overflow: hidden; }
.batch-print {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.sticky-card {
  position: sticky;
  top: 16px;
}



.invoice-selection { display: flex; flex-direction: column; height: calc(100vh - 220px); }
.invoice-list {
  flex: 1;
  overflow-y: auto;
  -ms-overflow-style: none; /* IE/Edge */
  scrollbar-width: none; /* Firefox */
}
.invoice-list::-webkit-scrollbar { width: 0; height: 0; }
.invoice-items { display: flex; flex-direction: column; }

.invoice-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.invoice-item:hover {
  background-color: var(--el-bg-color-page);
  border-color: var(--el-color-primary);
}

.invoice-item.selected {
  background-color: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.invoice-checkbox {
  margin-right: 12px;
}

.invoice-info {
  flex: 1;
}

.invoice-title {
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-bottom: 4px;
}

.invoice-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.filename {
  font-size: 12px;
  color: var(--el-text-color-regular);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.amount {
  font-weight: 600;
  color: var(--el-color-danger);
  font-size: 14px;
}

.invoice-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.service-type {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.pagination-wrapper {
  margin-top: 20px;
  text-align: center;
}

.selection-summary {
  text-align: center;
}

.option-desc {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.preview-info {
  background: var(--el-bg-color-page);
  padding: 16px;
  border-radius: 6px;
}

.summary-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.type-tag {
  margin-right: 8px;
  margin-bottom: 4px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.batch-operations {
  text-align: center;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
}
</style>