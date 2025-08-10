<template>
  <div class="login-container">
    <el-card class="login-card">
      <div class="login-header">
        <h1 class="login-title">发票管理系统</h1>
      </div>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            size="large"
            placeholder="用户名"
            :prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            size="large"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="w-full"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    await loginFormRef.value.validate()
    loading.value = true
    
    // 登录页自身负责错误提示，避免全局拦截器重复 toast
    const success = await userStore.login(loginForm)
    
    if (success) {
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      ElMessage.error('用户名或密码错误')
    }
  } catch (error) {
    console.error('登录失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  position: relative;
  padding: 24px;
  /* 主题渐变背景（亮色） */
  background:
    radial-gradient(1200px 600px at 10% 10%, color-mix(in srgb, var(--theme-primary-light, #79bbff) 30%, transparent) 0%, transparent 60%),
    radial-gradient(900px 600px at 90% 90%, color-mix(in srgb, var(--theme-primary, #409EFF) 28%, transparent) 0%, transparent 55%),
    linear-gradient(135deg, color-mix(in srgb, var(--el-bg-color-page) 90%, transparent) 0%, color-mix(in srgb, var(--el-bg-color) 100%, transparent) 100%);
}

.login-card {
  width: 420px;
  padding: 32px 36px;
  border-radius: 16px;
  border: 1px solid var(--el-border-color-lighter);
  background: color-mix(in srgb, var(--el-bg-color) 88%, transparent);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}


/* :deep(.el-input__wrapper) { padding: 10px 14px; min-height: 40px; } */

.login-form { display: flex; flex-direction: column; gap: 36px; }
:deep(.el-form-item) { margin: 0; }

:deep(.el-button.w-full) { height: 36px; font-size: 15px; }

/* 校验错误提示与输入框间距适度拉开 */
:deep(.el-form-item.is-error .el-form-item__error) {
  margin-top: 12px;
}

@media (min-width: 992px) {
  .login-card { width: 460px; }
}

/* 深色模式的背景优化 */
:global(.dark) .login-container {
  background:
    radial-gradient(1200px 600px at 10% 10%, color-mix(in srgb, var(--theme-primary, #409EFF) 20%, transparent) 0%, transparent 60%),
    radial-gradient(900px 600px at 90% 90%, color-mix(in srgb, var(--theme-primary-light, #79bbff) 18%, transparent) 0%, transparent 55%),
    linear-gradient(135deg, color-mix(in srgb, #0a0f1a 92%, transparent) 0%, color-mix(in srgb, #0b1220 100%, transparent) 100%);
}
</style>
