<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api/client'

const rows = ref([])
let timer = null

async function load() { rows.value = await api.get('/states/latest') }
onMounted(() => { load(); timer = setInterval(load, 10000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>实时状态</h1><p>车辆最新位置与运行状态（10秒自动刷新）</p></div></header>
    <div class="table-wrap">
      <table>
        <thead><tr><th>车辆ID</th><th>经度</th><th>纬度</th><th>速度(m/s)</th><th>电量</th><th>模式</th><th>更新时间</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="7" class="empty">暂无实时数据，等待调度引擎拉取厂商数据...</td></tr>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.vehicle_id }}</td>
            <td>{{ r.longitude?.toFixed(6) }}</td>
            <td>{{ r.latitude?.toFixed(6) }}</td>
            <td>{{ r.speed_mps?.toFixed(2) || '-' }}</td>
            <td>{{ r.battery_soc != null ? r.battery_soc + '%' : '-' }}</td>
            <td>{{ r.drive_mode || '-' }}</td>
            <td>{{ r.received_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
