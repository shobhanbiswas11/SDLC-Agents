import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Plus, History } from 'lucide-react'
import { runAgent, fixAgent } from './lib/api'
import { useHistory } from './hooks/useHistory'
import { HistorySidebar } from './components/HistorySidebar'
import { ChatMessage } from './components/ChatMessage'

const QUICK_PROMPTS = [
  'Create a t2.micro EC2 instance in ap-south-1 with proper tags',
  'Create a Kubernetes deployment for nginx:1.25 with resource limits',
  'Create a Docker Compose for web app + postgres with secure config',
  'Create an S3 bucket with encryption and block public access',
]

function genId() {
  return Math.random().toString(36).slice(2, 9)
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const [selectedRunId, setSelectedRunId] = useState(null)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const { history, addRun, clearHistory, removeRun } = useHistory()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const newChat = useCallback(() => {
    setMessages([])
    setInput('')
    setError(null)
    setSelectedRunId(null)
    setTimeout(() => inputRef.current?.focus(), 100)
  }, [])

  const submit = useCallback(async (prompt) => {
    if (!prompt.trim() || isLoading) return
    setError(null)
    setSelectedRunId(null)

    const loadingId = genId()
    const newMessages = [
      ...messages,
      { id: genId(), role: 'user', content: prompt },
      { id: loadingId, role: 'assistant', content: '', isLoading: true },
    ]
    setMessages(newMessages)
    setInput('')
    setIsLoading(true)

    try {
      const run = await runAgent(prompt, messages)
      const finalMessages = newMessages.map(m =>
        m.id === loadingId
          ? { id: loadingId, role: 'assistant', content: run.result, run, isLoading: false }
          : m
      )
      setMessages(finalMessages)
      // Save run with full conversation so history can restore it
      addRun(run, finalMessages)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Agent failed')
      setMessages(prev => prev.filter(m => m.id !== loadingId))
    } finally {
      setIsLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isLoading, addRun, messages])

  const handleFix = useCallback(async (failedMessage) => {
    if (isLoading) return
    setError(null)

    const updatedMessages = messages.map(m =>
      m.id === failedMessage.id ? { ...m, fixed: true } : m
    )
    const loadingId = genId()
    const newMessages = [
      ...updatedMessages,
      { id: loadingId, role: 'assistant', content: '', isLoading: true },
    ]
    setMessages(newMessages)
    setIsLoading(true)

    try {
      const run = await fixAgent(failedMessage.content, messages)
      const finalMessages = newMessages.map(m =>
        m.id === loadingId
          ? { id: loadingId, role: 'assistant', content: run.result, run, isLoading: false }
          : m
      )
      setMessages(finalMessages)
      addRun(run, finalMessages)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fix failed')
      setMessages(prev => prev.filter(m => m.id !== loadingId))
    } finally {
      setIsLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isLoading, addRun, messages])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit(input)
    }
  }

  // Restore full conversation from history
  const handleHistorySelect = (run) => {
    setSelectedRunId(run.id)
    if (run.messages?.length > 0) {
      setMessages(run.messages)
    } else {
      // Fallback for old history entries
      setMessages([
        { id: run.id + '-u', role: 'user', content: run.prompt },
        { id: run.id + '-a', role: 'assistant', content: run.result, run },
      ])
    }
    setShowHistory(false)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="h-screen w-full bg-white flex overflow-hidden">

      {/* History Sidebar */}
      {showHistory && (
        <HistorySidebar
          history={history}
          selectedId={selectedRunId}
          onSelect={handleHistorySelect}
          onClear={clearHistory}
          onRemove={removeRun}
          onClose={() => setShowHistory(false)}
        />
      )}

      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="shrink-0 border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
            <h1 className="text-lg font-semibold text-black">IaC Agent</h1>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">
                {history.length} run{history.length !== 1 ? 's' : ''}
              </span>
              {!isEmpty && (
                <button
                  onClick={newChat}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-all"
                >
                  <Plus size={15} />
                  New Chat
                </button>
              )}
              <button
                onClick={() => setShowHistory(v => !v)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  showHistory
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <History size={15} />
                History
              </button>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto bg-white">
          {isEmpty ? (
            <div className="h-full flex flex-col items-center justify-center px-6 py-12">
              <div className="max-w-2xl w-full space-y-8 text-center">
                <div className="space-y-3">
                  <h2 className="text-4xl font-semibold text-black">How can I help?</h2>
                  <p className="text-lg text-gray-600">
                    Describe the infrastructure you need or ask for help with IaC
                  </p>
                </div>
                <div className="grid grid-cols-1 gap-3 pt-4">
                  {QUICK_PROMPTS.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => submit(prompt)}
                      className="p-4 text-left rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition-all hover:border-gray-400"
                    >
                      <div className="font-semibold text-black text-base">
                        {prompt.split(' ').slice(0, 3).join(' ')}
                      </div>
                      <div className="text-gray-600 text-sm mt-2">{prompt}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto w-full px-6 py-8 space-y-6">
              {messages.map(msg => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onFix={handleFix}
                />
              ))}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-6 py-4 text-base text-red-700">
                  {error}
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="shrink-0 border-t border-gray-200 bg-white p-6">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex gap-4">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message IaC Agent..."
                rows={1}
                disabled={isLoading}
                className="flex-1 bg-white border border-gray-300 rounded-lg px-5 py-4 text-base text-black placeholder:text-gray-500 focus:outline-none focus:border-gray-600 focus:ring-1 focus:ring-gray-200 resize-none disabled:opacity-50 transition-all"
              />
              <button
                onClick={() => submit(input)}
                disabled={isLoading || !input.trim()}
                className="flex items-center justify-center w-12 h-12 rounded-lg bg-black text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all mt-1"
              >
                <Send size={18} />
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-3 text-center">
              Press Enter to send • Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}