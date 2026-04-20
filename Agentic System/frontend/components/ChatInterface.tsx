'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { generateId } from '@/lib/utils';
import { streamAgent } from '@/lib/sse';
import { AgentEvent, AgentTurn } from '@/types/agent';
import Sidebar from './Sidebar';
import TurnView from './TurnView';
import { Send } from 'lucide-react';

export default function ChatInterface() {
  const [turns, setTurns] = useState<AgentTurn[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [threadId, setThreadId] = useState(() => 'thread_' + generateId());
  const [input, setInput] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  const appendEvent = useCallback((turnId: string, event: AgentEvent) => {
    setTurns((prev) =>
      prev.map((t) => {
        if (t.id !== turnId) return t;
        const updated = { ...t, events: [...t.events, event] };
        if (event.type === 'tool_result') {
          updated.stepStatuses = {
            ...t.stepStatuses,
            [event.data.step_id]: event.data.success ? 'success' : 'failed',
          };
        }
        return updated;
      })
    );
  }, []);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isStreaming) return;
      const turnId = generateId();
      setTurns((prev) => [...prev, { id: turnId, query, events: [], stepStatuses: {}, isStreaming: true }]);
      setIsStreaming(true);
      setInput('');
      const controller = new AbortController();
      abortRef.current = controller;

      const onEvent = (eventType: string, data: unknown) => {
        appendEvent(turnId, { type: eventType, data } as AgentEvent);
        if (eventType === 'planning' && (data as { steps?: unknown[] }).steps) {
          const steps = (data as { steps: { step_id: string }[] }).steps;
          setTurns((prev) =>
            prev.map((t) => {
              if (t.id !== turnId) return t;
              const statuses: Record<string, 'pending' | 'running' | 'success' | 'failed'> = {};
              steps.forEach((s) => (statuses[s.step_id] = 'pending'));
              return { ...t, stepStatuses: statuses };
            })
          );
        }
      };
      try {
        await streamAgent(query, 20, threadId, onEvent, controller.signal);
      } catch (err: unknown) {
        if ((err as Error)?.name !== 'AbortError') {
          appendEvent(turnId, { type: 'error', data: { message: (err as Error)?.message ?? 'Unknown error' } });
        }
      } finally {
        setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, isStreaming: false } : t)));
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, threadId, appendEvent]
  );

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); sendMessage(input); };
  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } };
  const newConversation = () => { abortRef.current?.abort(); setTurns([]); setIsStreaming(false); setThreadId('thread_' + generateId()); };

  const hasMessages = turns.length > 0;

  return (
    <div className="flex h-screen overflow-hidden bg-[#1a1a18]">
      <Sidebar turnCount={turns.length} onNewConversation={newConversation} />

      <div className="flex flex-1 flex-col overflow-hidden">
        {!hasMessages ? (
          <div className="flex flex-1 flex-col items-center justify-center px-6">
            <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="font-syne text-3xl font-bold text-[#e8e4dc] mb-8">
              Hello, LEC Team
            </motion.h1>
            <motion.form initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} onSubmit={handleSubmit} className="w-full max-w-2xl">
              <div className="relative rounded-2xl border border-white/[0.08] bg-[#252520] shadow-lg">
                <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="How can I help you today?" rows={2} className="w-full resize-none bg-transparent px-5 py-4 pr-14 text-[15px] text-[#e8e4dc] placeholder-[#5a5548] outline-none" />
                <button type="submit" disabled={!input.trim() || isStreaming} className="absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-lg bg-amber-600 text-white transition-all hover:bg-amber-500 disabled:opacity-30 disabled:cursor-not-allowed">
                  <Send size={16} />
                </button>
              </div>
            </motion.form>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="mx-auto max-w-3xl px-6 py-6">
                <AnimatePresence>
                  <motion.div className="flex flex-col gap-6">
                    {turns.map((turn) => (<TurnView key={turn.id} turn={turn} />))}
                    {isStreaming && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 pl-1">
                        <div className="flex gap-1">
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-amber-400" style={{ animationDelay: '0ms' }} />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-amber-400" style={{ animationDelay: '150ms' }} />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-amber-400" style={{ animationDelay: '300ms' }} />
                        </div>
                        <span className="font-mono text-xs text-[#5a5548]">Thinking…</span>
                      </motion.div>
                    )}
                  </motion.div>
                </AnimatePresence>
                <div ref={bottomRef} />
              </div>
            </div>
            <div className="border-t border-white/[0.04] px-6 py-4">
              <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
                <div className="relative rounded-2xl border border-white/[0.08] bg-[#252520]">
                  <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask a follow-up question..." rows={1} className="w-full resize-none bg-transparent px-5 py-3 pr-14 text-[15px] text-[#e8e4dc] placeholder-[#5a5548] outline-none" />
                  <button type="submit" disabled={!input.trim() || isStreaming} className="absolute bottom-2 right-3 flex h-8 w-8 items-center justify-center rounded-lg bg-amber-600 text-white transition-all hover:bg-amber-500 disabled:opacity-30 disabled:cursor-not-allowed">
                    <Send size={14} />
                  </button>
                </div>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
