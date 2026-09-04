import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import AuthPage from './pages/AuthPage'
import CheckoutPage from './pages/CheckoutPage'
import DashboardPage from './pages/DashboardPage'
import WebhookPage from './pages/WebhookPage'
import ApiKeysPage from './pages/ApiKeysPage'
import SettingsPage from './pages/SettingsPage'
import Layout from './components/Layout'

function PrivateRoute({ children }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AuthPage />} />
      <Route path="/pay/:linkId" element={<CheckoutPage />} />
      <Route path="/pay" element={<CheckoutPage />} />
      <Route
        path="/*"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="webhook" element={<WebhookPage />} />
        <Route path="api-keys" element={<ApiKeysPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="dashboard" replace />} />
      </Route>
    </Routes>
  )
}
