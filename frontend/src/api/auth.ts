import type { LoginRequest, LoginResponse, User, PasswordChangeRequest } from '@/types/user'
import api from '@/utils/request'

// 用户登录（使用 application/x-www-form-urlencoded 符合后端 OAuth2PasswordRequestForm）
export const login = (data: LoginRequest) => {
  const body = new URLSearchParams()
  body.append('username', data.username)
  body.append('password', data.password)
  return api.post<LoginResponse>('/auth/login', body, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      // 登录页自行处理错误，屏蔽全局 toast
      'X-Suppress-Error-Toast': 'true',
    }
  })
}

// 获取当前用户信息
export const getCurrentUser = () => {
  return api.get<User>('/auth/me')
}

// 修改密码
export const changePassword = (data: PasswordChangeRequest) => {
  return api.post('/auth/change-password', data)
}

// 用户登出
export const logout = () => {
  return api.post('/auth/logout')
}