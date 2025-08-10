import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'
import { useThemeStore } from './stores/theme'

// 全局样式
import './styles/main.css'
import './styles/theme.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default',
})

app.mount('#app')

// 应用初始化后恢复用户状态
const userStore = useUserStore()
userStore.restoreFromStorage()

// 初始化主题
const themeStore = useThemeStore()
themeStore.initTheme()
