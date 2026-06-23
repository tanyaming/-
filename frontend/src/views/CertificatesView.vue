<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const fileInput = ref(null)
const message = ref('')

async function load() { rows.value = await api.get('/certificates') }
async function upload() {
  const file = fileInput.value?.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  const token = localStorage.getItem('token')
  const res = await fetch('/certificates/upload', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData })
  const data = await res.json()
  message.value = res.ok ? '上传成功' : (data.detail || '上传失败')
  await load()
}
onMounted(load)
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>证书管理</h1><p>上传车辆 TLS 证书和私钥</p></div><button class="primary" @click="load">刷新</button></header>
    <div style="background:#fff;padding:1.5rem;border-radius:10px;margin-bottom:1.5rem;display:flex;gap:1rem;align-items:center;">
      <input ref="fileInput" type="file" />
      <button class="primary" @click="upload">上传证书</button>
      <span style="font-size:.8rem;">{{ message }}</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>文件名</th><th>类型</th><th>绑定车辆</th><th>到期时间</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="5" class="empty">暂无证书</td></tr>
          <tr v-for="r in rows" :key="r.id"><td>{{ r.id }}</td><td>{{ r.filename }}</td><td>{{ r.cert_type }}</td><td>{{ r.vehicle_id || '-' }}</td><td>{{ r.expires_at || '-' }}</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
