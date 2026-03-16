import { useState } from 'react'
import { ChevronDown, ChevronRight, Terminal, Shield } from 'lucide-react'

export function StepTrace({ steps, duration_ms }) {
  const [expanded, setExpanded] = useState(null)
  const [showTrace, setShowTrace] = useState(false)

  if (!steps?.length) return null

  const toolColor = (tool) =>
    tool.includes('policy') || tool.includes('check') ? '#a78bfa' : '#00d9ff'

  const toolIcon = (tool) =>
    tool.includes('policy') || tool.includes('check')
      ? <Shield size={12} />
      : <Terminal size={12} />

  return (
    <div className="mt-3">
      <button
        onClick={() => setShowTrace(v => !v)}
        className="flex items-center gap-2 text-xs font-mono text-terminal-muted hover:text-terminal-accent transition-colors"
      >
        {showTrace ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span>{steps.length} tool call{steps.length !== 1 ? 's' : ''}</span>
        <span className="opacity-50">·</span>
        <span>{(duration_ms / 1000).toFixed(1)}s</span>
      </button>

      {showTrace && (
        <div className="mt-2 space-y-1.5 pl-3 border-l border-terminal-border">
          {steps.map((step, i) => (
            <div key={i} className="animate-message">
              <button
                className="w-full text-left"
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <div className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-white/5 transition-colors">
                  <span style={{ color: toolColor(step.tool) }}>{toolIcon(step.tool)}</span>
                  <span className="font-mono text-xs" style={{ color: toolColor(step.tool) }}>
                    {step.tool}
                  </span>
                  <span className="text-terminal-muted text-xs truncate flex-1 text-left">
                    {String(step.input).slice(0, 60)}{String(step.input).length > 60 ? '…' : ''}
                  </span>
                  {expanded === i
                    ? <ChevronDown size={10} className="text-terminal-muted shrink-0" />
                    : <ChevronRight size={10} className="text-terminal-muted shrink-0" />}
                </div>
              </button>

              {expanded === i && (
                <div className="mx-2 mb-2 rounded overflow-hidden border border-terminal-border animate-message">
                  {[['INPUT', step.input], ['OUTPUT', step.output]].map(([label, content]) => (
                    <div key={label}>
                      <div className="px-3 py-1 border-b border-terminal-border text-[10px] font-mono text-terminal-muted bg-black/20">
                        {label}
                      </div>
                      <pre className="px-3 py-2 text-[11px] font-mono text-terminal-text overflow-x-auto whitespace-pre-wrap bg-black/10">
                        {String(content) || '(empty)'}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}