<script setup>
import { ref, onMounted, reactive } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const message = ref('')
const form = reactive({ vin: '', vendor_vehicle_id: '', plate_number: '', vehicle_type: '', is_enabled: true })

async function load() { rows.value = await api.get('/vehicles') }
async function save() {
  message.value = ''
  try { await api.post('/vehicles', { ...form }); message.value = '保存成功'; await load() }
  catch (e) { message.value = `保存失败: ${e.message}` }
}
onMounted(load)
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>车辆管理</h1><p>维护中台车辆档案与厂商/监管绑定</p></div><button class="primary" @click="load">刷新</button></header>
    <form class="form-grid" @submit.prevent="save">
      <label>VIN<input v-model="form.vin" /></label>
      <label>厂商车辆ID<input v-model="form.vendor_vehicle_id" /></label>
      <label>车牌<input v-model="form.plate_number" /></label>
      <label>车辆类型<input v-model="form.vehicle_type" /></label>
      <button class="primary" type="submit">保存</button>
      <span class="form-message">{{ message }}</span>
    </form>
    <div class="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>VIN</th><th>厂商车辆ID</th><th>车牌</th><th>类型</th><th>启用</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="6" class="empty">暂无车辆</td></tr>
          <tr v-for="r in rows" :key="r.id"><td>{{ r.id }}</td><td>{{ r.vin }}</td><td>{{ r.vendor_vehicle_id }}</td><td>{{ r.plate_number }}</td><td>{{ r.vehicle_type }}</td><td>{{ r.is_enabled ? '✅' : '❌' }}</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
