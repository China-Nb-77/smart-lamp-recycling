// 强制覆盖 API 地址 - 必须在所有 import 之前
if (typeof window !== 'undefined') {
  window.__API_BASE_URL__ = 'http://114.215.177.52:8000';
  window.__VISION_API_URL__ = 'http://114.215.177.52:8000/vision-api';
  window.__PAYMENT_API_URL__ = 'http://114.215.177.52:8000/pay-api';
  window.__AGENT_API_URL__ = 'http://114.215.177.52:8000/api';
  (window as any).global = window;
  localStorage.setItem('VITE_API_BASE_URL', 'http://114.215.177.52:8000');
  localStorage.setItem('VITE_VISION_API_BASE_URL', 'http://114.215.177.52:8000/vision-api');
  localStorage.setItem('VITE_PAYMENT_API_BASE_URL', 'http://114.215.177.52:8000/pay-api');
}

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
