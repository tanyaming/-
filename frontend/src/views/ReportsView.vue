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
    <header class="page-header"><div><h1>上报监控</h1><p>各连接状态（厂商/监管/车辆上报），10秒自动刷新</p></div><button class="primary" @click="load">刷新</button></header>
    <div class="table-wrap">
      <table>
        <thead><tr><th>类型</th><th>关联ID</th><th>状态</th><th>最后活跃</th><th>错误信息</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="5" class="empty">暂无连接信息，等待调度引擎启动...</td></tr>
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
