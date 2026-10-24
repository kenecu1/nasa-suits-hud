import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

const rootE1 = document.getElementById('root');
if (!rootE1) throw new Error("HUD failed to start: #root not foundin index.html");
createRoot(rootE1).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
