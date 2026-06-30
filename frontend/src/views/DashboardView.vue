<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const stats = ref({ vehicles: 0, online: 0, reporting: 0, alerts: 0 })
const vendors = ref([])
const platforms = ref([])
const loading = ref(true)

// 在线判定：最近 2 分钟内有上报视为在线
const ONLINE_WINDOW_MS = 2 * 60 * 1000

function parseUtc(iso) {
  if (!iso) return 0
  const s = String(iso)
  const n = s.includes('T') ? s : s.replace(' ', 'T')
  const u = n.includes('Z') || n.includes('+') ? n : n + 'Z'
  const t = new Date(u).getTime()
  return isNaN(t) ? 0 : t
}

onMounted(async () => {
  const [v, p, a, vehicles, states] = await Promise.all([
    api.get('/vendors').catch(() => []),
    api.get('/regulatory-platforms').catch(() => []),
    api.get('/alerts').catch(() => ({ total: 0 })),
    api.get('/vehicles').catch(() => []),
    api.get('/states/latest').catch(() => []),
  ])
  vendors.value = v
  platforms.value = p

  const now = Date.now()
  const onlineCount = (states || []).filter(s => now - parseUtc(s.received_at) < ONLINE_WINDOW_MS).length

  stats.value = {
    vehicles: Array.isArray(vehicles) ? vehicles.length : 0,
    online: onlineCount,
    reporting: 0,
    alerts: a.total || a.length || 0,
  }
  try {
    const r = await api.get('/reports/connections')
    stats.value.reporting = (r || []).filter(c => c.status === 'connected' || c.status === 'ok').length
  } catch {}
  loading.value = false
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
        <div class="stat-value">{{ loading ? '—' : stats.vehicles }}</div>
        <div class="stat-label">车辆总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ loading ? '—' : stats.online }}</div>
        <div class="stat-label">在线车辆（近2分钟）</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ loading ? '—' : stats.reporting }}</div>
        <div class="stat-label">上报中连接</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ loading ? '—' : stats.alerts }}</div>
        <div class="stat-label">活跃告警</div>
      </div>
    </div>

    <div class="table-wrap">
      <table>
        <thead><tr><th>厂商</th><th>类型</th><th>环境</th><th>启用</th></tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 3" :key="'sk'+n"><td colspan="4" style="padding:0;">
              <div class="skeleton-row"><div class="skeleton-cell"></div><div class="skeleton-cell"></div></div>
            </td></tr>
          </template>
          <tr v-else-if="vendors.length === 0"><td colspan="4" class="empty"><span class="empty-icon">🔌</span>暂无厂商</td></tr>
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
