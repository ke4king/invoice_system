import axios from 'axios'
import type { AxiosResponse, AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

// 创建axios实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError) => {
    const { response } = error
    // 允许在请求级别通过自定义头关闭全局错误 toast/处理
    const suppressToast = (error.config as any)?.headers?.['X-Suppress-Error-Toast'] === 'true'
    if (suppressToast) {
      return Promise.reject(error)
    }
    
    if (response) {
      const { status, data } = response
      
      switch (status) {
        case 401:
      ElMessage.error('登录已过期，请重新登录')
          const userStore = useUserStore()
          userStore.logout()
      if (router.currentRoute.value.name !== 'Login') {
        router.push('/login')
      }
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 422:
          ElMessage.error('请求参数错误')
          break
        case 429:
          ElMessage.error('请求过于频繁，请稍后重试')
          break
        case 409:
          ElMessage.warning((data as any)?.detail?.message || '资源已存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error((data as any)?.detail || '请求失败')
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

export default api