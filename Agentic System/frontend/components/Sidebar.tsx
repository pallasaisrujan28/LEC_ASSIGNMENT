'use client';

import { motion } from 'framer-motion';
import { Plus, MessageSquare, Settings, BookOpen, Zap, ToggleLeft, ToggleRight } from 'lucide-react';

interface SidebarProps {
  threadId: string;
  turnCount: number;
  onNewConversation: () => void;
  demoMode: boolean;
  onToggleDemo: () => void;
}

export default function Sidebar({
  threadId,
  turnCount,
  onNewConversation,
  demoMode,
  onToggleDemo,
}: SidebarProps) {
  const shortThread = threadId.replace('thread_', '');

  return (
    <aside className="flex w-[240px] shrink-0 flex-col border-r border-white/[0.05] bg-[#0c0c18]">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-white/[0.05] px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-violet-500 shadow-lg">
          <Zap size={15} className="text-white" />
        </div>
        <div className="font-syne text-[15px] font-800 tracking-tight text-[#e2e4f0]">
          Agent<span className="text-cyan-400">Core</span>
        </div>
      </div>

      {/* New chat */}
      <div className="p-3">
        <button
          onClick={onNewConversation}
          className="group flex w-full items-center gap-2 rounded-lg border border-cyan-500/20 bg-cyan-500/[0.07] px-3 py-2.5 text-sm font-medium text-cyan-400 transition-all hover:border-cyan-500/40 hover:bg-cyan-500/[0.12]"
        >
          <Plus size={15} />
          <span className="font-outfit">New conversation</span>
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-3">
        <p className="mb-2 px-1 font-mono text-[10px] uppercase tracking-[1.5px] text-[#2a2d3a]">
          Recent
        </p>

        {turnCount > 0 ? (
          <motion.div
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2 rounded-lg border-l-2 border-cyan-400 bg-[#111120] px-2.5 py-2 cursor-default"
          >
            <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#00e5ff]" />
            <MessageSquare size={12} className="text-[#5a6070]" />
            <span className="truncate font-outfit text-[12px] text-[#8890a8]">
              Active session
            </span>
          </motion.div>
        ) : (
          <p className="px-1 font-mono text-[11px] text-[#2a2d3a]">No history yet</p>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-white/[0.05] p-3 flex flex-col gap-1">
        {/* Demo toggle */}
        <button
          onClick={onToggleDemo}
          className="flex w-full items-center justify-between rounded-lg px-2.5 py-2 transition-all hover:bg-white/[0.03]"
        >
          <div className="flex items-center gap-2">
            {demoMode ? (
              <ToggleRight size={14} className="text-amber-400" />
            ) : (
              <ToggleLeft size={14} className="text-[#5a6070]" />
            )}
            <span className="font-mono text-[11px] text-[#5a6070]">Demo mode</span>
          </div>
          <span
            className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
              demoMode
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                : 'bg-white/[0.03] text-[#2a2d3a] border border-white/[0.05]'
            }`}
          >
            {demoMode ? 'ON' : 'OFF'}
          </span>
        </button>

        {/* Settings */}
        <button className="flex items-center gap-2 rounded-lg px-2.5 py-2 transition-all hover:bg-white/[0.03]">
          <Settings size={13} className="text-[#5a6070]" />
          <span className="font-mono text-[11px] text-[#5a6070]">Settings</span>
        </button>

        <button className="flex items-center gap-2 rounded-lg px-2.5 py-2 transition-all hover:bg-white/[0.03]">
          <BookOpen size={13} className="text-[#5a6070]" />
          <span className="font-mono text-[11px] text-[#5a6070]">Docs</span>
        </button>

        {/* Thread ID pill */}
        <div className="mt-1 flex items-center gap-1.5 rounded-lg border border-white/[0.04] bg-white/[0.02] px-2.5 py-1.5">
          <span className="font-mono text-[9px] text-[#2a2d3a]">thread</span>
          <span className="font-mono text-[9px] text-[#3d4450] truncate">{shortThread}</span>
        </div>
      </div>
    </aside>
  );
}
