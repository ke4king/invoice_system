<template>
  <el-dialog
    v-model="visibleLocal"
    :title="editMode ? '编辑发票' : '发票详情'"
    width="90%"
    destroy-on-close
  >
    <template #header>
      <div class="dialog-header">
        <span>{{ editMode ? '编辑发票' : '发票详情' }}</span>
        <div class="header-actions">
          <el-button v-if="!editMode" size="small" @click="editMode = true">编辑</el-button>
          <el-button v-else size="small" type="primary" :loading="saving" @click="saveEdit">保存</el-button>
          <el-button v-if="editMode" size="small" @click="cancelEdit">取消</el-button>
        </div>
      </div>
    </template>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="预览" name="preview">
        <div class="preview" v-loading="previewLoading">
          <div class="toolbar">
            <el-button size="small" @click="loadPdf"><el-icon><Refresh /></el-icon> 刷新预览</el-button>
          </div>
          <div class="preview-container">
            <iframe v-if="pdfUrl" :src="pdfUrl" frameborder="0"></iframe>
            <el-empty v-else description="暂无预览" />
          </div>
        </div>
      </el-tab-pane>
      <el-tab-pane label="发票信息" name="info">
        <div v-if="editMode">
          <el-form :model="editModel" ref="formRef" label-width="100px">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="发票代码" prop="invoice_code">
                  <el-input v-model="editModel.invoice_code" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="发票号码" prop="invoice_num">
                  <el-input v-model="editModel.invoice_num" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="销售方" prop="seller_name">
                  <el-input v-model="editModel.seller_name" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="购买方" prop="purchaser_name">
                  <el-input v-model="editModel.purchaser_name" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="金额" prop="total_amount">
                  <el-input v-model.number="editModel.total_amount" type="number" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="消费类型" prop="service_type">
                  <el-input v-model="editModel.service_type" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
        <div v-else>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="文件名">{{ current?.original_filename }}</el-descriptions-item>
            <el-descriptions-item label="发票代码">{{ current?.invoice_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="发票号码">{{ current?.invoice_num || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开票日期">{{ current?.invoice_date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="销售方">{{ current?.seller_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="购买方">{{ current?.purchaser_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="金额">{{ current?.total_amount ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="消费类型">{{ current?.service_type || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>
      <el-tab-pane label="OCR原始数据" name="ocr">
        <div class="json-viewer">
          <el-input v-model="jsonFilter" size="small" placeholder="过滤关键字" clearable class="mb-8" />
          <pre class="json-block">{{ prettyJson }}</pre>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useInvoiceStore } from '@/stores/invoice'
import { downloadInvoice } from '@/api/invoice'
import type { Invoice, InvoiceUpdate } from '@/types/invoice'

const props = defineProps<{
  modelValue: boolean
  invoiceId?: string | null
  invoice?: Invoice | null
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved', v: Invoice): void
}>()

const visibleLocal = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v)
})

const store = useInvoiceStore()

const current = ref<Invoice | null>(null)
const editMode = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const editModel = reactive<InvoiceUpdate>({})
const activeTab = ref<'preview' | 'info' | 'ocr'>('preview')

// 预览
const previewLoading = ref(false)
const pdfUrl = ref<string | null>(null)
const jsonFilter = ref('')

const prettyJson = computed(() => {
  const data = current.value?.ocr_raw_data || {}
  const text = JSON.stringify(data, null, 2)
  if (!jsonFilter.value) return text
  const k = jsonFilter.value.toLowerCase()
  return text.split('\n').map(l => l.toLowerCase().includes(k) ? `> ${l}` : `  ${l}`).join('\n')
})

const revokeUrl = () => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = null
  }
}

const loadPdf = async () => {
  if (!current.value?.id) return
  previewLoading.value = true
  try {
    const resp = await downloadInvoice(current.value.id)
    const blob = new Blob([resp.data], { type: 'application/pdf' })
    revokeUrl()
    pdfUrl.value = URL.createObjectURL(blob)
  } finally {
    previewLoading.value = false
  }
}

const ensureData = async () => {
  if (props.invoice) {
    current.value = props.invoice
  } else if (props.invoiceId) {
    await store.fetchInvoice(props.invoiceId)
    current.value = store.currentInvoice
  }
  Object.assign(editModel, current.value || {})
  if (current.value?.id) loadPdf()
}

const cancelEdit = () => {
  editMode.value = false
  Object.assign(editModel, current.value || {})
}

const saveEdit = async () => {
  if (!current.value) return
  try {
    saving.value = true
    const ok = await store.updateInvoice(current.value.id, editModel)
    if (ok) {
      ElMessage.success('保存成功')
      await store.fetchInvoice(current.value.id)
      current.value = store.currentInvoice
      emit('saved', current.value as Invoice)
      editMode.value = false
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (v) => {
  if (v) {
    activeTab.value = 'preview'
    await ensureData()
  } else {
    revokeUrl()
  }
})

onMounted(async () => {
  if (props.modelValue) {
    await ensureData()
  }
})

onUnmounted(() => revokeUrl())
</script>

<style scoped>
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.header-actions { display: flex; gap: 8px; }
.preview { display: flex; flex-direction: column; gap: 8px; }
.toolbar { display: flex; justify-content: flex-end; }
.preview-container {
  width: 100%;
  height: 60vh;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
  background: var(--el-bg-color);
}
.preview-container iframe { width: 100%; height: 100%; }
@media (max-width: 768px) { .preview-container { height: 50vh; } }
.json-viewer { display: flex; flex-direction: column; }
.json-block {
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 12px;
  max-height: 50vh;
  overflow: auto;
}
.mb-8 { margin-bottom: 8px; }
</style>


