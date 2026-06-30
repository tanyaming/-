import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'

// 路由懒加载：各页面按需加载，减小首屏 JS，加快首次渲染
const routes = [
  { path: '/', component: () => import('./views/DashboardView.vue'), meta: { title: '概览' } },
  { path: '/vendors', component: () => import('./views/VendorsView.vue'), meta: { title: '厂商接入' } },
  { path: '/platforms', component: () => import('./views/PlatformsView.vue'), meta: { title: '监管平台' } },
  { path: '/vehicles', component: () => import('./views/VehiclesView.vue'), meta: { title: '车辆管理' } },
  { path: '/certificates', component: () => import('./views/CertificatesView.vue'), meta: { title: '证书管理' } },
  { path: '/states', component: () => import('./views/StatesView.vue'), meta: { title: '实时状态' } },
  { path: '/reports', component: () => import('./views/ReportsView.vue'), meta: { title: '上报监控' } },
  { path: '/alerts', component: () => import('./views/AlertsView.vue'), meta: { title: '告警中心' } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

const app = createApp(App)
app.use(router)

// 全局时间格式化函数（后端存储 UTC 时间，前端转为本地时区显示）
app.config.globalProperties.$fmtTime = (iso) => {
  if (!iso) return '-'
  // 后端返回的 naive datetime 实际是 UTC 时间，补上 Z 后缀让 JS 正确解析
  const str = String(iso)
  const normalized = str.includes('T') ? str : str.replace(' ', 'T')
  const utcStr = normalized.includes('Z') || normalized.includes('+') || normalized.includes('[') ? normalized : normalized + 'Z'
  const d = new Date(utcStr)
  if (isNaN(d.getTime())) return iso
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}/${pad(d.getMonth()+1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

app.mount('#app')
