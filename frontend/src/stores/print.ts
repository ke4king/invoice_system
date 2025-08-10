import { defineStore } from 'pinia'
import type { 
  PrintLayout, 
  InvoiceType,
  StatusOption, 
  BatchPrintRequest,
  PrintPreviewRequest,
  PrintPreviewResponse,
  BatchStatusUpdateRequest
} from '@/types/print'
import { 
  getPrintLayouts, 
  getStatusOptions,
  previewBatchPrint,
  generateBatchPrint,
  batchUpdateStatus,
  generatePrintForBrowser
} from '@/api/print'

interface PrintState {
  layouts: PrintLayout[]
  invoiceTypes: InvoiceType[]
  statusOptions: StatusOption[]
  loading: boolean
  previewData: PrintPreviewResponse | null
}

export const usePrintStore = defineStore('print', {
  state: (): PrintState => ({
    layouts: [],
    invoiceTypes: [],
    statusOptions: [],
    loading: false,
    previewData: null
  }),
  
  getters: {
    hasPreviewData: (state) => state.previewData !== null,
    previewSummary: (state) => {
      if (!state.previewData) return null
      return {
        totalInvoices: state.previewData.total_invoices,
        totalPages: state.previewData.total_pages,
        layoutInfo: state.previewData.layout_info
      }
    },
    // 根据发票类型过滤可用布局
    getLayoutsForType: (state) => (invoiceType: string) => {
      return state.layouts.filter(layout => 
        layout.supported_types.includes(invoiceType)
      )
    }
  },
  
  actions: {
    async fetchLayouts(): Promise<void> {
      try {
        const response = await getPrintLayouts()
        this.layouts = response.data.layouts
        this.invoiceTypes = response.data.invoice_types
      } catch (error) {
        console.error('获取打印布局失败:', error)
      }
    },
    
    async fetchStatusOptions(): Promise<void> {
      try {
        const response = await getStatusOptions()
        this.statusOptions = response.data.statuses
      } catch (error) {
        console.error('获取状态选项失败:', error)
      }
    },
    
    async previewPrint(previewRequest: PrintPreviewRequest): Promise<boolean> {
      this.loading = true
      try {
        const response = await previewBatchPrint(previewRequest)
        this.previewData = response.data
        return true
      } catch (error) {
        console.error('预览打印失败:', error)
        return false
      } finally {
        this.loading = false
      }
    },
    
    async generatePrint(printRequest: BatchPrintRequest): Promise<Blob | null> {
      this.loading = true
      try {
        const response = await generateBatchPrint(printRequest)
        return response.data as Blob
      } catch (error) {
        console.error('生成打印PDF失败:', error)
        return null
      } finally {
        this.loading = false
      }
    },
    
    async updateStatus(updateRequest: BatchStatusUpdateRequest): Promise<boolean> {
      try {
        const response = await batchUpdateStatus(updateRequest)
        return response.data.failed_count === 0
      } catch (error) {
        console.error('批量更新状态失败:', error)
        return false
      }
    },
    
    clearPreview(): void {
      this.previewData = null
    },
    
    // 下载PDF文件
    downloadPDF(blob: Blob, filename: string): void {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
    
    // 生成PDF并在浏览器中预览/打印
    async generatePrintForBrowser(printRequest: BatchPrintRequest): Promise<string | null> {
      this.loading = true
      try {
        const response = await generatePrintForBrowser(printRequest)
        const blob = response.data as Blob
        
        // 创建blob URL用于浏览器预览
        const url = window.URL.createObjectURL(blob)
        return url
      } catch (error) {
        console.error('生成浏览器预览PDF失败:', error)
        return null
      } finally {
        this.loading = false
      }
    },
    
    // 调用浏览器打印API
    printPDFInBrowser(pdfUrl: string): void {
      // 在新窗口中打开PDF
      const printWindow = window.open(pdfUrl, '_blank', 'width=800,height=600')
      
      if (printWindow) {
        printWindow.onload = () => {
          // PDF加载完成后自动调用打印
          setTimeout(() => {
            printWindow.print()
          }, 1000)
        }
      } else {
        console.error('无法打开新窗口进行打印')
      }
    }
  }
})