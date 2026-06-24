import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import DashboardView from './views/DashboardView.vue'
import VendorsView from './views/VendorsView.vue'
import PlatformsView from './views/PlatformsView.vue'
import VehiclesView from './views/VehiclesView.vue'
import CertificatesView from './views/CertificatesView.vue'
import StatesView from './views/StatesView.vue'
import ReportsView from './views/ReportsView.vue'
import AlertsView from './views/AlertsView.vue'

const routes = [
  { path: '/', component: DashboardView, meta: { title: '概览' } },
  { path: '/vendors', component: VendorsView, meta: { title: '厂商接入' } },
  { path: '/platforms', component: PlatformsView, meta: { title: '监管平台' } },
  { path: '/vehicles', component: VehiclesView, meta: { title: '车辆管理' } },
  { path: '/certificates', component: CertificatesView, meta: { title: '证书管理' } },
  { path: '/states', component: StatesView, meta: { title: '实时状态' } },
  { path: '/reports', component: ReportsView, meta: { title: '上报监控' } },
  { path: '/alerts', component: AlertsView, meta: { title: '告警中心' } },
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
