import { defineStore } from 'pinia'
import type { Invoice, InvoiceFilter, InvoiceListResponse, InvoiceUpdate } from '@/types/invoice'
import { 
  getInvoices, 
  getInvoice, 
  updateInvoice, 
  deleteInvoice, 
  uploadInvoice, 
  retryOCR 
} from '@/api/invoice'

interface InvoiceState {
  invoices: Invoice[]
  currentInvoice: Invoice | null
  loading: boolean
  filters: InvoiceFilter
  pagination: {
    page: number
    size: number
    total: number
    pages: number
  }
  selectedInvoices: string[]
}

export const useInvoiceStore = defineStore('invoice', {
  state: (): InvoiceState => ({
    invoices: [],
    currentInvoice: null,
    loading: false,
    filters: {},
    pagination: {
      page: 1,
      size: 20,
      total: 0,
      pages: 0
    },
    selectedInvoices: []
  }),
  
  getters: {
    filteredInvoices: (state) => state.invoices,
    hasSelected: (state) => state.selectedInvoices.length > 0,
    selectedCount: (state) => state.selectedInvoices.length,
  },
  
  actions: {
    async fetchInvoices(params?: {
      page?: number
      size?: number
      filters?: InvoiceFilter
    }): Promise<void> {
      this.loading = true
      try {
        const { page = 1, size = 20, filters = {} } = params || {}
        
        const response = await getInvoices({
          page,
          size,
          ...filters,
          include_duplicates: (filters as any).include_duplicates ?? false,
        })
        
        const data: InvoiceListResponse = response.data
        
        this.invoices = data.items
        this.pagination = {
          page: data.page,
          size: data.size,
          total: data.total,
          pages: data.pages
        }
        this.filters = filters
      } catch (error) {
        console.error('获取发票列表失败:', error)
      } finally {
        this.loading = false
      }
    },
    
    async fetchInvoice(id: string): Promise<void> {
      try {
        const response = await getInvoice(id)
        this.currentInvoice = response.data
      } catch (error) {
        console.error('获取发票详情失败:', error)
      }
    },
    
    async uploadInvoice(file: File): Promise<boolean> {
      try {
        const response = await uploadInvoice(file)
        await this.fetchInvoices()
        return true
      } catch (error) {
        console.error('上传发票失败:', error)
        return false
      }
    },
    
    async updateInvoice(id: string, data: InvoiceUpdate): Promise<boolean> {
      try {
        const response = await updateInvoice(id, data)
        
        // 更新本地状态
        const index = this.invoices.findIndex(invoice => invoice.id === id)
        if (index !== -1) {
          this.invoices[index] = response.data
        }
        
        if (this.currentInvoice?.id === id) {
          this.currentInvoice = response.data
        }
        
        return true
      } catch (error) {
        console.error('更新发票失败:', error)
        return false
      }
    },
    
    async deleteInvoice(id: string): Promise<boolean> {
      try {
        await deleteInvoice(id)
        
        // 从本地状态中移除
        this.invoices = this.invoices.filter(invoice => invoice.id !== id)
        this.selectedInvoices = this.selectedInvoices.filter(selectedId => selectedId !== id)
        
        if (this.currentInvoice?.id === id) {
          this.currentInvoice = null
        }
        
        return true
      } catch (error) {
        console.error('删除发票失败:', error)
        return false
      }
    },
    
    async retryOCR(id: string, force: boolean = false): Promise<boolean> {
      try {
        await retryOCR(id, { force })
        
        // 更新发票状态
        const invoice = this.invoices.find(inv => inv.id === id)
        if (invoice) {
          invoice.ocr_status = 'pending'
          invoice.ocr_error_message = undefined
        }
        
        return true
      } catch (error) {
        console.error('重试OCR失败:', error)
        return false
      }
    },
    
    setFilters(filters: InvoiceFilter): void {
      this.filters = { ...filters }
    },
    
    toggleSelection(id: string): void {
      const index = this.selectedInvoices.indexOf(id)
      if (index > -1) {
        this.selectedInvoices.splice(index, 1)
      } else {
        this.selectedInvoices.push(id)
      }
    },
    
    selectAll(): void {
      this.selectedInvoices = this.invoices.map(invoice => invoice.id)
    },
    
    clearSelection(): void {
      this.selectedInvoices = []
    },
    
    isSelected(id: string): boolean {
      return this.selectedInvoices.includes(id)
    }
  }
})