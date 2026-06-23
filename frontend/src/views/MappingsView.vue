<script setup>
import { ref, onMounted, reactive } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const message = ref('')
const form = reactive({ source_vendor: '', source_field: '', target_field: '', mapping_type: 'field' })

async function load() { rows.value = await api.get('/mappings') }
async function save() {
  try { await api.post('/mappings', { ...form }); message.value = '保存成功'; await load() }
  catch (e) { message.value = `保存失败: ${e.message}` }
}
onMounted(load)
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>映射配置</h1><p>厂商字段到标准字段的映射规则</p></div><button class="primary" @click="load">刷新</button></header>
    <form class="form-grid" @submit.prevent="save">
      <label>厂商<input v-model="form.source_vendor" /></label>
      <label>类型
        <select v-model="form.mapping_type"><option value="field">字段映射</option><option value="enum">枚举映射</option></select>
      </label>
      <label>源字段<input v-model="form.source_field" /></label>
      <label>目标字段<input v-model="form.target_field" /></label>
      <button class="primary" type="submit">保存</button>
      <span class="form-message">{{ message }}</span>
    </form>
    <div class="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>厂商</th><th>类型</th><th>源字段</th><th>目标字段</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="5" class="empty">暂无映射</td></tr>
          <tr v-for="r in rows" :key="r.id"><td>{{ r.id }}</td><td>{{ r.source_vendor }}</td><td>{{ r.mapping_type }}</td><td>{{ r.source_field }}</td><td>{{ r.target_field }}</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
