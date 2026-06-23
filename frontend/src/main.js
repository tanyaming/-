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
import MappingsView from './views/MappingsView.vue'

const routes = [
  { path: '/', component: DashboardView, meta: { title: '概览' } },
  { path: '/vendors', component: VendorsView, meta: { title: '厂商接入' } },
  { path: '/platforms', component: PlatformsView, meta: { title: '监管平台' } },
  { path: '/vehicles', component: VehiclesView, meta: { title: '车辆管理' } },
  { path: '/certificates', component: CertificatesView, meta: { title: '证书管理' } },
  { path: '/states', component: StatesView, meta: { title: '实时状态' } },
  { path: '/reports', component: ReportsView, meta: { title: '上报监控' } },
  { path: '/alerts', component: AlertsView, meta: { title: '告警中心' } },
  { path: '/mappings', component: MappingsView, meta: { title: '映射配置' } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
