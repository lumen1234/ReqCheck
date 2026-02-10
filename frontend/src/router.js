import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./pages/Home.vue')
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('./pages/Upload.vue')
  },
  {
    path: '/parse/:docId',
    name: 'Parse',
    component: () => import('./pages/Parse.vue')
  },
  {
    path: '/validate/:docId',
    name: 'Validate',
    component: () => import('./pages/Validate.vue')
  },
  {
    path: '/export/:docId',
    name: 'Export',
    component: () => import('./pages/Export.vue')
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('./pages/History.vue')
  },
  {
    path: '/document/:docId',
    name: 'DocumentDetail',
    component: () => import('./pages/DocumentDetail.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
