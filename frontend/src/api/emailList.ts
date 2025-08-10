import type { 
  Email, 
  EmailFilter, 
  EmailListResponse, 
  EmailStatistics,
  EmailBatchOperation,
  EmailBatchOperationResponse,
  EmailUpdate
} from '@/types/email'
import api from '@/utils/request'

// 获取邮件列表
export const getEmails = (params: {
  page?: number
  size?: number
  invoice_scan_status?: string
  processing_status?: string
  sender?: string
  subject?: string
  has_attachments?: boolean
  has_invoice?: boolean
  date_from?: string
  date_to?: string
}) => {
  // 后端 POST /emails/search 不包含日期过滤参数，若需要可在后端补充；此处仅传递已支持的筛选项
  const body: any = {
    page: params.page ?? 1,
    size: params.size ?? 20,
    invoice_scan_status: params.invoice_scan_status,
    processing_status: params.processing_status,
    sender: params.sender,
    subject: params.subject,
    has_attachments: params.has_attachments,
    has_invoice: params.has_invoice
  }
  return api.post<EmailListResponse>('/emails/search', body)
}

// 获取邮件统计信息
export const getEmailStatistics = (days: number = 30) => {
  return api.get<EmailStatistics>('/emails/statistics', { 
    params: { days } 
  })
}

// 获取邮件详情
export const getEmailDetail = (emailId: string) => {
  return api.get<Email>(`/emails/${emailId}`)
}

// 更新邮件信息
export const updateEmail = (emailId: string, data: EmailUpdate) => {
  return api.put<Email>(`/emails/${emailId}`, data)
}

// 批量操作邮件
export const batchOperationEmails = (data: EmailBatchOperation) => {
  return api.post<EmailBatchOperationResponse>('/emails/batch', data)
}

// 获取状态选项
export const getEmailStatusOptions = () => {
  return api.get<{
    invoice_scan_status: Array<{ value: string; label: string }>
    processing_status: Array<{ value: string; label: string }>
  }>('/emails/status/options')
}