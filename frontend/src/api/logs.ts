import api from '@/utils/request'
import type { LogItem, LogFilters, LogStatistics, SystemHealth, PerformanceMetrics, DashboardStats } from '@/types/logs'

/**
 * 获取日志列表
 * @param params 查询参数
 */
export function getLogs(params: {
  page: number
  pageSize: number
  level?: string
  module?: string
  keyword?: string
  startDate?: string
  endDate?: string
}) {
  // 改为 POST 提交筛选条件
  const body: any = {
    page: params.page,
    size: params.pageSize,
    log_level: params.level,
    log_type: params.module,
    search: params.keyword,
    date_from: params.startDate,
    date_to: params.endDate
  }
  
  return api.post<{
    items: LogItem[]
    total: number
    page: number
    size: number
  }>('/logs/logs/search', body).then(response => {
    // 转换响应格式以匹配前端期望的格式
    return {
      data: response.data.items || [],
      total: response.data.total || 0
    }
  }).catch(error => {
    console.error('获取日志列表失败:', error)
    return {
      data: [],
      total: 0
    }
  })
}

/**
 * 获取日志统计信息
 * @param days 统计天数
 */
export function getLogStatistics(days: number = 7) {
  return api.get<LogStatistics>(`/logs/logs/statistics`, { 
    params: { days } 
  })
}

/**
 * 获取仪表盘统计信息（实际数据）
 * @param days 统计天数
 */
export function getDashboardStatistics(days: number = 30) {
  return api.get<DashboardStats>(`/logs/dashboard/statistics`, {
    params: { days }
  })
}

/**
 * 清空日志
 * @param days 保留天数
 */
export function clearLogs(days: number = 90) {
  return api.delete(`/logs/logs/cleanup`, {
    params: { days_to_keep: days }
  })
}

/**
 * 获取系统健康状态
 */
export function getSystemHealth() {
  return api.get<SystemHealth>(`/logs/system/health`)
}

/**
 * 获取系统性能指标
 * @param hours 分析时间范围（小时）
 */
export function getPerformanceMetrics(hours: number = 24) {
  return api.get<PerformanceMetrics>(`/logs/system/performance`, {
    params: { hours }
  })
}

/**
 * 导出日志为CSV格式
 * @param params 筛选参数
 */
export async function exportLogsCSV(params: {
  log_level?: string
  log_type?: string
  date_from?: string
  date_to?: string
  search?: string
  limit?: number
}) {
  const response = await api.get(`/logs/logs/export/csv`, {
    params,
    responseType: 'blob'
  } as any)
  return response.data as Blob
}

/**
 * 导出日志为Excel格式
 * @param params 筛选参数
 */
export async function exportLogsExcel(params: {
  log_level?: string
  log_type?: string
  date_from?: string
  date_to?: string
  search?: string
  limit?: number
}) {
  const response = await api.get(`/logs/logs/export/excel`, {
    params,
    responseType: 'blob'
  } as any)
  return response.data as Blob
}
