<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">仪表板</h1>
      <div class="page-header-actions">
        <el-button @click="fetchDashboardData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div v-for="card in statsCards" :key="card.title" class="stat-card">
        <!-- <div class="card-icon" :style="{ backgroundColor: card.color }">
          <el-icon :size="24">
            <component :is="card.icon" />
          </el-icon>
        </div> -->
        <div class="stat-number">{{ card.value }}</div>
        <div class="stat-label">{{ card.title }}</div>
      </div>
    </div>
    
    <el-row :gutter="20">
      <!-- 最近上传的发票 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-header-title">最近上传的发票</span>
              <el-button type="primary" link @click="$router.push('/invoices')">
                查看全部
              </el-button>
            </div>
          </template>
          
          <div v-loading="loading">
            <div v-if="recentInvoices.length === 0" class="empty-state">
              <el-empty description="暂无发票数据" />
            </div>
            <div v-else>
              <div
                v-for="invoice in recentInvoices"
                :key="invoice.id"
                class="invoice-item"
                @click="viewInvoice(invoice.id)"
              >
                <div class="invoice-info">
                  <h4>{{ invoice.seller_name || '未知销售方' }}</h4>
                  <p>{{ invoice.original_filename }}</p>
                </div>
                <div class="invoice-status">
                  <el-tag :type="getStatusType(invoice.ocr_status)">
                    {{ getStatusText(invoice.ocr_status) }}
                  </el-tag>
                  <span class="invoice-amount">
                    ¥{{ invoice.total_amount || 0 }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 快速操作 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-header-title">快速操作</span>
          </template>
          
          <div class="quick-actions">
            <el-button
              type="primary"
              size="large"
              @click="$router.push('/invoices/upload')"
            >
              <el-icon><UploadFilled /></el-icon>
              上传发票
            </el-button>
            
            <el-button
              size="large"
              @click="$router.push('/print')"
            >
              <el-icon><Printer /></el-icon>
              批量打印
            </el-button>
            
            <el-button
              size="large"
              @click="$router.push('/settings')"
            >
              <el-icon><Setting /></el-icon>
              邮箱配置
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Document, 
  UploadFilled, 
  Printer, 
  Setting,
  CircleCheck,
  Warning,
  Loading,
  Refresh
} from '@element-plus/icons-vue'
import { useInvoiceStore } from '@/stores/invoice'
import type { Invoice } from '@/types/invoice'

const router = useRouter()
const invoiceStore = useInvoiceStore()

const loading = ref(false)
const recentInvoices = ref<Invoice[]>([])

// 统计卡片数据
const statsCards = ref([
  {
    title: '总发票数',
    value: 0,
    // icon: Document,
    color: 'var(--el-color-primary)'
  },
  {
    title: '待处理',
    value: 0,
    // icon: Loading,
    color: 'var(--el-color-warning)'
  },
  {
    title: '已完成',
    value: 0,
    // icon: CircleCheck,
    color: 'var(--el-color-success)'
  },
  {
    title: '处理失败',
    value: 0,
    // icon: Warning,
    color: 'var(--el-color-danger)'
  }
])

const getStatusType = (status: string) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'danger'
    case 'processing':
      return 'warning'
    default:
      return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'success':
      return '识别成功'
    case 'failed':
      return '识别失败'
    case 'processing':
      return '识别中'
    default:
      return '待处理'
  }
}

const viewInvoice = (id: string) => {
  router.push(`/invoices/${id}`)
}

const fetchDashboardData = async () => {
  loading.value = true
  try {
    // 获取最近的发票数据
    await invoiceStore.fetchInvoices({ page: 1, size: 5 })
    recentInvoices.value = invoiceStore.invoices
    
    // 更新统计数据
    const total = invoiceStore.pagination.total
    statsCards.value[0].value = total
    
    // 简单统计各状态数量
    const pending = recentInvoices.value.filter(inv => inv.ocr_status === 'pending').length
    const processing = recentInvoices.value.filter(inv => inv.ocr_status === 'processing').length
    const success = recentInvoices.value.filter(inv => inv.ocr_status === 'success').length
    const failed = recentInvoices.value.filter(inv => inv.ocr_status === 'failed').length
    
    statsCards.value[1].value = pending + processing
    statsCards.value[2].value = success
    statsCards.value[3].value = failed
    
  } catch (error) {
    console.error('获取仪表板数据失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()
})
</script>

<style scoped>
.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 12px;
}

.invoice-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: background-color 0.2s;
}

.invoice-item:hover {
  background-color: var(--el-fill-color-light);
  margin: 0 -12px;
  padding: 12px;
  border-radius: 4px;
}

.invoice-item:last-child {
  border-bottom: none;
}

.invoice-info h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.invoice-info p {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.invoice-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.invoice-amount {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-color-danger);
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.quick-actions .el-button {
  justify-content: flex-start;
  width: 100%;
}
</style>
