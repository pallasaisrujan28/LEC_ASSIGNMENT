'use client';

import { Plus } from 'lucide-react';

interface SidebarProps {
  turnCount: number;
  onNewConversation: () => void;
}

export default function Sidebar({ turnCount, onNewConversation }: SidebarProps) {
  return (
    <aside className="flex w-[220px] shrink-0 flex-col border-r border-white/[0.05] bg-[#141412]">
      {/* Logo */}
      <div className="flex items-center justify-center border-b border-white/[0.05] px-5 py-5">
        <img src="/lec-logo.png" alt="LEC" className="h-10 w-auto object-contain brightness-110" />
      </div>

      {/* New chat */}
      <div className="p-3">
        <button
          onClick={onNewConversation}
          className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-[#c0b8a8] transition-all hover:bg-white/[0.04]"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#2a2824]">
            <Plus size={16} className="text-[#8a8478]" />
          </div>
          <span className="font-outfit text-[15px]">New chat</span>
        </button>
      </div>

      {/* Session info */}
      <div className="flex-1 overflow-y-auto px-3">
        {turnCount > 0 && (
          <div className="flex items-center gap-2 rounded-lg bg-[#1a1814] px-2.5 py-2">
            <div className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            <span className="font-outfit text-[12px] text-[#8a8478]">
              {turnCount} {turnCount === 1 ? 'query' : 'queries'}
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}
