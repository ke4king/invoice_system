<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapsed ? '64px' : '220px'" :class="['sidebar', { collapsed: isCollapsed }]">
      <div class="logo" :class="{ collapsed: isCollapsed }">
        <div class="logo-icon">
          <img :src="logoUrl" alt="Logo" class="logo-img" />
        </div>
        <h2 class="logo-title">发票管理系统</h2>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        router
        :collapse="isCollapsed"
        :collapse-transition="false"
      >
        <el-menu-item index="/dashboard">
          <el-tooltip :effect="tooltipEffect" content="工作台" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><HomeFilled /></el-icon>
              <span>工作台</span>
            </div>
          </el-tooltip>
        </el-menu-item>
        
        <el-menu-item index="/invoices">
          <el-tooltip :effect="tooltipEffect" content="发票列表" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><Document /></el-icon>
              <span>发票列表</span>
            </div>
          </el-tooltip>
        </el-menu-item>

        <el-menu-item index="/invoices/upload">
          <el-tooltip :effect="tooltipEffect" content="发票上传" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><UploadFilled /></el-icon>
              <span>发票上传</span>
            </div>
          </el-tooltip>
        </el-menu-item>
        
        <el-menu-item index="/emails">
          <el-tooltip :effect="tooltipEffect" content="邮件列表" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><Message /></el-icon>
              <span>邮件列表</span>
            </div>
          </el-tooltip>
        </el-menu-item>
        
        <el-menu-item index="/print">
          <el-tooltip :effect="tooltipEffect" content="批量打印" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><Printer /></el-icon>
              <span>批量打印</span>
            </div>
          </el-tooltip>
        </el-menu-item>
        
        <el-menu-item index="/logs">
          <el-tooltip :effect="tooltipEffect" content="系统日志" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><Document /></el-icon>
              <span>系统日志</span>
            </div>
          </el-tooltip>
        </el-menu-item>

        <el-menu-item index="/monitoring">
          <el-tooltip :effect="tooltipEffect" content="系统监控" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><Monitor /></el-icon>
              <span>系统监控</span>
            </div>
          </el-tooltip>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-tooltip :effect="tooltipEffect" content="邮箱设置" placement="right" :disabled="!isCollapsed" :popper-options="tooltipPopperOptions">
            <div class="menu-item-inner">
              <el-icon><Setting /></el-icon>
              <span>邮箱设置</span>
            </div>
          </el-tooltip>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer" :class="{ collapsed: isCollapsed }">
        <div class="collapse-toggle" @click="isCollapsed = !isCollapsed" :title="isCollapsed ? '展开' : '收起'">
          <el-icon size="18">
            <Expand v-if="isCollapsed" />
            <Fold v-else />
          </el-icon>
        </div>
      </div>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute?.meta?.title">
              {{ currentRoute.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <div class="theme-toggle" @click="themeStore.toggleTheme()">
            <el-icon size="18">
              <Moon v-if="themeStore.currentTheme === 'light'" />
              <Sunny v-else />
            </el-icon>
          </div>
          
          <el-dropdown @command="handleCommand">
            <span class="el-dropdown-link">
              <el-avatar :size="32" :src="userAvatar">
                <el-icon><User /></el-icon>
              </el-avatar>
              <span class="username">{{ userStore.user?.username }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon>
                  修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
  
  <!-- 修改密码对话框 -->
  <el-dialog
    v-model="passwordDialogVisible"
    title="修改密码"
    width="400px"
    :before-close="handleClosePasswordDialog"
  >
    <el-form
      ref="passwordFormRef"
      :model="passwordForm"
      :rules="passwordRules"
      label-width="100px"
    >
      <el-form-item label="当前密码" prop="current_password">
        <el-input
          v-model="passwordForm.current_password"
          type="password"
          show-password
        />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input
          v-model="passwordForm.new_password"
          type="password"
          show-password
        />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input
          v-model="passwordForm.confirm_password"
          type="password"
          show-password
        />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">
          确定
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { 
  HomeFilled, 
  Document, 
  Printer, 
  Setting, 
  User, 
  ArrowDown,
  Monitor,
  Message,
  Moon,
  Sunny,
  Lock,
  SwitchButton,
  Fold,
  Expand,
  UploadFilled
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import logoUrl from '@/assets/logo.png'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const themeStore = useThemeStore()

const passwordDialogVisible = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref<FormInstance>()

const currentRoute = computed(() => route)
const activeMenu = computed(() => route.path)
const userAvatar = computed(() => '')

// 初始化主题
themeStore.initTheme()

const isCollapsed = ref(false)
// 让 Tooltip 在右侧空间不足时自动翻转到左侧，避免被裁切
const tooltipPopperOptions = {
  placement: 'right',
  modifiers: [
    { name: 'offset', options: { offset: [0, 6] } },
    { name: 'preventOverflow', options: { boundary: 'viewport', padding: 8 } },
    { name: 'flip', options: { fallbackPlacements: ['left'] } },
  ],
}
const tooltipEffect = computed(() => (themeStore.currentTheme === 'dark' ? 'light' : 'dark'))

const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const passwordRules: FormRules = {
  current_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleCommand = (command: string) => {
  switch (command) {
    case 'password':
      passwordDialogVisible.value = true
      break
    case 'logout':
      handleLogout()
      break
  }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  } catch {
    // 用户取消
  }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  
  try {
    await passwordFormRef.value.validate()
    passwordLoading.value = true
    
    const success = await userStore.changePassword({
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password
    })
    
    if (success) {
      ElMessage.success('密码修改成功，请重新登录')
      passwordDialogVisible.value = false
      userStore.logout()
      router.push('/login')
    } else {
      ElMessage.error('密码修改失败')
    }
  } catch (error) {
    console.error('修改密码失败:', error)
  } finally {
    passwordLoading.value = false
  }
}

const handleClosePasswordDialog = () => {
  passwordFormRef.value?.resetFields()
  Object.assign(passwordForm, {
    current_password: '',
    new_password: '',
    confirm_password: ''
  })
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  transition: width 500ms ease-in-out, background-color var(--theme-transition), border-color var(--theme-transition);
  display: flex;
  flex-direction: column;
  position: relative;
  will-change: width;
}

.sidebar.collapsed {
  overflow: visible;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 0 20px;
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  transition: padding 300ms ease-in-out, gap 300ms ease-in-out, background-color var(--theme-transition), border-color var(--theme-transition);
}

.logo.collapsed {
  gap: 0;
}

.logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: transparent;
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.logo-title {
  color: var(--el-color-primary);
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  transition: opacity 260ms ease-in-out, max-width 260ms ease-in-out, transform 260ms ease-in-out;
  white-space: nowrap;
  overflow: hidden;
  max-width: 160px;
}

.sidebar.collapsed .logo-title {
  opacity: 0;
  max-width: 0;
  transform: translateX(-6px);
}

.sidebar-menu {
  border: none;
  background-color: var(--el-bg-color);
  padding: 12px;
  transition: padding 300ms ease-in-out, background-color var(--theme-transition);
  flex: 1;
  overflow-y: auto;
  will-change: padding;
}

.sidebar.collapsed .sidebar-menu {
  padding: 8px 6px;
}

.sidebar.collapsed :deep(.el-menu-item),
.sidebar.collapsed :deep(.el-sub-menu__title) {
  padding-left: 0 !important;
  padding-right: 0 !important;
  justify-content: center;
  transition: padding 220ms ease-in-out, justify-content 220ms ease-in-out;
}

.sidebar.collapsed :deep(.el-menu-item .el-icon),
.sidebar.collapsed :deep(.el-sub-menu__title .el-icon) {
  margin: 0 !important;
  transition: margin 220ms ease-in-out;
}

.menu-item-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-menu-item) {
  color: var(--el-text-color-regular);
  margin: 4px 0;
  border-radius: 8px;
  transition: var(--theme-transition);
}

:deep(.el-menu-item:hover) {
  background-color: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

:deep(.el-menu-item.is-active) {
  background-color: var(--el-color-primary);
  color: var(--el-color-white);
  font-weight: 600;
}

.sidebar.collapsed :deep(.el-menu-item span),
.sidebar.collapsed :deep(.el-sub-menu__title span) {
  display: none;
}

:deep(.el-sub-menu) {
  margin: 4px 0;
}

:deep(.el-sub-menu__title) {
  color: var(--el-text-color-regular);
  border-radius: 8px;
  transition: var(--theme-transition);
}

:deep(.el-sub-menu__title:hover) {
  background-color: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

:deep(.el-sub-menu .el-menu-item) {
  margin: 2px 8px;
  padding-left: 40px;
}

.header {
  height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  box-shadow: var(--el-box-shadow-light);
  transition: var(--theme-transition);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid var(--el-border-color);
  cursor: pointer;
  transition: var(--theme-transition);
  color: var(--el-text-color-primary);
}

.theme-toggle:hover {
  background-color: var(--el-fill-color-light);
  border-color: var(--el-color-primary);
}

.collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid var(--el-border-color);
  cursor: pointer;
  transition: background-color var(--theme-transition), border-color var(--theme-transition), transform 200ms ease-in-out;
  color: var(--el-text-color-primary);
}

.collapse-toggle:hover {
  background-color: var(--el-fill-color-light);
  border-color: var(--el-color-primary);
}

.sidebar-footer {
  padding: 12px;
  display: flex;
  justify-content: flex-end;
}

.sidebar.collapsed .sidebar-footer {
  justify-content: center;
}

.el-dropdown-link {
  cursor: pointer;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  transition: var(--theme-transition);
}

.el-dropdown-link:hover {
  background-color: var(--el-fill-color-light);
}

.username {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.main-content {
  background-color: var(--el-bg-color-page);
  padding: 20px;
  transition: var(--theme-transition);
}
</style>
