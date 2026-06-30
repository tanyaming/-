<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api, startPolling } from '../api/client'

const rows = ref([])
const loading = ref(true)      // 首次加载
const refreshing = ref(false)  // 轮询刷新
const error = ref('')
let stop = null

async function load() {
  if (!loading.value) refreshing.value = true
  try {
    rows.value = await api.get('/states/latest')
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
      <div><h1>实时状态</h1><p>车辆最新位置与运行状态（10秒自动刷新）</p></div>
      <span v-if="refreshing" class="loading-inline"><span class="spinner"></span>刷新中</span>
    </header>
    <p v-if="error" class="error" style="margin-bottom:.75rem;font-size:.82rem;">{{ error }}</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>车辆</th><th>车牌</th><th>位置</th><th>经纬度</th><th>速度(m/s)</th><th>电量</th><th>档位</th><th>更新时间</th></tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="'sk'+n"><td colspan="8" style="padding:0;">
              <div class="skeleton-row"><div class="skeleton-cell"></div><div class="skeleton-cell"></div><div class="skeleton-cell"></div><div class="skeleton-cell"></div></div>
            </td></tr>
          </template>
          <tr v-else-if="rows.length === 0"><td colspan="8" class="empty"><span class="empty-icon">📡</span>暂无实时数据，等待调度引擎拉取厂商数据…</td></tr>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.vehicle_name || '车辆' + r.vehicle_id }}</td>
            <td>{{ r.vehicle_plate_no || '-' }}</td>
            <td class="addr-cell" :title="r.address?.formatted_address">
              <template v-if="r.address?.formatted_address">{{ r.address.formatted_address }}</template>
              <template v-else-if="r.address?.address">{{ r.address.address }}</template>
              <template v-else-if="r.longitude">解析中…</template>
              <template v-else>-</template>
            </td>
            <td class="coord-cell">
              <span v-if="r.longitude">{{ r.longitude.toFixed(6) }}, {{ r.latitude.toFixed(6) }}</span>
              <span v-else>-</span>
            </td>
            <td>{{ r.speed_mps?.toFixed(2) || '-' }}</td>
            <td>{{ r.battery_soc != null ? r.battery_soc + '%' : '-' }}</td>
            <td>{{ r.gear_label || r.gear || '-' }}</td>
            <td>{{ $fmtTime(r.received_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.addr-cell {
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.875rem;
  color: var(--text-secondary, #666);
}
.coord-cell {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 0.8rem;
}
</style>
