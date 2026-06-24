<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { api } from '../api/client'

const rows = ref([])
const vendors = ref([])
const platforms = ref([])
const message = ref('')
const showCreate = ref(false)
const showBindVendor = ref(null)
const showBindRegulatory = ref(null)
const editing = ref(null)

const form = reactive({ name: '', vin: '', plate_no: '', model: '', brand: '', vehicle_category: '', power_type: '', project_code: '', status: 'active' })
const vendorBindForm = reactive({ vendor_id: null, vendor_vehicle_id: '', vendor_vehicle_name: '', vendor_vin: '' })
const regulatoryBindForm = reactive({ platform_id: null, regulatory_vehicle_no: '', reporting_strategy: 'strict' })

// 用于回填编辑表单
function resetForm() {
  Object.assign(form, { name: '', vin: '', plate_no: '', model: '', brand: '', vehicle_category: '', power_type: '', project_code: '', status: 'active' })
  editing.value = null
}

async function load() {
  const [v, rowsData, p] = await Promise.all([
    api.get('/vendors').catch(() => []),
    api.get('/vehicles').catch(() => []),
    api.get('/regulatory-platforms').catch(() => []),
  ])
  vendors.value = v
  rows.value = rowsData
  platforms.value = p
}

function vendorName(bindings) {
  if (!bindings || bindings.length === 0) return '未绑定'
  const b = bindings[0]
  const v = vendors.value.find(v => v.id === b.vendor_id)
  return v ? `${v.name} (${b.vendor_vehicle_id})` : b.vendor_vehicle_id
}

function regulatorySummary(bindings) {
  if (!bindings || bindings.length === 0) return '未绑定'
  return bindings.map(b => {
    const p = platforms.value.find(p => p.id === b.platform_id)
    return `${p?.name || b.platform_id}:${b.regulatory_vehicle_no}`
  }).join(', ')
}

async function createVehicle() {
  message.value = ''
  try {
    await api.post('/vehicles', { ...form })
    message.value = '创建成功'
    showCreate.value = false
    resetForm()
    await load()
  } catch (e) { message.value = `创建失败: ${e.message}` }
}

function startEdit(row) {
  editing.value = row.id
  Object.assign(form, {
    name: row.name, vin: row.vin || '', plate_no: row.plate_no || '',
    model: row.model || '', brand: row.brand || '',
    vehicle_category: row.vehicle_category || '', power_type: row.power_type || '',
    project_code: row.project_code || '', status: row.status || 'active'
  })
}

async function saveEdit() {
  message.value = ''
  try {
    await api.put(`/vehicles/${editing.value}`, { ...form })
    message.value = '更新成功'
    editing.value = null
    resetForm()
    await load()
  } catch (e) { message.value = `更新失败: ${e.message}` }
}

async function bindVendor(vehicleId) {
  message.value = ''
  try {
    await api.post(`/vehicles/${vehicleId}/vendor-bindings`, { ...vendorBindForm })
    message.value = '厂商绑定成功'
    showBindVendor.value = null
    await load()
  } catch (e) { message.value = `厂商绑定失败: ${e.message}` }
}

async function bindRegulatory(vehicleId) {
  message.value = ''
  try {
    await api.post(`/vehicles/${vehicleId}/regulatory-bindings`, { ...regulatoryBindForm })
    message.value = '监管绑定成功'
    showBindRegulatory.value = null
    await load()
  } catch (e) { message.value = `监管绑定失败: ${e.message}` }
}

async function toggleStatus(row) {
  const newStatus = row.status === 'active' ? 'inactive' : 'active'
  try {
    await api.put(`/vehicles/${row.id}`, { ...row, status: newStatus })
    await load()
  } catch (e) { message.value = `操作失败: ${e.message}` }
}

onMounted(load)
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>车辆管理</h1>
        <p>维护中台车辆档案，绑定厂商与监管平台</p>
      </div>
      <div style="display:flex;gap:0.5rem;">
        <button class="primary" @click="load">刷新</button>
        <button class="primary" @click="showCreate = true; resetForm()">+ 新建车辆</button>
      </div>
    </header>

    <p v-if="message" :class="message.includes('失败') ? 'error' : ''" style="margin-bottom:1rem;font-size:.85rem;">{{ message }}</p>

    <!-- 新建/编辑车辆表单 -->
    <div v-if="showCreate || editing" class="modal-overlay" @click.self="showCreate = false; editing = null; resetForm()">
      <div class="modal">
        <h2>{{ editing ? '编辑车辆' : '新建车辆' }}</h2>
        <div class="form-grid">
          <label>名称 *<input v-model="form.name" required /></label>
          <label>VIN<input v-model="form.vin" /></label>
          <label>车牌号<input v-model="form.plate_no" /></label>
          <label>车型<input v-model="form.model" /></label>
          <label>品牌<input v-model="form.brand" /></label>
          <label>车辆类别<input v-model="form.vehicle_category" /></label>
          <label>动力类型<input v-model="form.power_type" /></label>
          <label>项目编号<input v-model="form.project_code" /></label>
          <label>状态
            <select v-model="form.status">
              <option value="active">启用</option>
              <option value="inactive">停用</option>
            </select>
          </label>
        </div>
        <div style="display:flex;gap:0.5rem;margin-top:1rem;">
          <button class="primary" @click="editing ? saveEdit() : createVehicle()">{{ editing ? '保存修改' : '创建' }}</button>
          <button @click="showCreate = false; editing = null; resetForm()" style="background:#eee;border:1px solid #d9d9d9;padding:.45rem 1rem;border-radius:6px;cursor:pointer;">取消</button>
        </div>
      </div>
    </div>

    <!-- 厂商绑定弹窗 -->
    <div v-if="showBindVendor" class="modal-overlay" @click.self="showBindVendor = null">
      <div class="modal">
        <h2>绑定厂商</h2>
        <div class="form-grid">
          <label>厂商 *
            <select v-model="vendorBindForm.vendor_id">
              <option :value="null" disabled>请选择厂商</option>
              <option v-for="v in vendors" :key="v.id" :value="v.id">{{ v.name }} ({{ v.vendor_type === 'neolix' ? '新石器' : '九识' }})</option>
            </select>
          </label>
          <label>厂商车辆ID *<input v-model="vendorBindForm.vendor_vehicle_id" required /></label>
          <label>厂商车辆名称<input v-model="vendorBindForm.vendor_vehicle_name" /></label>
          <label>厂商VIN<input v-model="vendorBindForm.vendor_vin" /></label>
        </div>
        <div style="display:flex;gap:0.5rem;margin-top:1rem;">
          <button class="primary" @click="bindVendor(showBindVendor)">确认绑定</button>
          <button @click="showBindVendor = null" style="background:#eee;border:1px solid #d9d9d9;padding:.45rem 1rem;border-radius:6px;cursor:pointer;">取消</button>
        </div>
      </div>
    </div>

    <!-- 监管绑定弹窗 -->
    <div v-if="showBindRegulatory" class="modal-overlay" @click.self="showBindRegulatory = null">
      <div class="modal">
        <h2>绑定监管平台</h2>
        <div class="form-grid">
          <label>监管平台 *
            <select v-model="regulatoryBindForm.platform_id">
              <option :value="null" disabled>请选择平台</option>
              <option v-for="p in platforms" :key="p.id" :value="p.id">{{ p.name }} ({{ p.city_code }})</option>
            </select>
          </label>
          <label>监管车辆编号 *（8位）<input v-model="regulatoryBindForm.regulatory_vehicle_no" maxlength="8" required /></label>
          <label>上报策略
            <select v-model="regulatoryBindForm.reporting_strategy">
              <option value="strict">严格模式</option>
              <option value="repeat">保活模式（最近值复用）</option>
              <option value="linear">插值模式</option>
            </select>
          </label>
        </div>
        <div style="display:flex;gap:0.5rem;margin-top:1rem;">
          <button class="primary" @click="bindRegulatory(showBindRegulatory)">确认绑定</button>
          <button @click="showBindRegulatory = null" style="background:#eee;border:1px solid #d9d9d9;padding:.45rem 1rem;border-radius:6px;cursor:pointer;">取消</button>
        </div>
      </div>
    </div>

    <!-- 车辆列表 -->
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>VIN</th>
            <th>车牌</th>
            <th>厂商绑定</th>
            <th>监管绑定</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0">
            <td colspan="8" class="empty">暂无车辆，请先接入厂商后同步，或手动创建</td>
          </tr>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.name }}</td>
            <td>{{ r.vin || '-' }}</td>
            <td>{{ r.plate_no || '-' }}</td>
            <td><span :class="r.vendor_bindings?.length ? 'badge badge-success' : 'badge badge-warn'">{{ vendorName(r.vendor_bindings) }}</span></td>
            <td><span :class="r.regulatory_bindings?.length ? 'badge badge-info' : 'badge badge-warn'">{{ regulatorySummary(r.regulatory_bindings) }}</span></td>
            <td>
              <span :class="r.status === 'active' ? 'badge badge-success' : 'badge badge-danger'">
                {{ r.status === 'active' ? '启用' : '停用' }}
              </span>
            </td>
            <td>
              <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
                <button @click="startEdit(r)" style="font-size:0.7rem;padding:0.2rem 0.4rem;">编辑</button>
                <button @click="showBindVendor = r.id" style="font-size:0.7rem;padding:0.2rem 0.4rem;">绑定厂商</button>
                <button @click="showBindRegulatory = r.id" style="font-size:0.7rem;padding:0.2rem 0.4rem;">绑定监管</button>
                <button @click="toggleStatus(r)" style="font-size:0.7rem;padding:0.2rem 0.4rem;">{{ r.status === 'active' ? '停用' : '启用' }}</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: #fff; border-radius: 12px; padding: 2rem; width: 520px; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 4px 24px rgba(0,0,0,.12);
}
.modal h2 { font-size: 1.1rem; margin-bottom: 1rem; }
</style>
