import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

console.log('Starting app...');
try {
  const root = document.getElementById('root');
  console.log('Root element:', root);
  if (!root) throw new Error('Root element not found');

  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
  console.log('App rendered');
} catch (e) {
  console.error('Error rendering app:', e);
}
