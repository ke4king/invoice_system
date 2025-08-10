export interface PrintLayout {
  value: string
  label: string
  description: string
  supported_types: string[]
}

export interface InvoiceType {
  value: string
  label: string
  description: string
}

export interface BatchPrintRequest {
  invoice_ids: string[]
  layout: string
  invoice_type: string
  show_dividers: boolean
  sort_by_type: boolean
  update_status: boolean
}

export interface PrintPreviewRequest {
  invoice_ids: string[]
  layout: string
  invoice_type: string
  sort_by_type: boolean
}

export interface PrintPreviewResponse {
  total_invoices: number
  total_pages: number
  layout_info: string
  invoices_by_type: Record<string, number>
}

export interface BatchStatusUpdateRequest {
  invoice_ids: string[]
  status: string
}

export interface BatchStatusUpdateResponse {
  updated_count: number
  failed_count: number
  errors: string[]
}

export interface StatusOption {
  value: string
  label: string
  description: string
}