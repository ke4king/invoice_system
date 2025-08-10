<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统监控</h1>
      <div class="header-actions">
        <div class="inline-group">
          <span class="label">时间范围:</span>
          <el-radio-group v-model="selectedPeriod" size="small" @change="handlePeriodChange">
            <el-radio-button :label="7">7天</el-radio-button>
            <el-radio-button :label="30">30天</el-radio-button>
            <el-radio-button :label="90">90天</el-radio-button>
          </el-radio-group>
        </div>

        <div class="inline-group">
          <span class="label">自动刷新:</span>
          <el-switch v-model="autoRefreshEnabled" @change="setupAutoRefresh" />
          <el-select v-model="autoRefreshSeconds" :disabled="!autoRefreshEnabled" size="small" style="width: 110px" @change="setupAutoRefresh">
            <el-option :value="30" label="30秒" />
            <el-option :value="60" label="1分钟" />
            <el-option :value="300" label="5分钟" />
          </el-select>
        </div>

        <el-button @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 系统健康状态 -->
    <el-card class="health-card" :class="healthStatus.status">
      <div class="health-header">
        <div class="health-icon">
          <el-icon v-if="healthStatus.status === 'healthy'"><CircleCheckFilled /></el-icon>
          <el-icon v-else-if="healthStatus.status === 'degraded'"><Warning /></el-icon>
          <el-icon v-else><CircleCloseFilled /></el-icon>
        </div>
        <div class="health-info">
          <div class="health-title">
            系统状态: {{ getHealthStatusText(healthStatus.status) }}
          </div>
          <div class="health-time">
            最近更新时间: {{ formatDateTime(lastUpdatedAt) }}
          </div>
        </div>
        <div class="health-details">
          <el-tag :type="healthStatus.database.healthy ? 'success' : 'danger'" size="small">
            数据库: {{ healthStatus.database.healthy ? '正常' : '异常' }}
          </el-tag>
          <el-tag type="warning" size="small" v-if="healthStatus.recent_errors > 0">
            最近错误: {{ healthStatus.recent_errors }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <!-- 统计概览（统一使用全局 stats-grid/stat-card 风格） -->
    <div class="overview-section">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-number">{{ dashboardStats.invoice_stats?.recent_invoices || 0 }}</div>
          <div class="stat-label">本期新增发票</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ dashboardStats.ocr_stats?.success_rate || 0 }}%</div>
          <div class="stat-label">OCR成功率</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ dashboardStats.email_stats?.active_accounts || 0 }}</div>
          <div class="stat-label">活跃邮箱账户</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ getTotalActivity() }}</div>
          <div class="stat-label">总活动</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-section">
      <el-row :gutter="20">
        <!-- 活动趋势图 -->
        <el-col :xs="24" :md="12">
          <el-card>
            <el-skeleton :loading="loading" animated :rows="6">
              <template #default>
                <div class="chart-header">
                  <h3>活动趋势</h3>
                </div>
                <div v-if="(dashboardStats.activity_stats?.daily_activity || []).length > 0" ref="activityChartRef" class="chart-container"></div>
                <el-empty v-else description="暂无数据" />
              </template>
            </el-skeleton>
          </el-card>
        </el-col>

        <!-- 日志类型分布 -->
        <el-col :xs="24" :md="12">
          <el-card>
            <el-skeleton :loading="loading" animated :rows="6">
              <template #default>
                <div class="chart-header">
                  <h3>日志类型分布</h3>
                </div>
                <div v-if="(dashboardStats.activity_stats?.by_type || []).length > 0" ref="typeChartRef" class="chart-container"></div>
                <el-empty v-else description="暂无数据" />
              </template>
            </el-skeleton>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px;">
        <!-- 发票状态分布 -->
        <el-col :xs="24" :md="12">
          <el-card>
            <el-skeleton :loading="loading" animated :rows="6">
              <template #default>
                <div class="chart-header">
                  <h3>发票状态分布</h3>
                </div>
                <div v-if="(dashboardStats.invoice_stats?.by_status || []).length > 0" ref="statusChartRef" class="chart-container"></div>
                <el-empty v-else description="暂无数据" />
              </template>
            </el-skeleton>
          </el-card>
        </el-col>

        <!-- 错误类型分布 -->
        <el-col :xs="24" :md="12">
          <el-card>
            <el-skeleton :loading="loading" animated :rows="6">
              <template #default>
                <div class="chart-header">
                  <h3>错误类型分布</h3>
                </div>
                <div v-if="(dashboardStats.error_stats?.by_type || []).length > 0" ref="errorChartRef" class="chart-container"></div>
                <el-empty v-else description="暂无数据" />
              </template>
            </el-skeleton>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 最近活动 -->
    <el-card class="recent-activity">
      <div class="card-header">
        <h3>最近活动</h3>
        <el-button type="text" @click="viewAllLogs">查看全部</el-button>
      </div>
      <el-skeleton :loading="loadingRecent" animated :rows="6">
        <template #default>
          <div class="activity-list">
            <div 
              v-for="activity in recentActivities" 
              :key="activity.id" 
              class="activity-item"
            >
              <div class="activity-icon" :class="(activity.log_level || '').toLowerCase()">
                <el-icon><Operation /></el-icon>
              </div>
              <div class="activity-content">
                <div class="activity-message">{{ activity.message }}</div>
                <div class="activity-meta">
                  <span class="activity-type">{{ getLogTypeLabel(activity.log_type) }}</span>
                  <span class="activity-time">{{ formatDateTime(activity.created_at) }}</span>
                </div>
              </div>
            </div>
            <div v-if="recentActivities.length === 0" class="no-activity">
              暂无最近活动
            </div>
          </div>
        </template>
      </el-skeleton>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Refresh, CircleCheckFilled, Warning, CircleCloseFilled, Document, View, 
  Message, DataLine, Operation 
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getLogStatistics, getSystemHealth, getPerformanceMetrics, getLogs, getDashboardStatistics } from '@/api/logs'
import { formatDateTime } from '@/utils/format'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const selectedPeriod = ref(30)
const autoRefreshEnabled = ref(false)
const autoRefreshSeconds = ref(60)
let autoRefreshTimer: any = null
const lastUpdatedAt = ref<string>('')

const healthStatus = reactive({
  status: 'healthy',
  database: { healthy: true, error: null },
  recent_errors: 0,
  check_time: new Date().toISOString()
})

const dashboardStats = reactive({
  period_days: 30,
  invoice_stats: null,
  ocr_stats: null,
  email_stats: null,
  activity_stats: null,
  error_stats: null,
  last_updated: ''
})

const recentActivities = ref<any[]>([])
const loadingRecent = ref(false)

// 计算属性
const errorCount = computed(() => {
  const total = (dashboardStats as any)?.error_stats?.total_errors
  return typeof total === 'number' ? total : 0
})

// Chart refs
const activityChartRef = ref()
const typeChartRef = ref()
const statusChartRef = ref()
const errorChartRef = ref()

// Chart instances
let activityChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null
let errorChart: echarts.ECharts | null = null

// 方法
const refreshData = async () => {
  loading.value = true
  try {
    await Promise.all([
      getHealthStatus(),
      getDashboardStats(),
      fetchPerformanceMetrics()
    ])
    
    await nextTick()
    initCharts()
    lastUpdatedAt.value = new Date().toISOString()
  } catch (error) {
    ElMessage.error('刷新数据失败')
    console.error('刷新数据失败:', error)
  } finally {
    loading.value = false
  }
}

const getHealthStatus = async () => {
  try {
    const response = await getSystemHealth()
    const data = response.data
    Object.assign(healthStatus, data || {})
  } catch (error) {
    console.error('获取健康状态失败:', error)
  }
}

const getDashboardStats = async () => {
  try {
    const response = await getDashboardStatistics(selectedPeriod.value)
    const stats = response.data || ({} as any)

    Object.assign(dashboardStats, stats)

    await nextTick()
    updateChartsData()
    
  } catch (error) {
    console.error('获取仪表板统计失败:', error)
    // 设置默认数据以避免页面崩溃
    Object.assign(dashboardStats, {
      period_days: selectedPeriod.value,
      invoice_stats: { recent_invoices: 0, total_invoices: 0, amount_stats: { total: 0 }, by_status: [] },
      ocr_stats: { success_rate: 0, total_processed: 0, successful_ocr: 0 },
      email_stats: { active_accounts: 0, scan_activities: 0, processed_emails: 0 },
      activity_stats: { daily_activity: [], by_type: [], recent_activities: [] },
      error_stats: { total_errors: 0, by_level: [] },
      last_updated: new Date().toISOString()
    })
  }
}

const updateChartsData = () => {
  // 更新活动趋势图数据
  if (activityChart && dashboardStats.activity_stats?.daily_activity) {
    const dailyActivity = dashboardStats.activity_stats.daily_activity
    const dates = dailyActivity.map(item => item.date)
    const counts = dailyActivity.map(item => item.count)
    
    activityChart.setOption({
      xAxis: {
        data: dates.map(date => {
          const d = new Date(date)
          return `${d.getMonth() + 1}/${d.getDate()}`
        })
      },
      series: [{
        data: counts
      }]
    })
  }
  
  // 更新类型分布图数据
  if (typeChart && dashboardStats.activity_stats?.by_type) {
    const byType = dashboardStats.activity_stats.by_type
    const data = byType.map(item => ({
      name: getLogTypeLabel(item.type),
      value: item.count
    }))
    
    typeChart.setOption({
      series: [{
        data: data
      }]
    })
  }
  
  // 更新发票状态分布图数据
  if (statusChart && dashboardStats.invoice_stats?.by_status) {
    const byStatus = dashboardStats.invoice_stats.by_status
    const data = byStatus.map(item => ({
      name: getStatusLabel(item.status),
      value: item.count
    }))
    
    statusChart.setOption({
      series: [{
        data: data
      }]
    })
  }
  
  // 更新错误类型统计图数据
  if (errorChart && dashboardStats.error_stats?.by_type) {
    const byType = dashboardStats.error_stats.by_type
    const categories = byType.map((item: any) => getLogTypeLabel(item.type))
    const values = byType.map((item: any) => item.count)

    errorChart.setOption({
      xAxis: {
        data: categories
      },
      series: [{
        data: values
      }]
    })
  }
}

const fetchPerformanceMetrics = async () => {
  try {
    const response = await getPerformanceMetrics(24)
    console.log('性能指标:', response)
  } catch (error) {
    console.error('获取性能指标失败:', error)
  }
}

const handlePeriodChange = () => {
  refreshData()
}

const fetchRecentActivities = async () => {
  try {
    loadingRecent.value = true
    const res = await getLogs({ page: 1, pageSize: 10 })
    recentActivities.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    recentActivities.value = []
  } finally {
    loadingRecent.value = false
  }
}

const setupAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
  if (autoRefreshEnabled.value) {
    autoRefreshTimer = setInterval(() => {
      refreshData()
      fetchRecentActivities()
    }, autoRefreshSeconds.value * 1000)
  }
}

const handleResize = () => {
  activityChart?.resize()
  typeChart?.resize()
  statusChart?.resize()
  errorChart?.resize()
}

const initCharts = () => {
  initActivityChart()
  initTypeChart()
  initStatusChart()
  initErrorChart()
}

const initActivityChart = () => {
  if (!activityChartRef.value) return
  
  if (activityChart) {
    activityChart.dispose()
  }
  
  activityChart = echarts.init(activityChartRef.value)
  
  const dailyActivity = dashboardStats.activity_stats?.daily_activity || []
  const dates = dailyActivity.map(item => item.date)
  const counts = dailyActivity.map(item => item.count)
  
  const option = {
    title: {
      show: false
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        formatter: (value: string) => {
          const date = new Date(value)
          return `${date.getMonth() + 1}/${date.getDate()}`
        }
      }
    },
    yAxis: {
      type: 'value'
    },
    series: [{
      data: counts,
      type: 'line',
      smooth: true,
      areaStyle: {
        opacity: 0.3
      },
      itemStyle: {
        color: '#409EFF'
      }
    }]
  }
  
  activityChart.setOption(option)
}

const initTypeChart = () => {
  if (!typeChartRef.value) return
  
  if (typeChart) {
    typeChart.dispose()
  }
  
  typeChart = echarts.init(typeChartRef.value)
  
  const byType = dashboardStats.activity_stats?.by_type || []
  const data = byType.map(item => ({
    name: getLogTypeLabel(item.type),
    value: item.count
  }))
  
  const option = {
    tooltip: {
      trigger: 'item'
    },
    series: [{
      type: 'pie',
      radius: '70%',
      data: data,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }
  
  typeChart.setOption(option)
}

const initStatusChart = () => {
  if (!statusChartRef.value) return
  
  if (statusChart) {
    statusChart.dispose()
  }
  
  statusChart = echarts.init(statusChartRef.value)
  
  const byStatus = dashboardStats.invoice_stats?.by_status || []
  const data = byStatus.map(item => ({
    name: getStatusLabel(item.status),
    value: item.count
  }))
  
  const option = {
    tooltip: {
      trigger: 'item'
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: data,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }
  
  statusChart.setOption(option)
}

const initErrorChart = () => {
  if (!errorChartRef.value) return
  
  if (errorChart) {
    errorChart.dispose()
  }
  
  errorChart = echarts.init(errorChartRef.value)
  
  const byTypeErr = dashboardStats.error_stats?.by_type || []
  const categories = byTypeErr.map((item: any) => getLogTypeLabel(item.type))
  const values = byTypeErr.map((item: any) => item.count)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: categories
    },
    yAxis: {
      type: 'value'
    },
    series: [{
      data: values,
      type: 'bar',
      itemStyle: {
        color: '#F56C6C'
      }
    }]
  }
  
  errorChart.setOption(option)
}

// 工具方法
const getHealthStatusText = (status: string) => {
  const statusMap = {
    healthy: '健康',
    degraded: '降级',
    unhealthy: '异常'
  }
  return statusMap[status] || status
}

const formatAmount = (amount: number) => {
  return (amount / 10000).toFixed(1) + '万'
}

const getTotalActivity = () => {
  const byType = dashboardStats.activity_stats?.by_type || []
  return byType.reduce((sum, item) => sum + item.count, 0)
}

const getActiveTypes = () => {
  const byType = dashboardStats.activity_stats?.by_type || []
  return byType.length
}

const getLogTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    auth: '认证',
    invoice: '发票',
    email: '邮箱',
    ocr: 'OCR',
    print: '打印',
    system: '系统'
  }
  return labels[type] || type
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    pending: '待处理'
  }
  return labels[status] || status
}

const viewAllLogs = () => {
  router.push('/logs')
}

// 生命周期
onMounted(() => {
  refreshData()
  fetchRecentActivities()
  setupAutoRefresh()
  
  // 窗口大小变化时重新调整图表
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.monitoring-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.inline-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.inline-group .label {
  color: #909399;
  font-size: 12px;
}

.health-card {
  margin-bottom: 20px;
  border-left: 4px solid #67C23A;
}

.health-card.degraded {
  border-left-color: #E6A23C;
}

.health-card.unhealthy {
  border-left-color: #F56C6C;
}

.health-header {
  display: flex;
  align-items: center;
  gap: 15px;
}

.health-icon {
  font-size: 24px;
  color: #67C23A;
}

.health-card.degraded .health-icon {
  color: #E6A23C;
}

.health-card.unhealthy .health-icon {
  color: #F56C6C;
}

.health-info {
  flex: 1;
}

.health-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 4px;
}

.health-time {
  font-size: 13px;
  color: #909399;
}

.health-details {
  display: flex;
  gap: 8px;
}

.overview-section {
  margin-bottom: 20px;
}

.overview-card {
  height: 140px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.card-icon {
  font-size: 20px;
  opacity: 0.7;
}

.card-icon.invoice { color: #409EFF; }
.card-icon.ocr { color: #67C23A; }
.card-icon.email { color: #E6A23C; }
.card-icon.activity { color: #909399; }

.card-stats {
  height: calc(100% - 45px);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.main-stat {
  text-align: center;
  margin-bottom: 15px;
}

.main-stat .value {
  display: block;
  font-size: 28px;
  font-weight: 600;
  line-height: 1;
  margin-bottom: 5px;
}

.main-stat .label {
  font-size: 13px;
  color: #909399;
}

.sub-stats {
  display: flex;
  justify-content: space-around;
}

.sub-stat {
  text-align: center;
}

.sub-stat .value {
  display: block;
  font-size: 14px;
  font-weight: 500;
  line-height: 1;
  margin-bottom: 3px;
}

.sub-stat .label {
  font-size: 12px;
  color: #909399;
}

.charts-section {
  margin-bottom: 20px;
}

.chart-header {
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #EBEEF5;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.chart-container {
  height: 300px;
}

.recent-activity {
  margin-bottom: 20px;
}

.activity-list {
  max-height: 400px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #F5F7FA;
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: white;
  flex-shrink: 0;
}

.activity-icon.info { background-color: #409EFF; }
.activity-icon.warning { background-color: #E6A23C; }
.activity-icon.error { background-color: #F56C6C; }
.activity-icon.debug { background-color: #909399; }

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-message {
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 4px;
  word-break: break-word;
}

.activity-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.no-activity {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}
</style>