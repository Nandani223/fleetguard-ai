import { useState, useRef, useEffect } from 'react'
import { MessageCircle, Send, X, Wrench, ChevronRight, Sparkles } from 'lucide-react'
import { chatWithAgent } from '../api/client'

function ToolCallChip({ call }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-brand-dim font-medium hover:text-brand transition-colors"
      >
        <Wrench size={11} />
        {call.tool}
        <ChevronRight size={11} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <pre className="mt-1 p-2 rounded-md bg-surface-sunken border border-line text-[11px] text-ink-dim overflow-x-auto max-w-full">
          {JSON.stringify(call.result, null, 2)}
        </pre>
      )}
    </div>
  )
}

function Message({ role, content, toolCalls }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-brand text-white rounded-br-md'
              : 'bg-surface-sunken text-ink rounded-bl-md'
          }`}
        >
          {content}
        </div>
        {toolCalls && toolCalls.length > 0 && (
          <div className="px-1">
            {toolCalls.map((call, i) => (
              <ToolCallChip key={i} call={call} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const [collapsed, setCollapsed] = useState(false)
  const [messages, setMessages] = useState([])
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setSending(true)
    try {
      const res = await chatWithAgent(text, history)
      setHistory(res.conversation_history)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, toolCalls: res.tool_calls }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: `Something went wrong: ${err.message}` }])
    } finally {
      setSending(false)
    }
  }

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="fixed bottom-6 right-6 w-13 h-13 px-4 py-3 rounded-full bg-brand text-white flex items-center gap-2 shadow-pop hover:brightness-110 transition-all z-20 text-sm font-semibold"
        aria-label="Open Insight Agent chat"
      >
        <MessageCircle size={18} />
        Ask FleetGuard
      </button>
    )
  }

  return (
    <aside className="w-96 shrink-0 border-l border-line bg-surface flex flex-col h-full">
      <div className="h-16 shrink-0 border-b border-line flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-soft flex items-center justify-center">
            <Sparkles size={14} className="text-brand-dim" />
          </div>
          <span className="font-semibold text-sm text-ink">Insight Agent</span>
        </div>
        <button
          onClick={() => setCollapsed(true)}
          className="text-ink-faint hover:text-ink transition-colors"
          aria-label="Collapse chat panel"
        >
          <X size={16} />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-sm text-ink-dim leading-relaxed">
            Ask about fleet risk, RUL, or signal correlations — answers are grounded in live
            backend data, and every tool call used is shown under the reply.
            <div className="mt-3 space-y-1.5">
              {[
                'Which vehicles are red-tier this week?',
                "What's the RUL for VIN ...?",
                'Compare the Alternator and Brake Pads',
              ].map((ex) => (
                <button
                  key={ex}
                  onClick={() => setInput(ex)}
                  className="block w-full text-left text-xs px-3 py-2 rounded-lg border border-line hover:border-brand/40 hover:bg-brand-soft hover:text-brand-dim text-ink-dim transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} role={m.role} content={m.content} toolCalls={m.toolCalls} />
        ))}
        {sending && (
          <div className="flex items-center gap-2 text-ink-faint text-xs px-1">
            <span className="w-2 h-2 rounded-full bg-brand animate-pulse" />
            thinking…
          </div>
        )}
      </div>

      <div className="p-3 border-t border-line">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about fleet risk…"
            className="flex-1 bg-surface-sunken border border-line rounded-lg px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-brand"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="w-10 h-10 shrink-0 rounded-lg bg-brand text-white flex items-center justify-center disabled:opacity-40 hover:brightness-110 transition-all"
            aria-label="Send message"
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </aside>
  )
}
