import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      name: 'Layout',
      component: () => import('@/layouts/DefaultLayout.vue'),
      redirect: '/dashboard',
      meta: { requiresAuth: true },
      children: [
        {
          path: '/dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '工作台' }
        },
        {
          path: '/invoices',
          name: 'InvoiceList',
          component: () => import('@/views/invoice/InvoiceList.vue'),
          meta: { title: '发票列表' }
        },
        {
          path: '/invoices/upload',
          name: 'InvoiceUpload',
          component: () => import('@/views/invoice/InvoiceUpload.vue'),
          meta: { title: '发票上传' }
        },
        {
          path: '/invoices/:id',
          name: 'InvoiceDetail',
          component: () => import('@/views/invoice/InvoiceDetail.vue'),
          meta: { title: '发票详情' }
        },
        {
          path: '/emails',
          name: 'EmailList',
          component: () => import('@/views/email/EmailList.vue'),
          meta: { title: '邮件列表' }
        },
        {
          path: '/print',
          name: 'BatchPrint',
          component: () => import('@/views/print/BatchPrint.vue'),
          meta: { title: '批量打印' }
        },
        {
          path: '/settings',
          name: 'Settings',
          component: () => import('@/views/settings/Settings.vue'),
          meta: { title: '邮箱配置' }
        },
        {
          path: '/logs',
          name: 'LogList',
          component: () => import('@/views/logs/LogList.vue'),
          meta: { title: '系统日志' }
        },
        {
          path: '/monitoring',
          name: 'Monitoring',
          component: () => import('@/views/logs/Monitoring.vue'),
          meta: { title: '系统监控' }
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue')
    }
  ]
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  // 刷新后确保从本地恢复登录状态
  if (!userStore.isLoggedIn && localStorage.getItem('token')) {
    userStore.restoreFromStorage()
  }
  
  if (to.meta.requiresAuth !== false) {
    if (!userStore.isLoggedIn) {
      next('/login')
      return
    }
  }
  
  if (to.name === 'Login' && userStore.isLoggedIn) {
    next('/')
    return
  }
  
  next()
})

export default router