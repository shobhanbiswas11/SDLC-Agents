import { User, Bot, RefreshCw, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { StatusBadge } from './StatusBadge'
import { StepTrace } from './StepTrace'

function parseMarkdown(content) {
  const parts = []
  let lastIndex = 0
  // Updated regex: matches language tags with hyphens, dots, etc. (docker-compose, terraform, etc)
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g
  let match
  let codeBlockCount = 0

  while ((match = codeBlockRegex.exec(content)) !== null) {
    codeBlockCount++
    console.log(`[parseMarkdown] Found code block #${codeBlockCount}: language="${match[1]}", length=${match[2].length}`)
    
    // Add text before code block
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex, match.index),
      })
    }

    // Add code block
    parts.push({
      type: 'code',
      language: match[1] || 'plaintext',
      content: match[2].trim(),
    })

    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.slice(lastIndex),
    })
  }

  console.log(`[parseMarkdown] Total parts: ${parts.length}, Code blocks: ${codeBlockCount}`)
  return parts.length > 0 ? parts : [{ type: 'text', content }]
}

function CodeBlock({ language, content }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-4 bg-gray-100 border border-gray-300 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-gray-200 border-b border-gray-300">
        <span className="text-sm font-semibold text-gray-800">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium text-gray-700 hover:bg-gray-300 transition-all"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check size={14} />
              Copied
            </>
          ) : (
            <>
              <Copy size={14} />
              Copy
            </>
          )}
        </button>
      </div>
      <pre className="px-4 py-4 overflow-x-auto text-sm font-mono text-black leading-relaxed">
        <code>{content}</code>
      </pre>
    </div>
  )
}

export function ChatMessage({ message, onFix }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="flex items-start gap-3 max-w-2xl">
          <div className="bg-black text-white rounded-xl rounded-tr-sm px-5 py-4">
            <p className="text-base leading-relaxed">{message.content}</p>
          </div>
          <div className="shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center mt-0.5">
            <User size={16} className="text-black" />
          </div>
        </div>
      </div>
    )
  }

  if (message.isLoading) {
    return (
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center mt-0.5">
          <Bot size={16} className="text-black" />
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-xl rounded-tl-sm px-5 py-4">
          <div className="flex items-center gap-2">
            {[0, 1, 2].map(i => (
              <span
                key={i}
                className="w-2 h-2 rounded-full bg-gray-400"
                style={{ animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }}
              />
            ))}
            <span className="text-sm text-gray-600">
              thinking...
            </span>
          </div>
        </div>
      </div>
    )
  }

  const isFail = message.run?.status === 'FAIL'
  const parsedContent = parseMarkdown(message.content)

  return (
    <div className="flex items-start gap-3">
      <div className="shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center mt-0.5">
        <Bot size={16} className="text-black" />
      </div>
      <div className="flex-1 min-w-0 bg-gray-50 border border-gray-200 rounded-xl rounded-tl-sm px-5 py-4">
        {message.run && (
          <div className="flex items-center gap-3 mb-4 pb-4 border-b border-gray-200">
            <StatusBadge status={message.run.status} />
            <span className="text-xs text-gray-500 font-medium">
              {new Date(message.run.timestamp).toLocaleTimeString()}
            </span>
          </div>
        )}

        <div className="text-base text-black leading-relaxed">
          {parsedContent.map((part, idx) =>
            part.type === 'code' ? (
              <CodeBlock key={idx} language={part.language} content={part.content} />
            ) : (
              <div key={idx} className="whitespace-pre-wrap">
                {part.content}
              </div>
            )
          )}
        </div>

        {message.run?.steps?.length > 0 && (
          <StepTrace steps={message.run.steps} duration_ms={message.run.duration_ms} />
        )}

        {/* Fix button — only show on FAIL messages */}
        {isFail && onFix && !message.fixed && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600 mb-3">
              Policy checks failed. Want to auto-fix the violations?
            </p>
            <button
              onClick={() => onFix(message)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-black text-white hover:bg-gray-800 transition-all"
            >
              <RefreshCw size={14} />
              Regenerate & Fix IaC
            </button>
          </div>
        )}
      </div>
    </div>
  )
}