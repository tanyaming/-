<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const stats = ref({ vehicles: 0, online: 0, reporting: 0, alerts: 0 })
const vendors = ref([])
const platforms = ref([])

onMounted(async () => {
  const [v, p, a] = await Promise.all([
    api.get('/vendors').catch(() => []),
    api.get('/regulatory-platforms').catch(() => []),
    api.get('/alerts').catch(() => ({ total: 0 })),
  ])
  vendors.value = v
  platforms.value = p
  stats.value = {
    vehicles: 0,
    online: 0,
    reporting: 0,
    alerts: a.total || a.length || 0,
  }
  try {
    const r = await api.get('/reports/connections')
    stats.value.reporting = (r || []).filter(c => c.status === 'connected').length
  } catch {}
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>概览</h1>
        <p>车辆数据接入与监管上报总览</p>
      </div>
    </header>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.vehicles }}</div>
        <div class="stat-label">车辆总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.online }}</div>
        <div class="stat-label">在线车辆</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.reporting }}</div>
        <div class="stat-label">上报中连接</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.alerts }}</div>
        <div class="stat-label">活跃告警</div>
      </div>
    </div>

    <div class="table-wrap">
      <table>
        <thead><tr><th>厂商</th><th>类型</th><th>环境</th><th>启用</th></tr></thead>
        <tbody>
          <tr v-if="vendors.length === 0"><td colspan="4" class="empty">暂无厂商</td></tr>
          <tr v-for="v in vendors" :key="v.id">
            <td>{{ v.name }}</td>
            <td><span :class="v.vendor_type === 'neolix' ? 'badge badge-info' : 'badge badge-success'">{{ v.vendor_type === 'neolix' ? '新石器' : '九识' }}</span></td>
            <td>{{ v.environment }}</td>
            <td>{{ v.is_enabled ? '✅' : '❌' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
