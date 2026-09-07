import React from 'react'
import ReactDOM from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import App from './App.jsx'
import { msalInstance } from './msalConfig.js'
import './index.css'

// MSAL v3 requires initialize() to resolve before the app renders, or
// loginPopup can throw "uninitialized_public_client_application".
msalInstance.initialize().then(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(
    
      <MsalProvider instance={msalInstance}>
        <App />
      </MsalProvider>
    
  )
})
