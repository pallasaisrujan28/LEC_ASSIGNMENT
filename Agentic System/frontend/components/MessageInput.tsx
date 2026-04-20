'use client';

import { useRef, useState, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { ArrowUp, DollarSign } from 'lucide-react';

interface MessageInputProps {
  onSend: (query: string) => void;
  isStreaming: boolean;
  budgetLimit: number;
  onBudgetChange: (val: number) => void;
}

export default function MessageInput({
  onSend,
  isStreaming,
  budgetLimit,
  onBudgetChange,
}: MessageInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length > 0 && !isStreaming;

  const handleSend = () => {
    if (!canSend) return;
    onSend(value.trim());
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  };

  return (
    <div className="border-t border-white/[0.05] bg-[#07070f]/90 px-6 py-4 backdrop-blur-xl">
      <div className="mx-auto max-w-3xl">
        {/* Input wrapper */}
        <div
          className={`relative flex items-end gap-3 rounded-2xl border bg-[#0c0c18] px-4 py-3 transition-all duration-200 ${
            isStreaming
              ? 'border-white/[0.05]'
              : 'border-white/[0.08] focus-within:border-cyan-500/30 focus-within:shadow-[0_0_0_3px_rgba(0,229,255,0.06)]'
          }`}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              handleInput();
            }}
            onKeyDown={handleKey}
            disabled={isStreaming}
            placeholder={isStreaming ? 'Agent is working…' : 'Ask a complex question…'}
            rows={1}
            className="max-h-[200px] flex-1 resize-none bg-transparent font-outfit text-sm text-[#e2e4f0] placeholder-[#3d4450] outline-none leading-relaxed disabled:cursor-not-allowed disabled:opacity-50"
            style={{ height: 'auto' }}
          />

          {/* Send button */}
          <motion.button
            onClick={handleSend}
            disabled={!canSend}
            whileTap={{ scale: 0.92 }}
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-all duration-200 ${
              canSend
                ? 'bg-cyan-400 text-[#07070f] hover:bg-white shadow-[0_0_16px_rgba(0,229,255,0.3)]'
                : 'bg-[#16162a] text-[#3d4450] cursor-not-allowed'
            }`}
          >
            <ArrowUp size={15} strokeWidth={2.5} />
          </motion.button>
        </div>

        {/* Footer row */}
        <div className="mt-2 flex items-center justify-between px-1">
          <p className="font-mono text-[10px] text-[#2a2d3a]">
            ↵ send · shift+↵ newline
          </p>

          <div className="flex items-center gap-1.5">
            <DollarSign size={10} className="text-[#3d4450]" />
            <span className="font-mono text-[10px] text-[#3d4450]">budget</span>
            <input
              type="number"
              value={budgetLimit}
              onChange={(e) => onBudgetChange(Number(e.target.value))}
              min={0.1}
              max={100}
              step={0.1}
              className="w-12 rounded border border-white/[0.06] bg-[#0c0c18] px-1.5 py-0.5 text-right font-mono text-[10px] text-[#5a6070] outline-none focus:border-white/[0.12] transition-colors"
            />
            <span className="font-mono text-[10px] text-[#3d4450]">USD</span>
          </div>
        </div>
      </div>
    </div>
  );
}
