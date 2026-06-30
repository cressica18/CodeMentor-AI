import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Terminal } from 'lucide-react'
import { chatApi, type ChatMessage } from '@/utils/api'
import { cn } from '@/utils/cn'

interface Message extends ChatMessage {
  id: string
  trace?: Array<Record<string, unknown>>
}

const SESSION_ID = `session-${Date.now()}`

export default function ChatPage() {
  const [handle, setHandle] = useState('')
  const [handleConfirmed, setHandleConfirmed] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showTrace, setShowTrace] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function addMessage(msg: Omit<Message, 'id'>) {
    setMessages((prev) => [...prev, { ...msg, id: crypto.randomUUID() }])
  }

  async function handleSend() {
    if (!input.trim() || loading) return
    const userText = input.trim()
    setInput('')
    addMessage({ role: 'user', content: userText })
    setLoading(true)
    try {
      const { data } = await chatApi.send({
        session_id: SESSION_ID,
        cf_handle: handle,
        message: userText,
      })
      addMessage({ role: 'assistant', content: data.message.content, trace: data.agent_trace })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Request failed'
      addMessage({ role: 'assistant', content: `Error: ${msg}` })
    } finally {
      setLoading(false)
    }
  }

  if (!handleConfirmed) {
    return (
      <div className="h-screen flex items-center justify-center p-8">
        <div className="card p-8 w-full max-w-md">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center mb-5">
            <Bot size={20} className="text-white" />
          </div>
          <h2 className="text-lg font-semibold text-white mb-1">Welcome to CodeMentor AI</h2>
          <p className="text-sm text-gray-400 mb-6">Enter your Codeforces handle to begin.</p>
          <input
            className="input w-full mb-4"
            placeholder="e.g. tourist"
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handle.trim() && setHandleConfirmed(true)}
          />
          <button
            className="btn-primary w-full"
            disabled={!handle.trim()}
            onClick={() => setHandleConfirmed(true)}
          >
            Start Session
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#2a2a3a] bg-[#16161d]">
        <div className="flex items-center gap-3">
          <Bot size={18} className="text-brand-400" />
          <span className="text-sm font-medium text-white">CodeMentor Chat</span>
          <span className="badge badge-purple">{handle}</span>
        </div>
        <button
          onClick={() => setShowTrace((v) => !v)}
          className={cn('flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors',
            showTrace ? 'bg-brand-600/20 text-brand-400' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5')}
        >
          <Terminal size={13} /> Agent trace
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-600 mt-20 text-sm">
              Send a message to start your session.
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={cn('flex gap-3', m.role === 'user' && 'flex-row-reverse')}>
              <div className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5',
                m.role === 'user' ? 'bg-brand-600' : 'bg-[#2a2a3a]'
              )}>
                {m.role === 'user' ? <User size={13} className="text-white" /> : <Bot size={13} className="text-brand-400" />}
              </div>
              <div className={cn(
                'max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
                m.role === 'user'
                  ? 'bg-brand-600 text-white rounded-tr-sm'
                  : 'bg-[#1c1c26] text-gray-200 rounded-tl-sm border border-[#2a2a3a]'
              )}>
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-[#2a2a3a] flex items-center justify-center">
                <Bot size={13} className="text-brand-400" />
              </div>
              <div className="bg-[#1c1c26] border border-[#2a2a3a] rounded-2xl rounded-tl-sm px-4 py-2.5">
                <Loader2 size={14} className="text-gray-500 animate-spin" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Trace panel */}
        {showTrace && (
          <div className="w-72 border-l border-[#2a2a3a] bg-[#16161d] overflow-y-auto p-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-widest mb-3">Agent Trace</p>
            {messages.filter((m) => m.trace).map((m) => (
              <div key={m.id} className="mb-3">
                {m.trace?.map((step, i) => (
                  <div key={i} className="text-xs text-gray-400 bg-[#1c1c26] rounded-lg p-2 mb-1 font-mono border border-[#2a2a3a]">
                    {JSON.stringify(step, null, 2)}
                  </div>
                ))}
              </div>
            ))}
            {messages.every((m) => !m.trace) && (
              <p className="text-xs text-gray-700">No trace data yet.</p>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-[#2a2a3a] bg-[#16161d]">
        <div className="flex gap-3">
          <input
            className="input flex-1"
            placeholder="Ask CodeMentor anything…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={loading}
          />
          <button
            className="btn-primary flex items-center gap-2"
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
