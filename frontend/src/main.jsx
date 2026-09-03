import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'sonner'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0f0f1a',
            border: '1px solid #1e1e35',
            color: '#e2e8f0',
            borderRadius: '10px',
          },
        }}
        richColors
      />
    </BrowserRouter>
  </React.StrictMode>
)
