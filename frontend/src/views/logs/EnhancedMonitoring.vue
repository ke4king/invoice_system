// 增强的前端日志查看组件
<template>
  <div class="enhanced-logs-page">
    <div class="page-header">
      <h1>增强型系统日志</h1>
      <div class="header-actions">
        <el-button @click="refreshLogs" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
        <el-button @click="exportLogs" type="primary">
          <el-icon><Download /></el-icon>
          导出日志
        </el-button>
        <el-button @click="showAdvancedSearch = !showAdvancedSearch" type="info">
          <el-icon><Search /></el-icon>
          高级搜索
        </el-button>
      </div>
    </div>

    <!-- 增强统计面板 -->
    <div class="enhanced-stats-panel">
      <el-row :gutter="20">
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-number">{{ statistics.total_logs }}</div>
            <div class="stat-label">总日志数</div>
            <div class="stat-change" :class="getChangeClass(statistics.daily_change)">
              {{ formatChange(statistics.daily_change) }}
            </div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-number">{{ statistics.error_logs }}</div>
            <div class="stat-label">错误日志</div>
            <div class="stat-change error">
              {{ statistics.error_rate }}%
            </div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-number">{{ statistics.success_rate }}%</div>
            <div class="stat-label">成功率</div>
            <div class="stat-trend" :class="getTrendClass(statistics.success_trend)">
              <el-icon><DataLine /></el-icon>
              {{ statistics.success_trend }}%
            </div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-number">{{ getActiveUsers() }}</div>
            <div class="stat-label">活跃用户</div>
            <div class="stat-info">今日</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-number">{{ getAvgResponseTime() }}ms</div>
            <div class="stat-label">平均响应</div>
            <div class="stat-info">{{ getResponseTrend() }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-number">{{ getSystemHealth() }}</div>
            <div class="stat-label">系统状态</div>
            <div class="stat-indicator" :class="healthStatus.status">
              <i class="status-dot"></i>
              {{ getHealthText() }}
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 错误类型分布图 -->
    <div class="error-analysis-section" v-if="statistics.error_logs > 0">
      <el-card>
        <div class="section-header">
          <h3>错误分析</h3>
          <el-button @click="analyzeErrors" size="small" type="warning">
            深度分析
          </el-button>
        </div>
        <div class="error-grid">
          <div class="error-types">
            <h4>错误类型分布</h4>
            <div class="error-item" v-for="error in statistics.by_level" :key="error.level">
              <div class="error-level" :class="error.level.toLowerCase()">
                {{ error.level }}
              </div>
              <div class="error-count">{{ error.count }}</div>
              <div class="error-percentage">
                {{ ((error.count / statistics.error_logs) * 100).toFixed(1) }}%
              </div>
            </div>
          </div>
          <div class="error-timeline">
            <h4>错误时间线</h4>
            <div ref="errorTimelineRef" class="timeline-chart"></div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 高级搜索面板 -->
    <el-collapse-transition>
      <div v-show="showAdvancedSearch" class="advanced-search-panel">
        <el-card>
          <el-form :model="advancedFilters" :inline="true" label-width="80px">
            <el-form-item label="用户ID">
              <el-input v-model="advancedFilters.user_id" placeholder="用户ID" />
            </el-form-item>
            <el-form-item label="资源类型">
              <el-select v-model="advancedFilters.resource_type" placeholder="选择资源类型">
                <el-option label="发票" value="invoice" />
                <el-option label="邮箱" value="email" />
                <el-option label="系统" value="system" />
                <el-option label="打印" value="print" />
              </el-select>
            </el-form-item>
            <el-form-item label="IP地址">
              <el-input v-model="advancedFilters.ip_address" placeholder="IP地址" />
            </el-form-item>
            <el-form-item label="响应时间">
              <el-slider
                v-model="advancedFilters.response_time_range"
                range
                :min="0"
                :max="5000"
                :step="100"
                show-stops
                show-input
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="performAdvancedSearch">搜索</el-button>
              <el-button @click="resetAdvancedFilters">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </el-collapse-transition>

    <!-- 实时日志流 -->
    <el-card class="realtime-logs">
      <div class="section-header">
        <h3>实时日志流</h3>
        <div class="controls">
          <el-switch 
            v-model="realtimeEnabled" 
            @change="toggleRealtime"
            active-text="实时模式"
          />
          <el-button @click="pauseRealtime" :disabled="!realtimeEnabled" size="small">
            {{ realtimePaused ? '继续' : '暂停' }}
          </el-button>
          <el-button @click="clearRealtime" size="small" type="danger">
            清空
          </el-button>
        </div>
      </div>
      <div class="realtime-container" ref="realtimeContainer">
        <div 
          v-for="log in realtimeLogs" 
          :key="log.id" 
          class="realtime-log-item"
          :class="log.log_level.toLowerCase()"
        >
          <span class="timestamp">{{ formatTime(log.created_at) }}</span>
          <span class="level">{{ log.log_level }}</span>
          <span class="type">{{ getLogTypeLabel(log.log_type) }}</span>
          <span class="message">{{ log.message }}</span>
        </div>
      </div>
    </el-card>

    <!-- 性能监控图表 -->
    <div class="performance-section">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card>
            <div class="section-header">
              <h3>系统性能趋势</h3>
              <el-select v-model="performancePeriod" @change="updatePerformanceData" size="small">
                <el-option label="1小时" :value="1" />
                <el-option label="6小时" :value="6" />
                <el-option label="24小时" :value="24" />
                <el-option label="7天" :value="168" />
              </el-select>
            </div>
            <div ref="performanceChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <div class="section-header">
              <h3>系统资源使用</h3>
            </div>
            <div class="resource-metrics">
              <div class="metric-item">
                <div class="metric-label">CPU使用率</div>
                <el-progress :percentage="systemMetrics.cpu_usage" :color="getProgressColor(systemMetrics.cpu_usage)" />
              </div>
              <div class="metric-item">
                <div class="metric-label">内存使用率</div>
                <el-progress :percentage="systemMetrics.memory_usage" :color="getProgressColor(systemMetrics.memory_usage)" />
              </div>
              <div class="metric-item">
                <div class="metric-label">磁盘使用率</div>
                <el-progress :percentage="systemMetrics.disk_usage" :color="getProgressColor(systemMetrics.disk_usage)" />
              </div>
              <div class="metric-item">
                <div class="metric-label">网络延迟</div>
                <div class="metric-value">{{ systemMetrics.network_latency }}ms</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { 
  Refresh, Download, Search, DataLine 
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getLogStatistics, exportLogsCSV, exportLogsExcel } from '@/api/logs'
import { formatDateTime } from '@/utils/format'

// 响应式数据
const loading = ref(false)
const showAdvancedSearch = ref(false)
const realtimeEnabled = ref(false)
const realtimePaused = ref(false)
const performancePeriod = ref(24)

type LevelCount = { level: string; count: number }
type TypeCount = { type: string; count: number }
type DateCount = { date: string; count: number }

const statistics = reactive({
  total_logs: 0,
  error_logs: 0,
  success_rate: 0,
  error_rate: 0,
  daily_change: 0,
  success_trend: 0,
  by_type: [] as TypeCount[],
  by_level: [] as LevelCount[],
  by_date: [] as DateCount[]
})

const healthStatus = reactive({
  status: 'healthy',
  database: { healthy: true },
  recent_errors: 0
})

const systemMetrics = reactive({
  cpu_usage: 0,
  memory_usage: 0,
  disk_usage: 0,
  network_latency: 0
})

const advancedFilters = reactive({
  user_id: '',
  resource_type: '',
  ip_address: '',
  response_time_range: [0, 1000]
})

type RealtimeLog = { id: number; created_at: string; log_level: string; log_type: string; message: string }
const realtimeLogs = ref<RealtimeLog[]>([])
let realtimeInterval: ReturnType<typeof setInterval> | null = null
let performanceChart: echarts.ECharts | null = null

// 图表引用
const errorTimelineRef = ref()
const performanceChartRef = ref()
const realtimeContainer = ref()

// 方法
const refreshLogs = async () => {
  loading.value = true
  try {
    await Promise.all([
      getStatistics(),
      getSystemMetrics(),
      getHealthStatus()
    ])
    ElMessage.success('数据刷新成功')
  } catch (error) {
    ElMessage.error('数据刷新失败')
  } finally {
    loading.value = false
  }
}

const getStatistics = async () => {
  try {
    const response = await getLogStatistics(7)
    Object.assign(statistics, {
      total_logs: response.data?.total_logs || 0,
      error_logs: response.data?.by_level?.find(item => item.level === 'ERROR')?.count || 0,
      success_rate: 85, // 模拟数据
      by_type: response.data?.by_type || [],
      by_level: response.data?.by_level || [],
      by_date: response.data?.by_date || [],
      error_rate: response.data?.total_logs > 0 ? ((response.data?.by_level?.find(item => item.level === 'ERROR')?.count || 0) / response.data.total_logs * 100).toFixed(1) : 0,
      daily_change: Math.floor(Math.random() * 20) - 10, // 模拟数据
      success_trend: Math.floor(Math.random() * 10) - 5   // 模拟数据
    })
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

const getSystemMetrics = async () => {
  // 模拟系统指标数据
  Object.assign(systemMetrics, {
    cpu_usage: Math.floor(Math.random() * 30) + 20,
    memory_usage: Math.floor(Math.random() * 40) + 30,
    disk_usage: Math.floor(Math.random() * 20) + 40,
    network_latency: Math.floor(Math.random() * 50) + 10
  })
}

const getHealthStatus = async () => {
  try {
    // 实际应该调用健康检查API
    Object.assign(healthStatus, {
      status: 'healthy',
      database: { healthy: true },
      recent_errors: statistics.error_logs
    })
  } catch (error) {
    console.error('获取健康状态失败:', error)
  }
}

const toggleRealtime = (enabled: boolean | string | number) => {
  const isEnabled = Boolean(enabled)
  if (isEnabled) {
    startRealtimeMonitoring()
  } else {
    stopRealtimeMonitoring()
  }
}

const startRealtimeMonitoring = () => {
  realtimeInterval = setInterval(async () => {
    if (!realtimePaused.value) {
      // 模拟实时日志数据
      const newLog: RealtimeLog = {
        id: Date.now(),
        created_at: new Date().toISOString(),
        log_level: ['INFO', 'WARNING', 'ERROR'][Math.floor(Math.random() * 3)],
        log_type: ['auth', 'invoice', 'email', 'ocr'][Math.floor(Math.random() * 4)],
        message: `实时日志消息 ${Date.now()}`
      }
      
      realtimeLogs.value.unshift(newLog)
      if (realtimeLogs.value.length > 100) {
        realtimeLogs.value = realtimeLogs.value.slice(0, 100)
      }
      
      // 自动滚动到顶部
      nextTick(() => {
        if (realtimeContainer.value) {
          realtimeContainer.value.scrollTop = 0
        }
      })
    }
  }, 2000)
}

const stopRealtimeMonitoring = () => {
  if (realtimeInterval) {
    clearInterval(realtimeInterval)
    realtimeInterval = null
  }
}

const pauseRealtime = () => {
  realtimePaused.value = !realtimePaused.value
}

const clearRealtime = () => {
  realtimeLogs.value = []
}

// 工具方法
const formatChange = (change: number) => {
  const sign = change > 0 ? '+' : ''
  return `${sign}${change}%`
}

const getChangeClass = (change: number) => {
  return change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'
}

const getTrendClass = (trend: number) => {
  return trend > 0 ? 'up' : trend < 0 ? 'down' : 'stable'
}

const getProgressColor = (percentage: number) => {
  if (percentage < 50) return '#67C23A'
  if (percentage < 80) return '#E6A23C'
  return '#F56C6C'
}

const getActiveUsers = () => Math.floor(Math.random() * 10) + 1
const getAvgResponseTime = () => Math.floor(Math.random() * 500) + 100
const getResponseTrend = () => Math.random() > 0.5 ? '↗️ 改善' : '↘️ 下降'
const getSystemHealth = () => healthStatus.status === 'healthy' ? '良好' : '异常'
const getHealthText = () => {
  const texts: Record<'healthy' | 'degraded' | 'unhealthy', string> = { healthy: '健康', degraded: '降级', unhealthy: '异常' }
  return texts[healthStatus.status as 'healthy' | 'degraded' | 'unhealthy'] || '未知'
}

const getLogTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    auth: '认证', invoice: '发票', email: '邮箱', 
    ocr: 'OCR', print: '打印', system: '系统'
  }
  return labels[type] || type
}

const formatTime = (dateString: string) => {
  return new Date(dateString).toLocaleTimeString()
}

const exportLogs = async () => {
  try {
    const result = await ElMessageBox.confirm(
      '导出增强监控日志数据，请选择导出格式：',
      '选择导出格式',
      {
        confirmButtonText: 'CSV格式',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    // 显示格式选择对话框
    const format = await ElMessageBox.prompt(
      '请选择导出格式：\n1. CSV - 适合Excel打开\n2. JSON - 完整结构化数据\n3. Excel - 包含统计信息',
      '选择导出格式',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: 'csv',
        inputValidator: (value) => {
          if (!['csv', 'json', 'excel'].includes(value)) {
            return '请输入 csv、json 或 excel'
          }
          return true
        },
        inputErrorMessage: '请输入有效的格式名称',
        inputPlaceholder: '输入 csv、json 或 excel'
      }
    )
    
    const formatValue = format.value
    
    // 显示进度条
    const progressInstance = ElLoading.service({
      lock: true,
      text: '正在导出监控日志数据...',
      background: 'rgba(0, 0, 0, 0.7)'
    })
    
    try {
      // 准备导出参数
      const exportParams = {
        log_type: 'system', // 导出系统监控相关日志
        limit: 50000 // 最多导出5万条
      }
      
      let blob: Blob
      let filename: string
      
      // 根据选择的格式调用不同API
      switch (formatValue) {
        case 'csv':
          // 使用URL方式下载CSV
          const csvUrl = await exportLogsCSV(exportParams)
          filename = `enhanced_monitoring_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`
          const csvBlobUrl = window.URL.createObjectURL(csvUrl)
          window.open(csvBlobUrl, '_blank')
          ElMessage.success(`监控日志导出成功！文件名：${filename}`)
          return
        case 'excel':
          const excelUrl = await exportLogsExcel(exportParams)
          filename = `enhanced_monitoring_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.xlsx`
          const excelBlobUrl = window.URL.createObjectURL(excelUrl)
          window.open(excelBlobUrl, '_blank')
          ElMessage.success(`监控日志导出成功！文件名：${filename}`)
          return
        case 'json':
          // JSON格式需要通过API获取数据然后生成文件
          const response = await getLogStatistics(7)
          const jsonData = JSON.stringify(response.data, null, 2)
          blob = new Blob([jsonData], { type: 'application/json' })
          filename = `enhanced_monitoring_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
          break
        default:
          throw new Error('不支持的导出格式')
      }
      
      // 下载文件
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.style.display = 'none'
      document.body.appendChild(link)
      link.click()
      
      // 清理
      window.URL.revokeObjectURL(url)
      document.body.removeChild(link)
      
      ElMessage.success(`监控日志导出成功！文件名：${filename}`)
      
    } finally {
      progressInstance.close()
    }
    
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('导出监控日志失败:', error)
      ElMessage.error('导出监控日志失败，请稍后重试')
    }
  }
}

const analyzeErrors = () => {
  ElMessage.info('错误分析功能开发中...')
}

const performAdvancedSearch = () => {
  ElMessage.info('高级搜索功能开发中...')
}

const resetAdvancedFilters = () => {
  Object.assign(advancedFilters, {
    user_id: '',
    resource_type: '',
    ip_address: '',
    response_time_range: [0, 1000]
  })
}

const updatePerformanceData = () => {
  // 更新性能图表数据
  if (performanceChart) {
    // 模拟性能数据
    const data = Array.from({length: performancePeriod.value}, (_, i) => 
      Math.floor(Math.random() * 100) + 50
    )
    
    performanceChart.setOption({
      series: [{ data }]
    })
  }
}

// 生命周期
onMounted(() => {
  refreshLogs()
  
  // 初始化性能图表
  nextTick(() => {
    if (performanceChartRef.value) {
      performanceChart = echarts.init(performanceChartRef.value)
      performanceChart.setOption({
        title: { show: false },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: Array.from({length: 24}, (_, i) => `${i}:00`) },
        yAxis: { type: 'value', name: 'ms' },
        series: [{
          data: Array.from({length: 24}, () => Math.floor(Math.random() * 100) + 50),
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.3 }
        }]
      })
    }
  })
})

onUnmounted(() => {
  stopRealtimeMonitoring()
  if (performanceChart) {
    performanceChart.dispose()
  }
})
</script>

<style scoped>
.enhanced-logs-page {
  padding: 20px;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.enhanced-stats-panel {
  margin-bottom: 20px;
}

.stat-item {
  background: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  position: relative;
  overflow: hidden;
}

.stat-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #409EFF, #67C23A);
}

.stat-number {
  font-size: 28px;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #7f8c8d;
  margin-bottom: 8px;
}

.stat-change {
  font-size: 12px;
  font-weight: 500;
}

.stat-change.positive { color: #67C23A; }
.stat-change.negative { color: #F56C6C; }
.stat-change.neutral { color: #909399; }

.stat-trend.up { color: #67C23A; }
.stat-trend.down { color: #F56C6C; }
.stat-trend.stable { color: #909399; }

.stat-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67C23A;
}

.stat-indicator.degraded .status-dot { background: #E6A23C; }
.stat-indicator.unhealthy .status-dot { background: #F56C6C; }

.error-analysis-section {
  margin-bottom: 20px;
}

.error-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
}

.error-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.error-level {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}

.error-level.error { background: #F56C6C; }
.error-level.warning { background: #E6A23C; }
.error-level.critical { background: #C0392B; }

.advanced-search-panel {
  margin-bottom: 20px;
}

.realtime-logs {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.realtime-container {
  height: 300px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 8px;
  background: #1e1e1e;
  color: #fff;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.realtime-log-item {
  padding: 4px 0;
  border-left: 3px solid transparent;
  padding-left: 8px;
  margin-bottom: 2px;
}

.realtime-log-item.info { border-left-color: #409EFF; }
.realtime-log-item.warning { border-left-color: #E6A23C; }
.realtime-log-item.error { border-left-color: #F56C6C; }

.realtime-log-item .timestamp { color: #95a5a6; }
.realtime-log-item .level { 
  color: #e74c3c; 
  font-weight: bold;
  margin: 0 8px;
}
.realtime-log-item .type { 
  color: #3498db; 
  margin-right: 8px;
}

.performance-section {
  margin-bottom: 20px;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.resource-metrics {
  padding: 16px 0;
}

.metric-item {
  margin-bottom: 16px;
}

.metric-label {
  margin-bottom: 8px;
  font-size: 14px;
  color: #666;
}

.metric-value {
  font-size: 18px;
  font-weight: bold;
  color: #2c3e50;
}

.timeline-chart {
  height: 200px;
}
</style>