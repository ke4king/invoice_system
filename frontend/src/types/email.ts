export interface EmailConfig {
  id: number
  user_id: number
  email_address: string
  imap_server: string
  imap_port: number
  username: string
  scan_days: number
  is_active: boolean
  last_scan_time?: string
  created_at: string
  updated_at: string
}

export interface EmailConfigCreate {
  email_address: string
  imap_server: string
  imap_port: number
  username: string
  password: string
  scan_days?: number
}

export interface EmailConfigUpdate {
  email_address?: string
  imap_server?: string
  imap_port?: number
  username?: string
  password?: string
  scan_days?: number
  is_active?: boolean
}

export interface EmailConnectionTest {
  email_address: string
  imap_server: string
  imap_port: number
  username: string
  password: string
}

export interface ManualScanRequest {
  config_id?: number
  days?: number
  force?: boolean
}

export interface ScanTaskStatus {
  state: string
  current?: number
  total?: number
  status?: string
  result?: any
  error?: string
}

export interface EmailScanResult {
  config_id: number
  email_address: string
  processed_count: number
  success_count: number
  error_count: number
  errors: string[]
  processed_files: Array<{
    filename: string
    type: string
    status: string
    invoice_id?: string
  }>
}

// 邮件列表相关类型
export interface Email {
  id: string
  user_id: number
  message_id: string
  subject?: string
  sender?: string
  recipient?: string
  date_sent?: string
  date_received?: string
  body_text?: string
  body_html?: string
  has_attachments: boolean
  attachment_count: number
  attachment_info?: Array<{
    filename: string
    content_type: string
    size: number
    is_pdf: boolean
  }>
  invoice_scan_status: string
  invoice_count: number
  scan_result?: Record<string, any>
  processing_status: string
  error_message?: string
  created_at: string
  updated_at: string
  scanned_at?: string
}

export interface EmailFilter {
  invoice_scan_status?: string
  processing_status?: string
  sender?: string
  subject?: string
  has_attachments?: boolean
  has_invoice?: boolean
  date_from?: string
  date_to?: string
}

export interface EmailListResponse {
  emails: Email[]
  total: number
  page: number
  size: number
  pages: number
}

export interface EmailStatistics {
  period_days: number
  total_emails: number
  emails_with_attachments: number
  emails_with_invoices: number
  emails_without_invoices: number
  total_invoices_found: number
  scan_status_breakdown: Record<string, number>
  processing_status_breakdown: Record<string, number>
  attachment_rate: number
  invoice_detection_rate: number
}

export interface EmailBatchOperation {
  email_ids: string[]
  operation: 'rescan' | 'delete'
}

export interface EmailBatchOperationResponse {
  success: boolean
  total: number
  processed: number
  failed: number
  failed_details?: Array<{
    email_id: string
    reason: string
  }>
  message: string
}

export interface EmailUpdate {
  subject?: string
  invoice_scan_status?: 'pending' | 'no_invoice' | 'has_invoice'
  processing_status?: string
  invoice_count?: number
  scan_result?: Record<string, any>
  error_message?: string
}