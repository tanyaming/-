<script setup>
import { useRouter, useRoute } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import { api } from './api/client'

const router = useRouter()
const route = useRoute()
const user = ref(null)
const loginForm = ref({ username: 'admin', password: 'change-me' })
const loginError = ref('')
const loggingIn = ref(false)
const sidebarOpen = ref(false)

const isLoginPage = computed(() => route.path === '/login')
const currentTitle = computed(() => route.meta?.title || '数据中台')

const navItems = [
  { path: '/', label: '概览', icon: '📊' },
  { path: '/vendors', label: '厂商接入', icon: '🔌' },
  { path: '/platforms', label: '监管平台', icon: '🏛️' },
  { path: '/vehicles', label: '车辆管理', icon: '🚗' },
  { path: '/certificates', label: '证书管理', icon: '🔐' },
  { path: '/states', label: '实时状态', icon: '📡' },
  { path: '/reports', label: '上报监控', icon: '📈' },
  { path: '/alerts', label: '告警中心', icon: '🔔' },
]

function go(path) {
  sidebarOpen.value = false
  router.push(path)
}

async function login() {
  loginError.value = ''
  loggingIn.value = true
  try {
    const res = await api.post('/auth/login', loginForm.value)
    localStorage.setItem('token', res.token)
    user.value = { username: loginForm.value.username }
    router.push('/')
  } catch (e) {
    loginError.value = e.message
  } finally {
    loggingIn.value = false
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
  } catch (e) {
    if (e.message === '未登录或登录已过期') {
      router.push('/login')
    }
  }
})
</script>

<template>
  <div v-if="isLoginPage" class="login-page">
    <form class="login-form" @submit.prevent="login">
      <div class="login-logo">🚗</div>
      <h1>无人车数据中台</h1>
      <p class="login-sub">车辆数据接入与监管上报平台</p>
      <label>用户名 <input v-model="loginForm.username" required /></label>
      <label>密码 <input v-model="loginForm.password" type="password" required /></label>
      <button class="primary" type="submit" :disabled="loggingIn">
        {{ loggingIn ? '登录中…' : '登录' }}
      </button>
      <p v-if="loginError" class="error">{{ loginError }}</p>
    </form>
  </div>

  <div v-else class="layout">
    <div class="scrim" :class="{ show: sidebarOpen }" @click="sidebarOpen = false"></div>
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-brand" @click="go('/')">
        <span class="brand-mark">🚗</span> 数据中台
      </div>
      <nav>
        <a
          v-for="item in navItems"
          :key="item.path"
          :class="{ active: route.path === item.path }"
          @click.prevent="go(item.path)"
        >
          <span class="nav-icon">{{ item.icon }}</span>{{ item.label }}
        </a>
      </nav>
      <div class="sidebar-footer">
        <span v-if="user" class="user-chip">👤 {{ user.username }}</span>
        <button @click="logout">登出</button>
      </div>
    </aside>
    <div class="content">
      <header class="topbar">
        <button class="menu-btn" @click="sidebarOpen = !sidebarOpen" aria-label="菜单">☰</button>
        <h2 class="topbar-title">{{ currentTitle }}</h2>
      </header>
      <main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>


<style>
:root {
  --brand: #2563eb;
  --brand-dark: #1d4ed8;
  --brand-soft: #eff6ff;
  --bg: #f5f7fb;
  --surface: #ffffff;
  --text: #1e2433;
  --text-secondary: #6b7280;
  --text-muted: #9ca3af;
  --border: #eaecf2;
  --border-strong: #d7dbe4;
  --sidebar-bg: #161b2e;
  --sidebar-bg-hover: #1f263f;
  --sidebar-text: #aab1c4;
  --radius: 12px;
  --radius-sm: 8px;
  --shadow-sm: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06);
  --shadow-md: 0 4px 16px rgba(16,24,40,.08);
  --shadow-lg: 0 12px 40px rgba(16,24,40,.14);
  --topbar-h: 56px;
  --ok: #16a34a;
  --warn: #ea580c;
  --danger: #dc2626;
  --info: #2563eb;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  font-size: 14px;
}
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-thumb { background: #cbd2e0; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: #b3bccd; }

/* ---------- 登录页 ---------- */
.login-page {
  display: flex; align-items: center; justify-content: center; min-height: 100vh;
  background: radial-gradient(1200px 600px at 70% -10%, #e7efff 0%, var(--bg) 55%);
  padding: 1rem;
}
.login-form {
  background: var(--surface); padding: 2.5rem 2.25rem; border-radius: 16px;
  box-shadow: var(--shadow-lg); width: 380px; max-width: 100%;
  animation: pop .35s cubic-bezier(.2,.8,.2,1);
}
.login-logo { font-size: 2.4rem; text-align: center; }
.login-form h1 { font-size: 1.35rem; margin-top: .5rem; text-align: center; letter-spacing: .5px; }
.login-sub { text-align: center; color: var(--text-muted); font-size: .8rem; margin-bottom: 1.6rem; margin-top: .25rem; }
.login-form label { display: block; margin-bottom: 1rem; font-size: .82rem; color: var(--text-secondary); }
.login-form input {
  width: 100%; padding: .65rem .8rem; border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
  font-size: .92rem; margin-top: .35rem; transition: border-color .15s, box-shadow .15s;
}
.login-form input:focus { outline: none; border-color: var(--brand); box-shadow: 0 0 0 3px rgba(37,99,235,.15); }
.login-form .primary { width: 100%; padding: .7rem; font-size: .95rem; margin-top: .25rem; }
.login-form .primary:disabled { opacity: .65; cursor: not-allowed; }
.login-form .error { color: var(--danger); font-size: .8rem; margin-top: .85rem; text-align: center; }

/* ---------- 布局 ---------- */
.layout { display: flex; min-height: 100vh; }
.content { flex: 1; display: flex; flex-direction: column; min-width: 0; }

.sidebar {
  width: 220px; background: var(--sidebar-bg); color: var(--sidebar-text);
  display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh; z-index: 40;
}
.sidebar-brand {
  padding: 1.15rem 1.1rem; font-weight: 700; font-size: 1.12rem; color: #fff; cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,.07); display: flex; align-items: center; gap: .5rem;
}
.brand-mark { font-size: 1.2rem; }
.sidebar nav { flex: 1; padding: .6rem .5rem; overflow-y: auto; }
.sidebar nav a {
  display: flex; align-items: center; gap: .6rem; padding: .6rem .75rem; color: var(--sidebar-text);
  text-decoration: none; font-size: .86rem; cursor: pointer; border-radius: var(--radius-sm);
  margin-bottom: 2px; transition: background .15s, color .15s;
}
.nav-icon { font-size: .95rem; width: 1.2rem; text-align: center; }
.sidebar nav a:hover { color: #fff; background: var(--sidebar-bg-hover); }
.sidebar nav a.active { color: #fff; background: linear-gradient(90deg, var(--brand) 0%, var(--brand-dark) 100%); box-shadow: 0 2px 8px rgba(37,99,235,.4); }
.sidebar-footer {
  padding: .85rem 1rem; border-top: 1px solid rgba(255,255,255,.07); font-size: .8rem;
  display: flex; justify-content: space-between; align-items: center; gap: .5rem;
}
.user-chip { color: #cdd3e1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sidebar-footer button {
  background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.18); color: #cdd3e1;
  padding: .28rem .7rem; border-radius: 6px; cursor: pointer; font-size: .76rem; transition: .15s; flex-shrink: 0;
}
.sidebar-footer button:hover { color: #fff; border-color: rgba(255,255,255,.4); background: rgba(255,255,255,.12); }

.topbar {
  height: var(--topbar-h); background: rgba(255,255,255,.85); backdrop-filter: saturate(180%) blur(8px);
  border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: .75rem;
  padding: 0 1.5rem; position: sticky; top: 0; z-index: 30;
}
.topbar-title { font-size: 1rem; font-weight: 650; color: var(--text); }
.menu-btn { display: none; background: none; border: none; font-size: 1.3rem; cursor: pointer; color: var(--text-secondary); }
.scrim { display: none; }

.main { flex: 1; padding: 1.5rem; overflow-y: auto; }

/* 路由过渡 */
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease, transform .18s ease; }
.fade-enter-from { opacity: 0; transform: translateY(6px); }
.fade-leave-to { opacity: 0; transform: translateY(-4px); }

@keyframes pop { from { opacity: 0; transform: scale(.96) translateY(8px); } to { opacity: 1; transform: none; } }

/* ---------- 移动端 ---------- */
@media (max-width: 860px) {
  .menu-btn { display: block; }
  .sidebar { position: fixed; left: 0; top: 0; transform: translateX(-100%); transition: transform .25s ease; }
  .sidebar.open { transform: translateX(0); box-shadow: var(--shadow-lg); }
  .scrim { display: block; position: fixed; inset: 0; background: rgba(0,0,0,.4); opacity: 0; pointer-events: none; transition: opacity .25s; z-index: 35; }
  .scrim.show { opacity: 1; pointer-events: auto; }
  .main { padding: 1rem; }
}

/* PLACEHOLDER_COMPONENT_STYLES */

/* ---------- 页头 ---------- */
.page { animation: fadeUp .25s ease; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.4rem; gap: 1rem; flex-wrap: wrap; }
.page-header h1 { font-size: 1.4rem; font-weight: 680; letter-spacing: .3px; }
.page-header p { font-size: .82rem; color: var(--text-secondary); margin-top: .35rem; }

/* ---------- 按钮 ---------- */
button { font-family: inherit; }
button.primary { background: var(--brand); color: #fff; border: none; padding: .5rem 1.05rem; border-radius: var(--radius-sm); cursor: pointer; font-size: .85rem; font-weight: 550; transition: background .15s, box-shadow .15s, transform .05s; box-shadow: 0 1px 2px rgba(37,99,235,.25); }
button.primary:hover { background: var(--brand-dark); box-shadow: 0 3px 10px rgba(37,99,235,.32); }
button.primary:active { transform: translateY(1px); }
button.danger { background: var(--danger); color: #fff; border: none; padding: .32rem .7rem; border-radius: 6px; cursor: pointer; font-size: .75rem; transition: filter .15s; }
button.danger:hover { filter: brightness(1.08); }

/* ---------- 表单 ---------- */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem 1.1rem; background: var(--surface); padding: 1.5rem; border-radius: var(--radius); margin-bottom: 1.5rem; box-shadow: var(--shadow-sm); border: 1px solid var(--border); }
.form-grid .span-2 { grid-column: span 2; }
.form-grid label { font-size: .8rem; color: var(--text-secondary); font-weight: 500; }
.form-grid input, .form-grid select, .form-grid textarea { width: 100%; padding: .5rem .7rem; border: 1px solid var(--border-strong); border-radius: var(--radius-sm); font-size: .85rem; margin-top: .3rem; background: #fff; transition: border-color .15s, box-shadow .15s; color: var(--text); }
.form-grid input:focus, .form-grid select:focus, .form-grid textarea:focus { outline: none; border-color: var(--brand); box-shadow: 0 0 0 3px rgba(37,99,235,.13); }
.form-grid textarea { font-family: 'SF Mono', 'Fira Code', ui-monospace, monospace; font-size: .8rem; resize: vertical; line-height: 1.5; }
.form-message { font-size: .8rem; align-self: center; color: var(--text-secondary); }

/* ---------- 表格 ---------- */
.table-wrap { background: var(--surface); border-radius: var(--radius); box-shadow: var(--shadow-sm); border: 1px solid var(--border); overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
th, td { padding: .7rem .85rem; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
thead th { background: #fafbfd; font-weight: 600; color: var(--text-secondary); font-size: .78rem; text-transform: none; position: sticky; top: 0; }
tbody tr { transition: background .12s; }
tbody tr:hover { background: var(--brand-soft); }
tbody tr:last-child td { border-bottom: none; }
td.empty { text-align: center; color: var(--text-muted); padding: 2.5rem; }

/* ---------- 徽章 ---------- */
.badge { display: inline-block; padding: .18rem .6rem; border-radius: 999px; font-size: .74rem; font-weight: 550; line-height: 1.5; }
.badge-info { background: #e0ecff; color: #1d4ed8; }
.badge-success { background: #dcfce7; color: #15803d; }
.badge-warn { background: #ffedd5; color: #c2410c; }
.badge-danger { background: #fee2e2; color: #b91c1c; }

/* ---------- 统计卡 ---------- */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { background: var(--surface); padding: 1.3rem 1.4rem; border-radius: var(--radius); box-shadow: var(--shadow-sm); border: 1px solid var(--border); position: relative; overflow: hidden; transition: transform .15s, box-shadow .15s; }
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--brand); opacity: .85; }
.stat-card .stat-value { font-size: 2rem; font-weight: 720; color: var(--text); line-height: 1.1; }
.stat-card .stat-label { font-size: .76rem; color: var(--text-secondary); margin-top: .45rem; }

/* ---------- 加载骨架 / loading ---------- */
.skeleton-row { display: flex; gap: .8rem; padding: .7rem .85rem; border-bottom: 1px solid var(--border); }
.skeleton-cell { height: 14px; border-radius: 5px; flex: 1; background: linear-gradient(90deg, #eef1f6 25%, #e3e7ef 37%, #eef1f6 63%); background-size: 400% 100%; animation: shimmer 1.3s ease infinite; }
@keyframes shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
.loading-inline { display: inline-flex; align-items: center; gap: .5rem; color: var(--text-secondary); font-size: .82rem; }
.spinner { width: 15px; height: 15px; border: 2px solid var(--border-strong); border-top-color: var(--brand); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; color: var(--text-muted); padding: 2.5rem 1rem; }
.empty-state .empty-icon { font-size: 2rem; opacity: .5; display: block; margin-bottom: .5rem; }

.error { color: var(--danger); }
</style>
