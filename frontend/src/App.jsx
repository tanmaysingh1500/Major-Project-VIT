import { useEffect, useState } from 'react'
import { api } from './api/client'
import EvModelsPage from './pages/EvModelsPage'
import TcoPage from './pages/TcoPage'
import SohPage from './pages/SohPage'
import PolicyPage from './pages/PolicyPage'
import RecommendPage from './pages/RecommendPage'
import './App.css'

const TABS = [
  { id: 'models', label: 'EV Models' },
  { id: 'tco', label: 'TCO Calculator' },
  { id: 'soh', label: 'Battery SOH' },
  { id: 'policy', label: 'Policy Q&A' },
  { id: 'recommend', label: 'Recommend' },
]

function App() {
  const [status, setStatus] = useState('checking…')
  const [tab, setTab] = useState('models')

  useEffect(() => {
    api
      .health()
      .then((data) => setStatus(`backend ok (${data.service})`))
      .catch(() => setStatus('backend unreachable'))
  }, [])

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>EV Pal</h1>
        <p>EV decision-support for the Indian market — MVP build</p>
      </header>

      <nav className="tab-bar">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'tab active' : 'tab'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {tab === 'models' && <EvModelsPage />}
        {tab === 'tco' && <TcoPage />}
        {tab === 'soh' && <SohPage />}
        {tab === 'policy' && <PolicyPage />}
        {tab === 'recommend' && <RecommendPage />}
      </main>
    </div>
  )
}

export default App
