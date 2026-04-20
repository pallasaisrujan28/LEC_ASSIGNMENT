'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { generateId } from '@/lib/utils';
import { runDemoStream } from '@/lib/demo';
import { streamAgent } from '@/lib/sse';
import { AgentEvent, AgentTurn } from '@/types/agent';
import Sidebar from './Sidebar';
import MessageInput from './MessageInput';
import TurnView from './TurnView';
import EmptyState from './EmptyState';
import { Zap } from 'lucide-react';

export default function ChatInterface() {
  const [turns, setTurns] = useState<AgentTurn[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [demoMode, setDemoMode] = useState(true);
  const [threadId, setThreadId] = useState(() => 'thread_' + generateId());
  const [budgetLimit, setBudgetLimit] = useState(20);
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
      const newTurn: AgentTurn = {
        id: turnId,
        query,
        events: [],
        stepStatuses: {},
        isStreaming: true,
      };

      setTurns((prev) => [...prev, newTurn]);
      setIsStreaming(true);

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
        if (demoMode) {
          await runDemoStream(query, onEvent, controller.signal);
        } else {
          await streamAgent(query, budgetLimit, threadId, onEvent, controller.signal);
        }
      } catch (err: unknown) {
        if ((err as Error)?.name !== 'AbortError') {
          appendEvent(turnId, {
            type: 'error',
            data: { message: (err as Error)?.message ?? 'Unknown error' },
          });
        }
      } finally {
        setTurns((prev) =>
          prev.map((t) => (t.id === turnId ? { ...t, isStreaming: false } : t))
        );
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, demoMode, budgetLimit, threadId, appendEvent]
  );

  const stopStreaming = () => {
    abortRef.current?.abort();
  };

  const newConversation = () => {
    abortRef.current?.abort();
    setTurns([]);
    setIsStreaming(false);
    setThreadId('thread_' + generateId());
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#07070f]">
      <Sidebar
        threadId={threadId}
        turnCount={turns.length}
        onNewConversation={newConversation}
        demoMode={demoMode}
        onToggleDemo={() => setDemoMode((d) => !d)}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center justify-between border-b border-white/[0.05] bg-[#07070f]/80 px-6 py-3 backdrop-blur-xl">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            <span className="font-mono text-xs tracking-widest text-[#5a6070] uppercase">
              Plan-and-Execute · LangGraph + Bedrock
            </span>
          </div>
          <div className="flex items-center gap-2">
            {isStreaming && (
              <button
                onClick={stopStreaming}
                className="rounded-md border border-red-500/20 bg-red-500/10 px-3 py-1 font-mono text-xs text-red-400 transition-all hover:bg-red-500/20"
              >
                ■ Stop
              </button>
            )}
            <button
              onClick={newConversation}
              className="rounded-md border border-white/[0.08] bg-white/[0.03] px-3 py-1 font-mono text-xs text-[#5a6070] transition-all hover:border-white/[0.15] hover:text-[#c8cce0]"
            >
              New chat
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-6 py-8">
            <AnimatePresence mode="wait">
              {turns.length === 0 ? (
                <EmptyState key="empty" onPrompt={sendMessage} />
              ) : (
                <motion.div
                  key="turns"
                  className="flex flex-col gap-8"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  {turns.map((turn) => (
                    <TurnView key={turn.id} turn={turn} />
                  ))}
                  {isStreaming && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-2 pl-1"
                    >
                      <div className="flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br from-cyan-500 to-violet-500">
                        <Zap size={10} className="text-white" />
                      </div>
                      <div className="flex gap-1">
                        <span className="h-1.5 w-1.5 animate-dot-1 rounded-full bg-cyan-400" />
                        <span className="h-1.5 w-1.5 animate-dot-2 rounded-full bg-cyan-400" />
                        <span className="h-1.5 w-1.5 animate-dot-3 rounded-full bg-cyan-400" />
                      </div>
                      <span className="font-mono text-xs text-[#5a6070]">Processing…</span>
                    </motion.div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <MessageInput
          onSend={sendMessage}
          isStreaming={isStreaming}
          budgetLimit={budgetLimit}
          onBudgetChange={setBudgetLimit}
        />
      </div>
    </div>
  );
}
