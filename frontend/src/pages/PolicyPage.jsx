import { useState } from 'react'
import { api } from '../api/client'

const SAMPLE_QUESTIONS = [
  'What is the FAME-II scheme?',
  "What is Karnataka's approach to EV policy?",
  'What are public charging standards in India?',
  'Do EVs get road tax exemptions?',
]

export default function PolicyPage() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const ask = async (q) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await api.askPolicy({ question: q, top_k: 3 })
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (question.trim()) ask(question.trim())
  }

  return (
    <div>

      <form onSubmit={handleSubmit} className="qa-form">
        <input
          type="text"
          placeholder="Ask a question about EV policy…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Searching…' : 'Ask'}
        </button>
      </form>

      <div className="sample-questions">
        {SAMPLE_QUESTIONS.map((q) => (
          <button key={q} className="chip" onClick={() => { setQuestion(q); ask(q) }}>
            {q}
          </button>
        ))}
      </div>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="qa-result">
          <p className="qa-answer">{result.answer}</p>
          {result.sources.length > 0 && (
            <div className="qa-sources">
              <strong>Sources:</strong>
              {result.sources.map((s, i) => (
                <div key={i} className="qa-source">
                  <span className="qa-source-title">{s.source_document}</span>
                  <span className="qa-source-meta">last verified {s.last_verified} · relevance {s.relevance_score}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
