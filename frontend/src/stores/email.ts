import { defineStore } from 'pinia'
import type { EmailConfig, EmailConfigCreate, EmailConfigUpdate, ManualScanRequest } from '@/types/email'
import { 
  getEmailConfigs, 
  createEmailConfig, 
  updateEmailConfig, 
  deleteEmailConfig,
  testEmailConnection,
  manualScanEmails,
  getScanStatus
} from '@/api/email'

interface EmailState {
  configs: EmailConfig[]
  loading: boolean
  scanningTaskId: string | null
  scanningStatus: string
}

export const useEmailStore = defineStore('email', {
  state: (): EmailState => ({
    configs: [],
    loading: false,
    scanningTaskId: null,
    scanningStatus: 'idle' // idle, scanning, completed, error
  }),
  
  getters: {
    activeConfigs: (state) => state.configs.filter(config => config.is_active),
    hasActiveConfigs: (state) => state.configs.some(config => config.is_active),
    isScanning: (state) => state.scanningStatus === 'scanning',
  },
  
  actions: {
    async fetchConfigs(): Promise<void> {
      this.loading = true
      try {
        const response = await getEmailConfigs()
        this.configs = response.data
      } catch (error) {
        console.error('获取邮箱配置失败:', error)
      } finally {
        this.loading = false
      }
    },
    
    async createConfig(configData: EmailConfigCreate): Promise<boolean> {
      try {
        const response = await createEmailConfig(configData)
        
        // 更新本地状态
        const existingIndex = this.configs.findIndex(
          config => config.email_address === response.data.email_address
        )
        
        if (existingIndex > -1) {
          this.configs[existingIndex] = response.data
        } else {
          this.configs.push(response.data)
        }
        
        return true
      } catch (error) {
        console.error('创建邮箱配置失败:', error)
        return false
      }
    },
    
    async updateConfig(id: number, configData: EmailConfigUpdate): Promise<boolean> {
      try {
        const response = await updateEmailConfig(id, configData)
        
        // 更新本地状态
        const index = this.configs.findIndex(config => config.id === id)
        if (index > -1) {
          this.configs[index] = response.data
        }
        
        return true
      } catch (error) {
        console.error('更新邮箱配置失败:', error)
        return false
      }
    },
    
    async deleteConfig(id: number): Promise<boolean> {
      try {
        await deleteEmailConfig(id)
        
        // 从本地状态中移除
        this.configs = this.configs.filter(config => config.id !== id)
        
        return true
      } catch (error) {
        console.error('删除邮箱配置失败:', error)
        return false
      }
    },
    
    async testConnection(connectionData: any): Promise<boolean> {
      try {
        await testEmailConnection(connectionData)
        return true
      } catch (error) {
        console.error('测试邮箱连接失败:', error)
        return false
      }
    },
    
    async startManualScan(scanRequest: ManualScanRequest = {}): Promise<boolean> {
      try {
        const response = await manualScanEmails(scanRequest)
        
        this.scanningTaskId = response.data.task_id
        this.scanningStatus = 'scanning'
        
        // 开始轮询任务状态
        this.pollScanStatus()
        
        return true
      } catch (error) {
        console.error('启动邮箱扫描失败:', error)
        this.scanningStatus = 'error'
        return false
      }
    },
    
    async pollScanStatus(): Promise<void> {
      if (!this.scanningTaskId) return
      
      try {
        const response = await getScanStatus(this.scanningTaskId)
        const status = response.data
        
        if (status.state === 'SUCCESS') {
          this.scanningStatus = 'completed'
          this.scanningTaskId = null
          // 刷新配置列表以更新最后扫描时间
          this.fetchConfigs()
        } else if (status.state === 'FAILURE') {
          this.scanningStatus = 'error'
          this.scanningTaskId = null
        } else {
          // 继续轮询
          setTimeout(() => {
            this.pollScanStatus()
          }, 2000)
        }
      } catch (error) {
        console.error('获取扫描状态失败:', error)
        this.scanningStatus = 'error'
        this.scanningTaskId = null
      }
    },
    
    resetScanStatus(): void {
      this.scanningTaskId = null
      this.scanningStatus = 'idle'
    }
  }
})