import { createApp } from 'vue'
import router from './router'
import './style.css'
import App from './App.vue'
import { getPortalProjectId } from './utils/portal'
import 'highlight.js/styles/github-dark.css'

// 启动时读取 UniPortal 工程 ID（写入 sessionStorage）
getPortalProjectId()

const app = createApp(App)
app.use(router)
app.mount('#app')
