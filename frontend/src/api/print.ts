import type { 
  BatchPrintRequest,
  PrintPreviewRequest, 
  PrintPreviewResponse,
  BatchStatusUpdateRequest,
  BatchStatusUpdateResponse,
  PrintLayout,
  StatusOption
} from '@/types/print'
import api from '@/utils/request'

// 预览批量打印
export const previewBatchPrint = (data: PrintPreviewRequest) => {
  return api.post<PrintPreviewResponse>('/print/preview', data)
}

// 生成批量打印PDF
export const generateBatchPrint = (data: BatchPrintRequest) => {
  return api.post('/print/generate', data, {
    responseType: 'blob',
    headers: {
      'Accept': 'application/pdf'
    }
  })
}

// 批量更新发票状态
export const batchUpdateStatus = (data: BatchStatusUpdateRequest) => {
  return api.post<BatchStatusUpdateResponse>('/print/update-status', data)
}

// 获取打印布局选项
export const getPrintLayouts = () => {
  return api.get<{ layouts: PrintLayout[] }>('/print/layouts')
}

// 获取状态选项
export const getStatusOptions = () => {
  return api.get<{ statuses: StatusOption[] }>('/print/status-options')
}

// 生成用于浏览器预览和打印的PDF
export const generatePrintForBrowser = (data: BatchPrintRequest) => {
  return api.post('/print/generate-for-browser', data, {
    responseType: 'blob',
    headers: {
      'Accept': 'application/pdf'
    }
  })
}