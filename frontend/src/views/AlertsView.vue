<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api, startPolling } from '../api/client'

const rows = ref([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
let stop = null

async function load() {
  if (!loading.value) refreshing.value = true
  try {
    rows.value = await api.get('/alerts')
    error.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(() => { stop = startPolling(load, 15000) })
onUnmounted(() => stop && stop())
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div><h1>告警中心</h1><p>连接异常、字段缺失、证书过期等告警</p></div>
      <div style="display:flex;align-items:center;gap:.75rem;">
        <span v-if="refreshing" class="loading-inline"><span class="spinner"></span>刷新中</span>
        <button class="primary" @click="load">刷新</button>
      </div>
    </header>
    <p v-if="error" class="error" style="margin-bottom:.75rem;font-size:.82rem;">{{ error }}</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>时间</th><th>级别</th><th>类型</th><th>车辆</th><th>消息</th></tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 5" :key="'sk'+n"><td colspan="5" style="padding:0;">
              <div class="skeleton-row"><div class="skeleton-cell"></div><div class="skeleton-cell"></div><div class="skeleton-cell"></div></div>
            </td></tr>
          </template>
          <tr v-else-if="rows.length === 0"><td colspan="5" class="empty"><span class="empty-icon">🔔</span>暂无告警</td></tr>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ $fmtTime(r.created_at) }}</td>
            <td><span :class="r.level === 'critical' ? 'badge badge-danger' : 'badge badge-warn'">{{ r.level }}</span></td>
            <td>{{ r.alert_type }}</td>
            <td>{{ r.vehicle_id || '-' }}</td>
            <td>{{ r.message }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
