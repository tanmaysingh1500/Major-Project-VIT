import { useState } from 'react'
import { api } from '../api/client'

const inr = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`
const STATES = ['Delhi', 'Maharashtra', 'Gujarat', 'Karnataka', 'Tamil Nadu', 'Other']

export default function RecommendPage() {
  const [form, setForm] = useState({
    budget_inr: 1600000,
    daily_km: 40,
    state: 'Delhi',
    payment_mode: 'cash',
    ownership_years: 5,
  })
  const [weights, setWeights] = useState({ cost: 40, range: 25, battery_health: 20, charging_speed: 15 })
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleFormChange = (e) => {
    const { name, value } = e.target
    setForm((f) => ({
      ...f,
      [name]: ['budget_inr', 'daily_km', 'ownership_years'].includes(name) ? Number(value) : value,
    }))
  }

  const handleWeightChange = (key) => (e) => {
    setWeights((w) => ({ ...w, [key]: Number(e.target.value) }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const data = await api.recommend({ ...form, weights })
      setResults(data.results)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="form-grid">
        <label>
          Budget (₹)
          <input type="number" name="budget_inr" min="1" value={form.budget_inr} onChange={handleFormChange} />
        </label>
        <label>
          Daily distance (km)
          <input type="number" name="daily_km" min="1" value={form.daily_km} onChange={handleFormChange} />
        </label>
        <label>
          Preferred state
          <select name="state" value={form.state} onChange={handleFormChange}>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label>
          Payment mode
          <select name="payment_mode" value={form.payment_mode} onChange={handleFormChange}>
            <option value="cash">Cash</option>
            <option value="loan">Loan</option>
          </select>
        </label>
        <label>
          Ownership years
          <input type="number" name="ownership_years" min="1" max="20" value={form.ownership_years} onChange={handleFormChange} />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Scoring…' : 'Get Recommendations'}
        </button>
      </form>

      <div className="weights-panel">
        <p className="weights-title">Adjust scoring weights (relative, don't need to sum to 100):</p>
        <div className="weights-grid">
          {[
            ['cost', 'Cost'],
            ['range', 'Range'],
            ['battery_health', 'Battery health'],
            ['charging_speed', 'Charging speed'],
          ].map(([key, label]) => (
            <label key={key} className="weight-slider">
              <span>{label}: {weights[key]}</span>
              <input
                type="range"
                min="0"
                max="100"
                value={weights[key]}
                onChange={handleWeightChange(key)}
              />
            </label>
          ))}
        </div>
      </div>

      {error && <p className="error">Error: {error}</p>}

      {results && (
        <div className="recommend-results">
          {results.map((r, i) => (
            <div key={r.model_id} className={`rec-card ${r.within_budget ? '' : 'over-budget'}`}>
              <div className="rec-header">
                <span className="rec-rank">#{i + 1}</span>
                <span className="rec-name">{r.make} {r.model}</span>
                <span className="rec-score">score {(r.score*100).toFixed(2)}</span>
                {!r.within_budget && <span className="rec-badge">Over budget</span>}
              </div>
              <div className="rec-body">
                <span>Effective price: {inr(r.tco.effective_purchase_price_inr)}</span>
                <span>TCO ({r.tco.ownership_years} yrs): {inr(r.tco.total_cost_of_ownership_inr)}</span>
                <span>Projected SOH: {r.projected_soh_pct}%</span>
              </div>
              <p className="rec-note">{r.soh_adjusted_resale_note}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
