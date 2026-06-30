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
    rows.value = await api.get('/reports/connections')
    error.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(() => { stop = startPolling(load, 10000) })
onUnmounted(() => stop && stop())
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div><h1>上报监控</h1><p>各连接状态（厂商/监管/车辆上报），10秒自动刷新</p></div>
      <div style="display:flex;align-items:center;gap:.75rem;">
        <span v-if="refreshing" class="loading-inline"><span class="spinner"></span>刷新中</span>
        <button class="primary" @click="load">刷新</button>
      </div>
    </header>
    <p v-if="error" class="error" style="margin-bottom:.75rem;font-size:.82rem;">{{ error }}</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>类型</th><th>关联ID</th><th>状态</th><th>最后活跃</th><th>错误信息</th></tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 5" :key="'sk'+n"><td colspan="5" style="padding:0;">
              <div class="skeleton-row"><div class="skeleton-cell"></div><div class="skeleton-cell"></div><div class="skeleton-cell"></div></div>
            </td></tr>
          </template>
          <tr v-else-if="rows.length === 0"><td colspan="5" class="empty"><span class="empty-icon">📈</span>暂无连接信息，等待调度引擎启动…</td></tr>
          <tr v-for="r in rows" :key="r.id">
            <td>
              <span :class="r.kind === 'vehicle_reporter' ? 'badge badge-info' : r.kind === 'vendor' ? 'badge badge-success' : 'badge badge-warn'">
                {{ r.kind === 'vehicle_reporter' ? '监管上报' : r.kind === 'vendor' ? '厂商连接' : '监管平台' }}
              </span>
            </td>
            <td>{{ r.ref_id }}</td>
            <td><span :class="r.status === 'ok' ? 'badge badge-success' : 'badge badge-danger'">{{ r.status }}</span></td>
            <td>{{ $fmtTime(r.last_seen_at) }}</td>
            <td>{{ r.last_error || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
