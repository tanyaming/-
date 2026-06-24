<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const message = ref('')
const editingId = ref(null)
const form = reactive({
  name: '',
  vendor_type: 'neolix',
  environment: 'test',
  base_url: 'https://scapi.test.neolix.net',
  config: '{\n  "client_id": "",\n  "x_from": "88e01d37NvKINh0LRm0NSivW",\n  "x_version": "0.1.0"\n}',
  secret_config: '{\n  "client_secret": ""\n}',
  is_enabled: true,
})

function resetForm() {
  editingId.value = null
  form.name = ''
  form.vendor_type = 'neolix'
  form.environment = 'test'
  form.base_url = 'https://scapi.test.neolix.net'
  form.config = '{\n  "client_id": "",\n  "x_from": "88e01d37NvKINh0LRm0NSivW",\n  "x_version": "0.1.0"\n}'
  form.secret_config = '{\n  "client_secret": ""\n}'
  form.is_enabled = true
}

async function load() {
  rows.value = await api.get('/vendors')
}

async function saveVendor() {
  message.value = ''
  try {
    const payload = {
      name: form.name,
      vendor_type: form.vendor_type,
      environment: form.environment,
      base_url: form.base_url || null,
      config: JSON.parse(form.config || '{}'),
      secret_config: JSON.parse(form.secret_config || '{}'),
      is_enabled: form.is_enabled,
    }
    if (editingId.value) {
      await api.put(`/vendors/${editingId.value}`, payload)
      message.value = '厂商已更新'
    } else {
      await api.post('/vendors', payload)
      message.value = '厂商已保存'
    }
    editingId.value = null
    resetForm()
    await load()
  } catch (e) {
    message.value = `保存失败: ${e.message}`
  }
}

function startEdit(item) {
  editingId.value = item.id
  form.name = item.name
  form.vendor_type = item.vendor_type
  form.environment = item.environment
  form.base_url = item.base_url || ''
  form.config = JSON.stringify(item.config || {}, null, 2)
  form.secret_config = JSON.stringify(item.secret_config || {}, null, 2)
  form.is_enabled = item.is_enabled
}

async function removeVendor(id) {
  if (!confirm('确定删除该厂商账号？关联的厂商绑定也会被删除。')) return
  message.value = ''
  try {
    await api.delete(`/vendors/${id}`)
    message.value = '厂商已删除'
    await load()
  } catch (e) {
    message.value = `删除失败: ${e.message}`
  }
}

async function testConnection(id) {
  message.value = '测试中...'
  try {
    const result = await api.post(`/vendors/${id}/test-connection`, {})
    message.value = `测试结果: ${result.status} - ${result.message || ''}`
  } catch (e) {
    message.value = `测试失败: ${e.message}`
  }
}

async function syncVehicles(id) {
  message.value = '同步中...'
  try {
    const result = await api.post(`/vendors/${id}/sync-vehicles`, {})
    message.value = `同步完成: 发现 ${result.count} 辆车 (新建 ${result.created}, 已有 ${result.updated})`
  } catch (e) {
    message.value = `同步失败: ${e.message}`
  }
}

function onTypeChange() {
  if (form.vendor_type === 'jiushi') {
    form.config = '{\n  "organization_code": "",\n  "mqtt_host": "127.0.0.1",\n  "mqtt_port": 1883\n}'
    form.secret_config = '{\n  "mqtt_username": "hub_client",\n  "mqtt_password": "hub_password",\n  "app_id": "",\n  "app_key": ""\n}'
    form.base_url = ''
  } else {
    form.config = '{\n  "client_id": "",\n  "x_from": "88e01d37NvKINh0LRm0NSivW",\n  "x_version": "0.1.0"\n}'
    form.secret_config = '{\n  "client_secret": ""\n}'
    form.base_url = 'https://scapi.test.neolix.net'
  }
  editingId.value = null
}

onMounted(load)
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>厂商接入</h1>
        <p>新石器 → 获取 API 账号接入 HTTP 拉取。九识 → 搭建 MQTT Broker，九识向你的 Broker 推送数据。</p>
      </div>
      <button class="primary" @click="load">刷新</button>
    </header>

    <p v-if="message" :class="message.includes('失败') ? 'error' : ''" style="margin-bottom:0.5rem;font-size:.85rem;">{{ message }}</p>

    <form class="form-grid" @submit.prevent="saveVendor">
      <label>名称<input v-model="form.name" required /></label>
      <label>类型
        <select v-model="form.vendor_type" @change="onTypeChange">
          <option value="neolix">新石器</option>
          <option value="jiushi">九识</option>
        </select>
      </label>
      <label>环境
        <select v-model="form.environment">
          <option value="test">测试</option>
          <option value="production">生产</option>
        </select>
      </label>
      <label v-if="form.vendor_type === 'neolix'">API 地址<input v-model="form.base_url" /></label>
      <div v-else></div>
      <label class="span-2">
        公开配置（JSON）
        <textarea v-model="form.config" rows="6"></textarea>
      </label>
      <label class="span-2">
        敏感配置（JSON，密钥将加密存储）
        <textarea v-model="form.secret_config" rows="4"></textarea>
      </label>
      <label>启用<input type="checkbox" v-model="form.is_enabled" style="width:auto;margin-top:.5rem;" /></label>
      <div></div>
      <div style="display:flex;gap:0.5rem;align-items:center;">
        <button class="primary" type="submit">{{ editingId ? '更新厂商' : '保存厂商' }}</button>
        <button v-if="editingId" type="button" @click="resetForm()" style="background:#eee;border:1px solid #d9d9d9;padding:.45rem 1rem;border-radius:6px;cursor:pointer;font-size:.85rem;">取消编辑</button>
      </div>
    </form>

    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>ID</th><th>名称</th><th>类型</th><th>环境</th><th>地址</th><th>启用</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="7" class="empty">暂无厂商账号</td></tr>
          <tr v-for="item in rows" :key="item.id" :class="{ 'editing-row': editingId === item.id }">
            <td>{{ item.id }}</td>
            <td>{{ item.name }}</td>
            <td><span :class="item.vendor_type === 'neolix' ? 'badge badge-info' : 'badge badge-success'">{{ item.vendor_type === 'neolix' ? '新石器' : '九识' }}</span></td>
            <td>{{ item.environment === 'production' ? '生产' : '测试' }}</td>
            <td>{{ item.base_url || '(MQTT)' }}</td>
            <td>{{ item.is_enabled ? '✅' : '❌' }}</td>
            <td>
              <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
                <button @click="startEdit(item)" style="font-size:0.7rem;padding:0.2rem 0.4rem;">编辑</button>
                <button @click="testConnection(item.id)" style="font-size:0.7rem;padding:0.2rem 0.4rem;">测试</button>
                <button @click="syncVehicles(item.id)" style="font-size:0.7rem;padding:0.2rem 0.4rem;">同步</button>
                <button @click="removeVendor(item.id)" class="danger" style="font-size:0.7rem;padding:0.2rem 0.4rem;">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.editing-row { background: #e3f2fd; }
</style>
