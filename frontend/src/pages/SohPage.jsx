import { useState } from 'react'
import { api } from '../api/client'

export default function SohPage() {
  const [form, setForm] = useState({
    age_months: 24,
    mileage_km: 40000,
    fast_charge_pct: 20,
    climate_zone: 'temperate',
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((f) => ({
      ...f,
      [name]: name === 'climate_zone' ? value : Number(value),
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await api.estimateSoh(form)
      setResult(data)
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
          Vehicle age (months)
          <input type="number" name="age_months" min="0" max="240" value={form.age_months} onChange={handleChange} />
        </label>
        <label>
          Mileage (km)
          <input type="number" name="mileage_km" min="0" value={form.mileage_km} onChange={handleChange} />
        </label>
        <label>
          Fast-charge usage (%)
          <input type="number" name="fast_charge_pct" min="0" max="100" value={form.fast_charge_pct} onChange={handleChange} />
        </label>
        <label>
          Climate zone
          <select name="climate_zone" value={form.climate_zone} onChange={handleChange}>
            <option value="hot">Hot</option>
            <option value="temperate">Temperate</option>
            <option value="cold">Cold</option>
          </select>
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Estimating…' : 'Estimate SOH'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="soh-result">
          <div className="soh-gauge">
            <span className="soh-value">{result.estimated_soh_pct}%</span>
            <span className="soh-label">Estimated Battery State of Health</span>
          </div>
          <p className="model-note">{result.model_type}</p>
          <p className="model-note">{result.note}</p>
        </div>
      )}
    </div>
  )
}
