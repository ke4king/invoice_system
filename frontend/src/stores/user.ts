import { defineStore } from 'pinia'
import type { User, LoginRequest, LoginResponse, PasswordChangeRequest } from '@/types/user'
import { login, getCurrentUser, changePassword } from '@/api/auth'

interface UserState {
  user: User | null
  token: string | null
  isLoggedIn: boolean
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    user: null,
    token: localStorage.getItem('token'),
    isLoggedIn: !!localStorage.getItem('token'),
  }),
  
  getters: {
    userInfo: (state) => state.user,
    isAdmin: (state) => state.user?.is_superuser || false,
  },
  
  actions: {
    async login(loginData: LoginRequest): Promise<boolean> {
      try {
        const response = await login(loginData)
        const { access_token, user } = response.data
        
        this.token = access_token
        this.user = user
        this.isLoggedIn = true
        
        localStorage.setItem('token', access_token)
        localStorage.setItem('user', JSON.stringify(user))
        // 登录后主动拉取最新用户信息，增强一致性
        try { await this.fetchUserInfo() } catch {}
        
        return true
      } catch (error) {
        return false
      }
    },
    
    async fetchUserInfo(): Promise<void> {
      try {
        const response = await getCurrentUser()
        this.user = response.data
        localStorage.setItem('user', JSON.stringify(response.data))
      } catch (error) {
        this.logout()
      }
    },
    
    async changePassword(passwordData: PasswordChangeRequest): Promise<boolean> {
      try {
        await changePassword(passwordData)
        return true
      } catch (error) {
        return false
      }
    },
    
    logout(): void {
      this.user = null
      this.token = null
      this.isLoggedIn = false
      
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
    
    // 从本地存储恢复用户状态
    restoreFromStorage(): void {
      const token = localStorage.getItem('token')
      const userStr = localStorage.getItem('user')
      
      if (token && userStr) {
        try {
          this.token = token
          this.user = JSON.parse(userStr)
          this.isLoggedIn = true
        } catch (error) {
          this.logout()
        }
      }
    },
  },
})