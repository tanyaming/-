<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api/client'

const rows = ref([])
let timer = null

async function load() { rows.value = await api.get('/alerts') }
onMounted(() => { load(); timer = setInterval(load, 15000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>告警中心</h1><p>连接异常、字段缺失、证书过期等告警</p></div><button class="primary" @click="load">刷新</button></header>
    <div class="table-wrap">
      <table>
        <thead><tr><th>时间</th><th>级别</th><th>类型</th><th>车辆</th><th>消息</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="5" class="empty">暂无告警</td></tr>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.created_at }}</td>
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
