import { Trash2, Clock, X } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function HistorySidebar({ history, selectedId, onSelect, onClear, onRemove, onClose }) {
  return (
    <aside className="flex flex-col h-full w-72 border-r border-terminal-border bg-terminal-surface shrink-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-terminal-border">
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-terminal-accent" />
          <span className="font-display text-sm font-semibold text-terminal-text">History</span>
          <span className="text-[10px] font-mono bg-terminal-border text-terminal-muted px-1.5 py-0.5 rounded">
            {history.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {history.length > 0 && (
            <button
              onClick={onClear}
              className="p-1.5 rounded hover:bg-red-500/10 text-terminal-muted hover:text-red-400 transition-colors"
              title="Clear all"
            >
              <Trash2 size={12} />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-white/5 text-terminal-muted hover:text-terminal-text transition-colors"
          >
            <X size={12} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-terminal-muted">
            <Clock size={24} className="opacity-30" />
            <p className="text-xs font-mono">No runs yet</p>
          </div>
        ) : (
          <ul className="py-2">
            {history.map(run => (
              <li key={run.id} className="group relative">
                <button
                  onClick={() => onSelect(run)}
                  className={`w-full text-left px-4 py-3 transition-colors hover:bg-white/5 ${
                    selectedId === run.id ? 'bg-terminal-accent/5 border-r-2 border-terminal-accent' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <StatusBadge status={run.status} size="sm" />
                    <span className="text-[10px] font-mono text-terminal-muted">{timeAgo(run.timestamp)}</span>
                  </div>
                  <p className="text-xs text-terminal-text line-clamp-2 leading-relaxed">{run.prompt}</p>
                  <div className="flex items-center gap-2 mt-1.5 text-[10px] font-mono text-terminal-muted">
                    <span>{run.total_steps} steps</span>
                    <span>·</span>
                    <span>{(run.duration_ms / 1000).toFixed(1)}s</span>
                  </div>
                </button>
                <button
                  onClick={e => { e.stopPropagation(); onRemove(run.id) }}
                  className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-terminal-muted hover:text-red-400 transition-all"
                >
                  <X size={10} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}