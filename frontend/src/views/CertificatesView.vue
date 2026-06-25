<script setup>
import { ref, onMounted, reactive } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const message = ref('')
const certInput = ref(null)
const keyInput = ref(null)
const caInput = ref(null)
const vehicles = ref([])

const form = reactive({
  name: '',
  vehicle_id: null,
})

async function load() {
  const [certs, vList] = await Promise.all([
    api.get('/certificates'),
    api.get('/vehicles').catch(() => []),
  ])
  rows.value = certs
  vehicles.value = vList
}

async function removeCert(cert) {
  if (!confirm(`确定要删除证书 "${cert.name}" (ID:${cert.id}) 吗？此操作不可恢复。`)) return
  message.value = ''
  try {
    await api.delete(`/certificates/${cert.id}`)
    message.value = '删除成功'
    await load()
  } catch (e) {
    message.value = `删除失败: ${e.message}`
  }
}
async function upload() {
  const certFile = certInput.value?.files?.[0]
  if (!certFile) { message.value = '请选择证书文件'; return }
  const formData = new FormData()
  formData.append('name', form.name || certFile.name)
  formData.append('certificate', certFile)
  if (form.vehicle_id) formData.append('vehicle_id', form.vehicle_id)
  const keyFile = keyInput.value?.files?.[0]
  if (keyFile) formData.append('private_key', keyFile)
  const caFile = caInput.value?.files?.[0]
  if (caFile) formData.append('ca_certificate', caFile)
  const token = localStorage.getItem('token')
  const res = await fetch('/api/certificates/upload', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData })
  const data = await res.json()
  message.value = res.ok ? '上传成功' : (data.detail || '上传失败')
  if (res.ok) {
    form.name = ''
    form.vehicle_id = null
    certInput.value.value = ''
    keyInput.value.value = ''
    caInput.value.value = ''
  }
  await load()
}
onMounted(load)
</script>

<template>
  <section class="page">
    <header class="page-header"><div><h1>证书管理</h1><p>上传车辆 TLS 证书和私钥</p></div><button class="primary" @click="load">刷新</button></header>
    <div style="background:#fff;padding:1.5rem;border-radius:10px;margin-bottom:1.5rem;">
      <div class="form-grid" style="margin-bottom:1rem;">
        <label>证书名称 *<input v-model="form.name" placeholder="例如：第一辆测试车 TLS 证书" required /></label>
        <label>绑定车辆
          <select v-model="form.vehicle_id">
            <option :value="null">不绑定</option>
            <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.name }} (ID: {{ v.id }})</option>
          </select>
        </label>
        <label>证书文件 (.pem) *<input ref="certInput" type="file" accept=".pem,.crt,.cert" /></label>
        <label>私钥文件 (.key)<input ref="keyInput" type="file" accept=".key" /></label>
        <label>CA 证书 (.pem)<input ref="caInput" type="file" accept=".pem,.crt" /></label>
      </div>
      <div style="display:flex;gap:1rem;align-items:center;">
        <button class="primary" @click="upload">上传证书</button>
        <span v-if="message" :style="{fontSize:'.85rem',color:message.includes('失败')?'#e53935':'#2e7d32'}">{{ message }}</span>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>名称</th><th>证书路径</th><th>绑定车辆</th><th>指纹</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="7" class="empty">暂无证书</td></tr>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.name }}</td>
            <td style="font-size:.75rem;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="r.certificate_path">{{ r.certificate_path }}</td>
            <td>{{ r.vehicle_id ? '车辆' + r.vehicle_id : '-' }}</td>
            <td style="font-size:.7rem;font-family:monospace;max-width:120px;overflow:hidden;text-overflow:ellipsis;" :title="r.fingerprint">{{ r.fingerprint?.slice(0, 12) || '-' }}</td>
            <td>{{ r.is_enabled ? '✅' : '❌' }}</td>
            <td>
              <button @click="removeCert(r)" style="font-size:0.7rem;padding:0.2rem 0.5rem;background:#fff;border:1px solid #e53935;color:#e53935;border-radius:4px;cursor:pointer;">移除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
