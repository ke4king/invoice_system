// 日志管理相关的类型定义
export interface LogItem {
  id: number
  log_type: string
  log_level: string
  message: string
  details?: Record<string, any> | null
  resource_type?: string | null
  resource_id?: string | null
  ip_address?: string | null
  user_agent?: string | null
  created_at: string
}

export interface LogFilters {
  log_type?: string
  log_level?: string
  dateRange?: string[]
  search?: string
}

export interface LogStatistics {
  total_logs: number
  error_logs: number
  success_rate: number
  by_type: Array<{ type: string; count: number }>
  by_level: Array<{ level: string; count: number }>
  by_date: Array<{ date: string; count: number }>
  period_days: number
}

export interface DashboardStats {
  period_days: number
  invoice_stats: any
  ocr_stats: any
  email_stats: any
  activity_stats: any
  error_stats: any
  last_updated: string
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  database: {
    healthy: boolean
    error?: string
  }
  recent_errors: number
  check_time: string
}

export interface PerformanceMetrics {
  period_hours: number
  performance: {
    avg_response_time: number
    max_response_time: number
    total_requests: number
    requests_per_hour: number
  }
  check_time: string
}