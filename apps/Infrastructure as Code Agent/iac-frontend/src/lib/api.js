const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

function detectStatus(resultText) {
  const match = resultText.match(/status[:\*\s]+\**\s*(PASS|FAIL)/i)
  if (match) return match[1].toUpperCase()
  return 'UNKNOWN'
}

function enrichRun(data, prompt, duration_ms) {
  const resultText = data.result || ''
  const status = (data.status && data.status !== 'UNKNOWN')
    ? data.status
    : detectStatus(resultText)

  return {
    id: data.id || crypto.randomUUID(),
    timestamp: data.timestamp || new Date().toISOString(),
    prompt,
    result: data.result,
    steps: data.steps || [],
    total_steps: data.total_steps || 0,
    status,
    duration_ms: data.duration_ms || duration_ms,
  }
}

// Convert messages array to conversation history format for backend
function buildConversationHistory(messages) {
  return messages
    .filter(m => !m.isLoading && m.content && m.id !== 'welcome')
    .map(m => ({
      role: m.role,
      content: m.content,
    }))
}

export async function runAgent(prompt, messages = []) {
  const start = Date.now()
  const res = await fetch(`${API_BASE}/run-agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      conversation_history: buildConversationHistory(messages),
    }),
  })
  if (!res.ok) throw new Error(`Agent failed: ${res.statusText}`)
  const data = await res.json()
  return enrichRun(data, prompt, Date.now() - start)
}

export async function fixAgent(violations, messages = []) {
  const start = Date.now()
  const res = await fetch(`${API_BASE}/fix-agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: violations,
      conversation_history: buildConversationHistory(messages),
    }),
  })
  if (!res.ok) throw new Error(`Fix failed: ${res.statusText}`)
  const data = await res.json()
  return enrichRun(data, violations, Date.now() - start)
}