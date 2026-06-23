<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const message = ref('')
const form = reactive({
  name: '',
  vendor_type: 'neolix',
  environment: 'test',
  base_url: 'https://scapi.test.neolix.net',
  config: '{\n  "client_id": "",\n  "x_from": "88e01d37NvKINh0LRm0NSivW",\n  "x_version": "0.1.0"\n}',
  secret_config: '{\n  "client_secret": ""\n}',
  is_enabled: true,
})

async function load() {
  rows.value = await api.get('/vendors')
}

async function createVendor() {
  message.value = ''
  try {
    await api.post('/vendors', {
      ...form,
      config: JSON.parse(form.config || '{}'),
      secret_config: JSON.parse(form.secret_config || '{}'),
    })
    message.value = '厂商账号已保存'
    await load()
  } catch (e) {
    message.value = `保存失败: ${e.message}`
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

function onTypeChange() {
  if (form.vendor_type === 'jiushi') {
    form.config = '{\n  "organization_code": "",\n  "mqtt_host": "127.0.0.1",\n  "mqtt_port": 1883\n}'
    form.secret_config = '{\n  "mqtt_username": "jiushi_user",\n  "mqtt_password": ""\n}'
    form.base_url = ''
  } else {
    form.config = '{\n  "client_id": "",\n  "x_from": "88e01d37NvKINh0LRm0NSivW",\n  "x_version": "0.1.0"\n}'
    form.secret_config = '{\n  "client_secret": ""\n}'
    form.base_url = 'https://scapi.test.neolix.net'
  }
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

    <form class="form-grid" @submit.prevent="createVendor">
      <label>名称<input v-model="form.name" required /></label>
      <label>类型
        <select v-model="form.vendor_type" @change="onTypeChange">
          <option value="neolix">新石器</option>
          <option value="jiushi">九识</option>
        </select>
      </label>
      <label>环境<input v-model="form.environment" /></label>
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
      <button class="primary" type="submit">保存厂商</button>
      <span class="form-message">{{ message }}</span>
    </form>

    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>ID</th><th>名称</th><th>类型</th><th>环境</th><th>地址</th><th>启用</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="7" class="empty">暂无厂商账号</td></tr>
          <tr v-for="item in rows" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.name }}</td>
            <td><span :class="item.vendor_type === 'neolix' ? 'badge badge-info' : 'badge badge-success'">{{ item.vendor_type === 'neolix' ? '新石器' : '九识' }}</span></td>
            <td>{{ item.environment }}</td>
            <td>{{ item.base_url || '(MQTT)' }}</td>
            <td>{{ item.is_enabled ? '✅' : '❌' }}</td>
            <td><button @click="testConnection(item.id)" style="font-size:0.75rem;padding:0.25rem 0.5rem">测试连接</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
