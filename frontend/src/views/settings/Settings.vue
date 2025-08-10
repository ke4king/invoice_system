<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">邮箱配置</h1>
      <div class="page-header-actions">
        <el-button type="primary" @click="showConfigDialog = true">
          <el-icon><Plus /></el-icon>
          添加邮箱
        </el-button>
      </div>
    </div>
    
    <!-- 邮箱配置 -->
    <div class="table-container">
      <el-card>
        <template #header>
          <span class="card-header-title">邮箱配置</span>
        </template>
          
          <div v-loading="emailStore.loading">
            <div v-if="emailStore.configs.length === 0" class="empty-state">
              <el-empty description="暂无邮箱配置">
                <el-button type="primary" @click="showConfigDialog = true">
                  添加第一个邮箱配置
                </el-button>
              </el-empty>
            </div>
            
            <div v-else>
              <div class="scan-controls mb-20">
                <el-button
                  type="primary"
                  :loading="emailStore.isScanning"
                  :disabled="!emailStore.hasActiveConfigs"
                  @click="handleManualScan"
                >
                  <el-icon><Refresh /></el-icon>
                  {{ emailStore.isScanning ? '扫描中...' : '立即扫描' }}
                </el-button>
                
                <span v-if="emailStore.scanningStatus !== 'idle'" class="scan-status">
                  <el-tag 
                    :type="getScanStatusType(emailStore.scanningStatus)"
                    effect="plain"
                  >
                    {{ getScanStatusText(emailStore.scanningStatus) }}
                  </el-tag>
                </span>
              </div>
              
              <el-table :data="emailStore.configs" stripe border>
                <el-table-column prop="email_address" label="邮箱地址" width="200" />
                <el-table-column prop="imap_server" label="IMAP服务器" width="150" />
                <el-table-column prop="imap_port" label="端口" width="80" />
                <el-table-column prop="username" label="用户名" width="150" />
                <el-table-column prop="scan_days" label="扫描天数" width="100" />
                
                <el-table-column prop="is_active" label="状态" width="100">
                  <template #default="{ row }">
                    <el-switch
                      v-model="row.is_active"
                      @change="handleToggleActive(row)"
                    />
                  </template>
                </el-table-column>
                
                <el-table-column prop="last_scan_time" label="最后扫描" width="160">
                  <template #default="{ row }">
                    {{ row.last_scan_time ? formatDate(row.last_scan_time) : '从未扫描' }}
                  </template>
                </el-table-column>
                
                <el-table-column label="操作" width="150" fixed="right">
                  <template #default="{ row }">
                    <div class="table-actions">
                      <el-button type="primary" link @click="editConfig(row)">
                        编辑
                      </el-button>
                      <el-button type="danger" link @click="deleteConfig(row)">
                        删除
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
      </el-card>
    </div>
    
    <!-- 邮箱配置对话框 -->
    <el-dialog
      v-model="showConfigDialog"
      :title="editingConfig ? '编辑邮箱配置' : '添加邮箱配置'"
      width="500px"
      :before-close="handleCloseConfigDialog"
    >
      <el-form
        ref="configFormRef"
        :model="configForm"
        :rules="configRules"
        label-width="100px"
      >
        <el-form-item label="邮箱地址" prop="email_address">
          <el-input
            v-model="configForm.email_address"
            placeholder="请输入邮箱地址"
          />
        </el-form-item>
        
        <el-form-item label="IMAP服务器" prop="imap_server">
          <el-input
            v-model="configForm.imap_server"
            placeholder="如: imap.gmail.com"
          />
        </el-form-item>
        
        <el-form-item label="IMAP端口" prop="imap_port">
          <el-input-number
            v-model="configForm.imap_port"
            :min="1"
            :max="65535"
            class="w-full"
          />
        </el-form-item>
        
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="configForm.username"
            placeholder="通常与邮箱地址相同"
          />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="configForm.password"
            type="password"
            placeholder="请输入邮箱密码或应用专用密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="扫描天数" prop="scan_days">
          <el-input-number
            v-model="configForm.scan_days"
            :min="1"
            :max="30"
            class="w-full"
          />
          <div class="form-tip">扫描最近几天的邮件</div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showConfigDialog = false">取消</el-button>
          <el-button :loading="testingConnection" @click="testConnection">
            测试连接
          </el-button>
          <el-button type="primary" :loading="configLoading" @click="handleSaveConfig">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { useEmailStore } from '@/stores/email'
import type { EmailConfig, EmailConfigCreate, EmailConfigUpdate } from '@/types/email'

const emailStore = useEmailStore()

const showConfigDialog = ref(false)
const configLoading = ref(false)
const testingConnection = ref(false)
const editingConfig = ref<EmailConfig | null>(null)
const configFormRef = ref<FormInstance>()

const configForm = reactive<EmailConfigCreate>({
  email_address: '',
  imap_server: '',
  imap_port: 993,
  username: '',
  password: '',
  scan_days: 7
})

const configRules: FormRules = {
  email_address: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  imap_server: [
    { required: true, message: '请输入IMAP服务器', trigger: 'blur' }
  ],
  imap_port: [
    { required: true, message: '请输入IMAP端口', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ],
  scan_days: [
    { required: true, message: '请输入扫描天数', trigger: 'blur' }
  ]
}

const getScanStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'idle': 'info',
    'scanning': 'warning',
    'completed': 'success',
    'error': 'danger'
  }
  return statusMap[status] || 'info'
}

const getScanStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'idle': '空闲',
    'scanning': '扫描中',
    'completed': '扫描完成',
    'error': '扫描失败'
  }
  return statusMap[status] || '未知'
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const handleManualScan = async () => {
  try {
    const success = await emailStore.startManualScan()
    if (success) {
      ElMessage.success('邮箱扫描已启动')
    } else {
      ElMessage.error('启动邮箱扫描失败')
    }
  } catch (error) {
    ElMessage.error('启动邮箱扫描失败')
  }
}

const handleToggleActive = async (config: EmailConfig) => {
  try {
    const success = await emailStore.updateConfig(config.id, {
      is_active: config.is_active
    })
    
    if (success) {
      ElMessage.success(`邮箱配置已${config.is_active ? '启用' : '禁用'}`)
    } else {
      // 恢复状态
      config.is_active = !config.is_active
      ElMessage.error('更新配置状态失败')
    }
  } catch (error) {
    config.is_active = !config.is_active
    ElMessage.error('更新配置状态失败')
  }
}

const editConfig = (config: EmailConfig) => {
  editingConfig.value = config
  Object.assign(configForm, {
    email_address: config.email_address,
    imap_server: config.imap_server,
    imap_port: config.imap_port,
    username: config.username,
    password: '', // 密码不回显
    scan_days: config.scan_days
  })
  showConfigDialog.value = true
}

const deleteConfig = async (config: EmailConfig) => {
  try {
    await ElMessageBox.confirm(`确定要删除邮箱配置 "${config.email_address}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const success = await emailStore.deleteConfig(config.id)
    if (success) {
      ElMessage.success('邮箱配置删除成功')
    } else {
      ElMessage.error('删除邮箱配置失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除邮箱配置失败')
    }
  }
}

const testConnection = async () => {
  if (!configFormRef.value) return
  
  try {
    await configFormRef.value.validate()
    testingConnection.value = true
    
    const success = await emailStore.testConnection(configForm)
    
    if (success) {
      ElMessage.success('邮箱连接测试成功')
    } else {
      ElMessage.error('邮箱连接测试失败，请检查配置')
    }
  } catch (error) {
    console.error('测试连接失败:', error)
  } finally {
    testingConnection.value = false
  }
}

const handleSaveConfig = async () => {
  if (!configFormRef.value) return
  
  try {
    await configFormRef.value.validate()
    configLoading.value = true
    
    let success = false
    
    if (editingConfig.value) {
      // 编辑模式
      const updateData: EmailConfigUpdate = { ...configForm }
      if (!updateData.password) {
        delete updateData.password // 如果密码为空，不更新密码
      }
      success = await emailStore.updateConfig(editingConfig.value.id, updateData)
    } else {
      // 新增模式
      success = await emailStore.createConfig(configForm)
    }
    
    if (success) {
      ElMessage.success(`邮箱配置${editingConfig.value ? '更新' : '创建'}成功`)
      showConfigDialog.value = false
    } else {
      ElMessage.error(`${editingConfig.value ? '更新' : '创建'}邮箱配置失败`)
    }
  } catch (error) {
    console.error('保存配置失败:', error)
  } finally {
    configLoading.value = false
  }
}

const handleCloseConfigDialog = () => {
  configFormRef.value?.resetFields()
  Object.assign(configForm, {
    email_address: '',
    imap_server: '',
    imap_port: 993,
    username: '',
    password: '',
    scan_days: 7
  })
  editingConfig.value = null
}

onMounted(() => {
  emailStore.fetchConfigs()
})
</script>

<style scoped>
.settings {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.scan-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.scan-status {
  font-size: 14px;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  margin-top: 4px;
}
</style>