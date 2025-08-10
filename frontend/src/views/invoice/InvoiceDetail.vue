<template>
  <div class="invoice-detail">
    <div class="page-header">
      <h1 class="page-title">发票详情</h1>
      <el-button @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>
    
    <el-card v-loading="loading">
      <div v-if="invoice">
        <el-descriptions title="发票信息" :column="2" border>
          <el-descriptions-item label="文件名">
            {{ invoice.original_filename }}
          </el-descriptions-item>
          <el-descriptions-item label="发票代码">
            {{ invoice.invoice_code || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="发票号码">
            {{ invoice.invoice_num || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="开票日期">
            {{ invoice.invoice_date ? formatDate(invoice.invoice_date) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="销售方">
            {{ invoice.seller_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="购买方">
            {{ invoice.purchaser_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="总金额">
            {{ invoice.total_amount ? `¥${invoice.total_amount}` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="消费类型">
            {{ invoice.service_type ? `${invoice.service_type}` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(invoice.status)">
              {{ getStatusText(invoice.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="OCR状态">
            <el-tag :type="getOCRStatusType(invoice.ocr_status)">
              {{ getOCRStatusText(invoice.ocr_status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <div v-else class="empty-state">
        <el-empty description="发票不存在或已被删除" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useInvoiceStore } from '@/stores/invoice'
import type { Invoice } from '@/types/invoice'

const route = useRoute()
const invoiceStore = useInvoiceStore()

const loading = ref(false)
const invoice = ref<Invoice | null>(null)

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
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

const getOCRStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
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

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('zh-CN')
}

const fetchInvoiceDetail = async () => {
  const id = route.params.id as string
  if (!id) return
  
  loading.value = true
  try {
    await invoiceStore.fetchInvoice(id)
    invoice.value = invoiceStore.currentInvoice
  } catch (error) {
    console.error('获取发票详情失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchInvoiceDetail()
})
</script>

<style scoped>
.invoice-detail {
  padding: 20px;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
}
</style>