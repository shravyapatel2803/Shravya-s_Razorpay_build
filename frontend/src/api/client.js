import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Auto-attach JWT Bearer token
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/'
    }
    return Promise.reject(err)
  }
)

export default client

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => client.post('/auth/register', data),
  login: (data) => client.post('/auth/login', data),
  refresh: (refreshToken) => client.post('/auth/refresh', { refresh_token: refreshToken }),
  logout: (refreshToken) => client.post('/auth/logout', { refresh_token: refreshToken }),
  me: () => client.get('/auth/me'),
  updateMe: (data) => client.put('/auth/me', data),
  changePassword: (data) => client.post('/auth/me/change-password', data),
  createSubUser: (data) => client.post('/auth/sub-users', data),
  listSubUsers: () => client.get('/auth/sub-users'),
  deactivateSubUser: (id) => client.delete(`/auth/sub-users/${id}`),
}

// ─── API Keys ─────────────────────────────────────────────────────────────────
export const apiKeysAPI = {
  list: () => client.get('/api-keys/'),
  create: (data) => client.post('/api-keys/', data),
  revoke: (id) => client.delete(`/api-keys/${id}`),
}

// ─── Recovery / Audit ────────────────────────────────────────────────────────
export const recoveryAPI = {
  fireWebhook: (data) => client.post('/webhook/payment-failed', data),
  metrics: () => client.get('/audit/metrics'),
  logs: (limit = 20) => client.get(`/audit/logs?limit=${limit}`),
  reset: () => client.post('/audit/reset'),
}

// ─── Health ───────────────────────────────────────────────────────────────────
export const healthAPI = {
  check: () => client.get('/health'),
}
