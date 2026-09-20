import { useEffect, useState } from 'react'
import { api } from '../api/client'

const inr = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`

export default function EvModelsPage() {
  const [models, setModels] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .listModels()
      .then(setModels)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading EV catalog…</p>
  if (error) return <p className="error">Failed to load models: {error}</p>

  return (
    <div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Model</th>
            <th>Body</th>
            <th>Price</th>
            <th>Battery (kWh)</th>
            <th>Range (km)</th>
            <th>Charging (kW)</th>
            <th>Warranty</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.id}>
              <td>{m.make} {m.model}</td>
              <td>{m.body_type}</td>
              <td>{inr(m.price_inr)}</td>
              <td>{m.battery_kwh}</td>
              <td>{m.range_km}</td>
              <td>{m.charging_speed_kw}</td>
              <td>{m.warranty_years} yr / {m.warranty_km.toLocaleString('en-IN')} km</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
