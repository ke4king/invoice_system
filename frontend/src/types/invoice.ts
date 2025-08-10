export interface Invoice {
  id: string
  user_id: number
  original_filename: string
  file_path: string
  file_size?: number
  source?: string
  
  // 发票基本信息
  invoice_code?: string
  invoice_num?: string
  invoice_date?: string
  invoice_type?: string
  
  // 购买方信息
  purchaser_name?: string
  purchaser_register_num?: string
  purchaser_address?: string
  purchaser_bank?: string
  
  // 销售方信息
  seller_name?: string
  seller_register_num?: string
  seller_address?: string
  seller_bank?: string
  
  // 金额信息
  total_amount?: number
  total_tax?: number
  amount_in_words?: string
  amount_in_figures?: number
  
  // 其他信息
  service_type?: string
  commodity_details?: any[]
  ocr_raw_data?: any
  
  // 状态
  status: string
  ocr_status: string
  ocr_error_message?: string
  
  // 时间戳
  created_at: string
  updated_at: string
  processed_at?: string
}

export interface InvoiceFilter {
  status?: string
  ocr_status?: string
  seller_name?: string
  purchaser_name?: string
  service_type?: string
  // 多选（Excel 风格）
  seller_names?: string[]
  purchaser_names?: string[]
  service_types?: string[]
  date_from?: string
  date_to?: string
  amount_min?: number
  amount_max?: number
  include_duplicates?: boolean
}

export interface InvoiceListResponse {
  items: Invoice[]
  total: number
  page: number
  size: number
  pages: number
}

export interface InvoiceUploadResponse {
  id: string
  message: string
  status: string
}

export interface InvoiceUpdate {
  invoice_code?: string
  invoice_num?: string
  invoice_date?: string
  invoice_type?: string
  purchaser_name?: string
  purchaser_register_num?: string
  purchaser_address?: string
  purchaser_bank?: string
  seller_name?: string
  seller_register_num?: string
  seller_address?: string
  seller_bank?: string
  total_amount?: number
  total_tax?: number
  amount_in_words?: string
  amount_in_figures?: number
  service_type?: string
  commodity_details?: any[]
  status?: string
}