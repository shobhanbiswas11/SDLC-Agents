export function StatusBadge({ status, size = 'md' }) {
  const config = {
    PASS: { color: '#10b981', label: 'PASS', bg: '#ecfdf5' },
    FAIL: { color: '#ef4444', label: 'FAIL', bg: '#fef2f2' },
    UNKNOWN: { color: '#f59e0b', label: '???', bg: '#fffbeb' },
  }[status] || { color: '#f59e0b', label: '???', bg: '#fffbeb' }

  const padding = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-semibold ${padding}`}
      style={{
        color: config.color,
        background: config.bg,
        border: `1.5px solid ${config.color}`,
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: config.color }} />
      {config.label}
    </span>
  )
}
