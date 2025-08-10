import type { 
  EmailConfig, 
  EmailConfigCreate, 
  EmailConfigUpdate,
  EmailConnectionTest,
  ManualScanRequest,
  ScanTaskStatus
} from '@/types/email'
import api from '@/utils/request'

// 创建邮箱配置
export const createEmailConfig = (data: EmailConfigCreate) => {
  return api.post<EmailConfig>('/email', data)
}

// 获取邮箱配置列表
export const getEmailConfigs = () => {
  return api.get<EmailConfig[]>('/email')
}

// 更新邮箱配置
export const updateEmailConfig = (id: number, data: EmailConfigUpdate) => {
  return api.put<EmailConfig>(`/email/${id}`, data)
}

// 删除邮箱配置
export const deleteEmailConfig = (id: number) => {
  return api.delete(`/email/${id}`)
}

// 测试邮箱连接
export const testEmailConnection = (data: EmailConnectionTest) => {
  return api.post('/email/test-connection', data)
}

// 手动扫描邮箱
export const manualScanEmails = (data: ManualScanRequest = {}) => {
  return api.post('/email/scan', data)
}

// 获取扫描任务状态
export const getScanStatus = (taskId: string) => {
  return api.get<ScanTaskStatus>(`/email/scan-status/${taskId}`)
}