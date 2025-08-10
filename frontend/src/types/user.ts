export interface User {
  id: number
  username: string
  email?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface PasswordChangeRequest {
  current_password: string
  new_password: string
}