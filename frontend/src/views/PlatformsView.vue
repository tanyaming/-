<script setup>
import { ref, onMounted, reactive } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const message = ref('')
const loading = ref(true)
const form = reactive({
  name: '', city: '成都', host: '171.221.218.40', port: 38090, coordinate_system: 'WGS84', report_frequency_hz: 10, is_enabled: true,
})

async function load() {
  try {
    rows.value = await api.get('/regulatory-platforms')
  } finally {
    loading.value = false
  }
}
async function save() {
  message.value = ''
  try {
    await api.post('/regulatory-platforms', { ...form })
    message.value = '保存成功'
    await load()
  } catch (e) { message.value = `保存失败: ${e.message}` }
}
onMounted(load)
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>监管平台</h1><p>城市监管平台连接配置</p></div><button class="primary" @click="load">刷新</button></header>
    <form class="form-grid" @submit.prevent="save">
      <label>名称<input v-model="form.name" required /></label>
      <label>城市<input v-model="form.city" /></label>
      <label>地址<input v-model="form.host" /></label>
      <label>端口<input v-model.number="form.port" type="number" /></label>
      <label>坐标系<input v-model="form.coordinate_system" /></label>
      <label>上报频率(Hz)<input v-model.number="form.report_frequency_hz" type="number" /></label>
      <button class="primary" type="submit">保存</button>
      <span class="form-message">{{ message }}</span>
    </form>
    <div class="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>名称</th><th>城市</th><th>地址</th><th>端口</th><th>坐标系</th><th>频率</th><th>启用</th></tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 2" :key="'sk'+n"><td colspan="8" style="padding:0;">
              <div class="skeleton-row"><div class="skeleton-cell"></div><div class="skeleton-cell"></div><div class="skeleton-cell"></div></div>
            </td></tr>
          </template>
          <tr v-else-if="rows.length === 0"><td colspan="8" class="empty"><span class="empty-icon">🏛️</span>暂无监管平台</td></tr>
          <tr v-for="r in rows" :key="r.id"><td>{{ r.id }}</td><td>{{ r.name }}</td><td>{{ r.city }}</td><td>{{ r.host }}</td><td>{{ r.port }}</td><td>{{ r.coordinate_system }}</td><td>{{ r.report_frequency_hz }}Hz</td><td>{{ r.is_enabled ? '✅' : '❌' }}</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
