import { useEffect, useState } from 'react'
import { api } from '../api/client'

const inr = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`

const STATES = ['Delhi', 'Maharashtra', 'Gujarat', 'Karnataka', 'Tamil Nadu', 'Other']

export default function TcoPage() {
  const [models, setModels] = useState([])
  const [form, setForm] = useState({
    model_id: '',
    annual_km: 12000,
    state: 'Delhi',
    payment_mode: 'cash',
    ownership_years: 5,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.listModels().then((data) => {
      setModels(data)
      if (data.length) setForm((f) => ({ ...f, model_id: data[0].id }))
    })
  }, [])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((f) => ({
      ...f,
      [name]: ['annual_km', 'ownership_years'].includes(name) ? Number(value) : value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await api.calculateTco(form)
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
          EV Model
          <select name="model_id" value={form.model_id} onChange={handleChange}>
            {models.map((m) => (
              <option key={m.id} value={m.id}>{m.make} {m.model}</option>
            ))}
          </select>
        </label>

        <label>
          Annual km driven
          <input type="number" name="annual_km" min="1" value={form.annual_km} onChange={handleChange} />
        </label>

        <label>
          State (for subsidy)
          <select name="state" value={form.state} onChange={handleChange}>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>

        <label>
          Payment mode
          <select name="payment_mode" value={form.payment_mode} onChange={handleChange}>
            <option value="cash">Cash</option>
            <option value="loan">Loan</option>
          </select>
        </label>

        <label>
          Ownership period (years)
          <input type="number" name="ownership_years" min="1" max="20" value={form.ownership_years} onChange={handleChange} />
        </label>

        <button type="submit" disabled={loading || !form.model_id}>
          {loading ? 'Calculating…' : 'Calculate TCO'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="tco-result">
          <table className="data-table">
            <tbody>
              <tr><td>Base price</td><td>{inr(result.base_price_inr)}</td></tr>
              <tr><td>Central subsidy</td><td>-{inr(result.central_subsidy_inr)}</td></tr>
              <tr><td>State subsidy</td><td>-{inr(result.state_subsidy_inr)}</td></tr>
              <tr><td><strong>Effective purchase price</strong></td><td><strong>{inr(result.effective_purchase_price_inr)}</strong></td></tr>
              <tr><td>Running cost (annual / total)</td><td>{inr(result.running_cost_annual_inr)} / {inr(result.running_cost_total_inr)}</td></tr>
              <tr><td>Maintenance (annual / total)</td><td>{inr(result.maintenance_cost_annual_inr)} / {inr(result.maintenance_cost_total_inr)}</td></tr>
              <tr><td>Insurance (total)</td><td>{inr(result.insurance_cost_total_inr)}</td></tr>
              {result.loan && (
                <>
                  <tr><td>Loan down payment</td><td>{inr(result.loan.down_payment_inr)}</td></tr>
                  <tr><td>Loan monthly EMI</td><td>{inr(result.loan.monthly_emi_inr)}</td></tr>
                  <tr><td>Loan total interest</td><td>{inr(result.loan.total_interest_inr)}</td></tr>
                </>
              )}
              <tr><td>Estimated resale value</td><td>-{inr(result.resale_value_inr)}</td></tr>
              <tr className="total-row">
                <td><strong>Total Cost of Ownership ({result.ownership_years} yrs)</strong></td>
                <td><strong>{inr(result.total_cost_of_ownership_inr)}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
