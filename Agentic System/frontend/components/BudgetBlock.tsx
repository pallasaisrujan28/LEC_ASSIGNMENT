'use client';

import { motion } from 'framer-motion';
import { BudgetEventData } from '@/types/agent';
import { formatCost, formatNumber } from '@/lib/utils';
import { AlertCircle, RefreshCw, Coins } from 'lucide-react';

/* ── Budget ── */
interface BudgetBlockProps {
  data: BudgetEventData;
}

export function BudgetBlock({ data }: BudgetBlockProps) {
  const pct = ((data.total_cost_usd / data.max_budget_usd) * 100).toFixed(1);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-wrap items-center gap-3 rounded-lg border border-white/[0.04] bg-[#07070f] px-4 py-2.5"
    >
      <div className="flex items-center gap-1.5">
        <Coins size={11} className="text-[#3d4450]" />
        <span className="font-mono text-[10px] text-[#3d4450]">Cost</span>
      </div>

      <Divider />

      <Stat label="in" value={formatNumber(data.total_input_tokens) + ' tok'} />
      <Divider />
      <Stat label="out" value={formatNumber(data.total_output_tokens) + ' tok'} />
      <Divider />
      <Stat label="calls" value={String(data.calls)} />
      <Divider />
      <Stat
        label="cost"
        value={formatCost(data.total_cost_usd)}
        accent
      />
      <span className="font-mono text-[10px] text-[#2a2d3a]">
        ({pct}% of ${data.max_budget_usd} budget)
      </span>
    </motion.div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <span className="flex items-center gap-1">
      <span className="font-mono text-[10px] text-[#2a2d3a]">{label}</span>
      <span className={`font-mono text-[10px] ${accent ? 'text-cyan-400' : 'text-[#5a6070]'}`}>
        {value}
      </span>
    </span>
  );
}

function Divider() {
  return <span className="font-mono text-[10px] text-[#1a1a28]">·</span>;
}

/* ── Reflecting ── */
interface ReflectingNoteProps {
  feedback: string;
}

export function ReflectingNote({ feedback }: ReflectingNoteProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start gap-2.5 rounded-lg border border-amber-500/15 bg-amber-500/[0.06] px-3.5 py-2.5"
    >
      <RefreshCw size={12} className="mt-0.5 shrink-0 text-amber-400 animate-spin [animation-duration:2s]" />
      <p className="font-mono text-[11px] text-amber-400/80">
        Re-planning: <span className="text-amber-400">{feedback}</span>
      </p>
    </motion.div>
  );
}

/* ── Error ── */
interface ErrorBlockProps {
  message: string;
}

export function ErrorBlock({ message }: ErrorBlockProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-2.5 rounded-xl border border-red-500/20 bg-red-500/[0.07] px-4 py-3"
    >
      <AlertCircle size={14} className="mt-0.5 shrink-0 text-red-400" />
      <p className="font-outfit text-sm text-red-400">{message}</p>
    </motion.div>
  );
}

export default BudgetBlock;
