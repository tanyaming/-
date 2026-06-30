const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const DEFAULT_TIMEOUT = 15000 // 请求超时，避免页面无限等待

async function request(method, url, body, { timeout = DEFAULT_TIMEOUT } = {}) {
  const token = localStorage.getItem('token')
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  // 超时保护：超过 timeout 主动中断，前端不会再被慢请求“卡死”
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  let res
  try {
    res = await fetch(`${API_BASE}${url}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch (e) {
    clearTimeout(timer)
    if (e.name === 'AbortError') throw new Error('请求超时，请稍后重试')
    throw new Error('网络异常，请检查后端服务')
  }
  clearTimeout(timer)

  if (res.status === 401) {
    const t = localStorage.getItem('token')
    if (t) {
      localStorage.removeItem('token')
      window.location.hash = '#/login'
    }
    throw new Error('未登录或登录已过期')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `请求失败 (${res.status})`)
  }

  return res.json()
}

export const api = {
  get: (url, opts) => request('GET', url, undefined, opts),
  post: (url, body, opts) => request('POST', url, body, opts),
  put: (url, body, opts) => request('PUT', url, body, opts),
  delete: (url, opts) => request('DELETE', url, undefined, opts),
}

/**
 * 安全轮询：递归 setTimeout 替代 setInterval。
 * - 上一次请求结束后才计时下一次，避免慢请求堆叠。
 * - 页面隐藏（切到后台标签页）时自动暂停，回到前台立即刷新一次。
 * 返回 stop() 用于在组件卸载时停止。
 */
export function startPolling(fn, intervalMs) {
  let stopped = false
  let timer = null

  async function tick() {
    if (stopped) return
    if (document.hidden) {
      // 后台标签页不轮询，等可见时由 visibilitychange 触发
      return
    }
    try {
      await fn()
    } catch {
      // 单次失败不中断轮询
    }
    if (!stopped) timer = setTimeout(tick, intervalMs)
  }

  function onVisible() {
    if (stopped) return
    if (!document.hidden) {
      clearTimeout(timer)
      tick()
    }
  }
  document.addEventListener('visibilitychange', onVisible)

  tick()

  return function stop() {
    stopped = true
    clearTimeout(timer)
    document.removeEventListener('visibilitychange', onVisible)
  }
}
