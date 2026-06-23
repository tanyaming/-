<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api/client'

const rows = ref([])
let timer = null

async function load() { rows.value = await api.get('/reports/connections') }
onMounted(() => { load(); timer = setInterval(load, 10000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>上报监控</h1><p>每车 TCP/TLS 连接与上报状态（10秒自动刷新）</p></div><button class="primary" @click="load">刷新</button></header>
    <div class="table-wrap">
      <table>
        <thead><tr><th>车辆</th><th>连接状态</th><th>最近上报</th><th>成功/失败</th><th>重连次数</th><th>错误信息</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="6" class="empty">暂无连接信息</td></tr>
          <tr v-for="r in rows" :key="r.vehicle_id">
            <td>{{ r.vehicle_id }}</td>
            <td><span :class="r.status === 'connected' ? 'badge badge-success' : 'badge badge-danger'">{{ r.status }}</span></td>
            <td>{{ r.last_report_at || '-' }}</td>
            <td>{{ r.success_count || 0 }} / {{ r.fail_count || 0 }}</td>
            <td>{{ r.reconnect_count || 0 }}</td>
            <td>{{ r.last_error || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
