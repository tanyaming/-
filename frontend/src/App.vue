<script setup>
import { useRouter, useRoute } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import { api } from './api/client'

const router = useRouter()
const route = useRoute()
const user = ref(null)
const loginForm = ref({ username: 'admin', password: 'change-me' })
const loginError = ref('')

const isLoginPage = computed(() => route.path === '/login')

const navItems = [
  { path: '/', label: '概览' },
  { path: '/vendors', label: '厂商接入' },
  { path: '/platforms', label: '监管平台' },
  { path: '/vehicles', label: '车辆管理' },
  { path: '/certificates', label: '证书管理' },
  { path: '/states', label: '实时状态' },
  { path: '/reports', label: '上报监控' },
  { path: '/alerts', label: '告警中心' },
]

async function login() {
  loginError.value = ''
  try {
    const res = await api.post('/auth/login', loginForm.value)
    localStorage.setItem('token', res.token)
    user.value = { username: loginForm.value.username }
    router.push('/')
  } catch (e) {
    loginError.value = e.message
  }
}

async function logout() {
  await api.post('/auth/logout', {}).catch(() => {})
  localStorage.removeItem('token')
  user.value = null
  router.push('/login')
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
    return
  }
  try {
    user.value = await api.get('/auth/me')
  } catch {
    localStorage.removeItem('token')
    router.push('/login')
  }
})
</script>

<template>
  <div v-if="isLoginPage" class="login-page">
    <form class="login-form" @submit.prevent="login">
      <h1>无人车数据中台</h1>
      <label>用户名 <input v-model="loginForm.username" required /></label>
      <label>密码 <input v-model="loginForm.password" type="password" required /></label>
      <button class="primary" type="submit">登录</button>
      <p v-if="loginError" class="error">{{ loginError }}</p>
    </form>
  </div>

  <div v-else class="layout">
    <aside class="sidebar">
      <div class="sidebar-brand" @click="router.push('/')"> 数据中台</div>
      <nav>
        <a
          v-for="item in navItems"
          :key="item.path"
          :class="{ active: route.path === item.path }"
          @click.prevent="router.push(item.path)"
        >
          {{ item.label }}
        </a>
      </nav>
      <div class="sidebar-footer">
        <span v-if="user">{{ user.username }}</span>
        <button @click="logout">登出</button>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #1a1a2e; }

.login-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.login-form { background: #fff; padding: 2.5rem; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.08); width: 360px; }
.login-form h1 { font-size: 1.4rem; margin-bottom: 1.5rem; text-align: center; }
.login-form label { display: block; margin-bottom: 1rem; font-size: .85rem; color: #555; }
.login-form input { width: 100%; padding: .55rem .75rem; border: 1px solid #d9d9d9; border-radius: 6px; font-size: .9rem; margin-top: .25rem; }
.login-form .error { color: #e74c3c; font-size: .8rem; margin-top: .75rem; }

.layout { display: flex; min-height: 100vh; }
.sidebar { width: 200px; background: #1a1a2e; color: #ccc; display: flex; flex-direction: column; }
.sidebar-brand { padding: 1.2rem 1rem; font-weight: 700; font-size: 1.1rem; color: #fff; cursor: pointer; border-bottom: 1px solid #2a2a4a; }
.sidebar nav { flex: 1; padding: .5rem 0; }
.sidebar nav a { display: block; padding: .6rem 1rem; color: #aaa; text-decoration: none; font-size: .85rem; cursor: pointer; border-left: 3px solid transparent; transition: .15s; }
.sidebar nav a:hover { color: #fff; background: #16213e; }
.sidebar nav a.active { color: #fff; border-left-color: #4fc3f7; background: #16213e; }
.sidebar-footer { padding: .75rem 1rem; border-top: 1px solid #2a2a4a; font-size: .8rem; display: flex; justify-content: space-between; align-items: center; }
.sidebar-footer button { background: none; border: 1px solid #555; color: #aaa; padding: .2rem .6rem; border-radius: 4px; cursor: pointer; font-size: .75rem; }
.sidebar-footer button:hover { color: #fff; border-color: #999; }

.main { flex: 1; padding: 1.5rem; overflow-y: auto; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
.page-header h1 { font-size: 1.3rem; }
.page-header p { font-size: .8rem; color: #777; margin-top: .25rem; }

button.primary { background: #1a73e8; color: #fff; border: none; padding: .45rem 1rem; border-radius: 6px; cursor: pointer; font-size: .85rem; }
button.primary:hover { background: #1557b0; }
button.danger { background: #e74c3c; color: #fff; border: none; padding: .3rem .7rem; border-radius: 4px; cursor: pointer; font-size: .75rem; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; background: #fff; padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.04); }
.form-grid .span-2 { grid-column: span 2; }
.form-grid label { font-size: .8rem; color: #555; }
.form-grid input, .form-grid select, .form-grid textarea { width: 100%; padding: .45rem .65rem; border: 1px solid #d9d9d9; border-radius: 6px; font-size: .85rem; margin-top: .25rem; }
.form-grid textarea { font-family: 'SF Mono', 'Fira Code', monospace; font-size: .8rem; resize: vertical; }
.form-message { font-size: .8rem; align-self: center; }

.table-wrap { background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.04); overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
th, td { padding: .6rem .8rem; text-align: left; border-bottom: 1px solid #f0f0f0; }
th { background: #fafafa; font-weight: 600; color: #555; }
td.empty { text-align: center; color: #999; padding: 2rem; }

.badge { display: inline-block; padding: .15rem .5rem; border-radius: 10px; font-size: .75rem; }
.badge-info { background: #e3f2fd; color: #1565c0; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warn { background: #fff3e0; color: #e65100; }
.badge-danger { background: #ffebee; color: #c62828; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { background: #fff; padding: 1.2rem; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.04); }
.stat-card .stat-value { font-size: 1.8rem; font-weight: 700; color: #1a73e8; }
.stat-card .stat-label { font-size: .75rem; color: #777; margin-top: .25rem; }

.page { }

.error { color: #e74c3c; }
</style>
