import { createRouter, createWebHashHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import ParseView from '../views/ParseView.vue'
import ValidateView from '../views/ValidateView.vue'
import ReportView from '../views/ReportView.vue'

const routes = [
  {
    path: '/',
    name: 'upload',
    component: UploadView,
    meta: { title: '文档上传' }
  },
  {
    path: '/documents/:documentId/parse',
    name: 'parse',
    component: ParseView,
    meta: { title: '文档分析' },
    beforeEnter: (to, from, next) => {
      if (!to.params.documentId) {
        next('/')
      } else {
        next()
      }
    }
  },
  {
    path: '/documents/:documentId/validate',
    name: 'validate',
    component: ValidateView,
    meta: { title: '需求验证' },
    beforeEnter: (to, from, next) => {
      if (!to.params.documentId) {
        next('/')
      } else {
        next()
      }
    }
  },
  {
    path: '/documents/:documentId/report',
    name: 'report',
    component: ReportView,
    meta: { title: '文档导出' },
    beforeEnter: (to, from, next) => {
      if (!to.params.documentId) {
        next('/')
      } else {
        next()
      }
    }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})    
// 全局路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {  
  document.title = to.meta.title ? `${to.meta.title} - 文档审查系统` : '文档审查系统'
  next()
})

export default router
