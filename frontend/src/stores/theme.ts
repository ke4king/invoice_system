import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref<ThemeMode>('light')

  // 初始化主题
  const initTheme = () => {
    const savedTheme = localStorage.getItem('theme') as ThemeMode
    if (savedTheme && ['light', 'dark'].includes(savedTheme)) {
      currentTheme.value = savedTheme
    }
    applyTheme(currentTheme.value)
  }

  // 应用主题
  const applyTheme = (theme: ThemeMode) => {
    const html = document.documentElement
    
    if (theme === 'dark') {
      // Element Plus 暗黑模式需要在 html 元素上添加 dark 类
      html.classList.add('dark')
      html.setAttribute('data-theme', 'dark')
    } else {
      html.classList.remove('dark')
      html.setAttribute('data-theme', 'light')
    }
    
    // 强制重新渲染，确保 CSS 变量更新
    html.style.display = 'none'
    html.offsetHeight // 触发重排
    html.style.display = ''
  }

  // 切换主题
  const toggleTheme = () => {
    currentTheme.value = currentTheme.value === 'light' ? 'dark' : 'light'
  }

  // 设置主题
  const setTheme = (theme: ThemeMode) => {
    currentTheme.value = theme
  }

  // 监听主题变化
  watch(currentTheme, (newTheme) => {
    applyTheme(newTheme)
    localStorage.setItem('theme', newTheme)
  })

  return {
    currentTheme,
    initTheme,
    toggleTheme,
    setTheme
  }
})