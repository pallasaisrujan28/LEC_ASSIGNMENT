'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ClipboardList } from 'lucide-react';
import { PlanningEventData, StepStatus } from '@/types/agent';
import { getToolColors } from '@/lib/utils';

interface PlanningBlockProps {
  data: PlanningEventData;
  stepStatuses: Record<string, StepStatus>;
}

const STATUS_ICON: Record<StepStatus, string> = {
  pending: '⏳',
  running: '⚙️',
  success: '✅',
  failed:  '❌',
};

const STATUS_BORDER: Record<StepStatus, string> = {
  pending: 'border-white/[0.06]',
  running: 'border-amber-500/40',
  success: 'border-emerald-500/40',
  failed:  'border-red-500/40',
};

export default function PlanningBlock({ data, stepStatuses }: PlanningBlockProps) {
  const [open, setOpen] = useState(true);

  const completedCount = Object.values(stepStatuses).filter(
    (s) => s === 'success' || s === 'failed'
  ).length;
  const totalCount = data.steps.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-xl border border-white/[0.06] bg-[#141210]"
    >
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.02]"
      >
        <ClipboardList size={14} className="mt-0.5 shrink-0 text-amber-400" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-medium text-amber-400 uppercase tracking-wide">
              Plan · {data.steps.length} step{data.steps.length !== 1 ? 's' : ''}
            </span>
            {totalCount > 0 && (
              <span className="font-mono text-[10px] text-[#3d4450]">
                {completedCount}/{totalCount} done
              </span>
            )}
          </div>
          <p className="mt-0.5 truncate font-outfit text-xs italic text-[#5a6070]">
            {data.thought}
          </p>
        </div>
        <ChevronDown
          size={14}
          className={`mt-0.5 shrink-0 text-[#3d4450] transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Steps */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="overflow-hidden border-t border-white/[0.04]"
          >
            <div className="flex flex-col gap-1.5 p-3">
              {data.steps.map((step, idx) => {
                const status = stepStatuses[step.step_id] ?? 'pending';
                const colors = getToolColors(step.tool);
                const isParallel = step.depends_on.length === 0 && idx > 0;

                return (
                  <motion.div
                    key={step.step_id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.07, duration: 0.25 }}
                    className={`rounded-lg border bg-[#0d0d0b] px-3 py-2.5 transition-colors ${STATUS_BORDER[status]}`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[9px] text-[#2a2d3a] w-4">
                        {String(idx + 1).padStart(2, '0')}
                      </span>
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-medium border ${colors.bg} ${colors.text} ${colors.border}`}
                      >
                        {step.tool}
                      </span>
                      {isParallel && (
                        <span className="rounded border border-amber-500/20 bg-amber-500/[0.08] px-1.5 py-0.5 font-mono text-[9px] text-amber-400">
                          ∥ parallel
                        </span>
                      )}
                      <span className="ml-auto text-[13px]">{STATUS_ICON[status]}</span>
                    </div>
                    {step.reason && (
                      <p className="mt-1.5 pl-6 font-outfit text-[11px] italic text-[#3d4450]">
                        {step.reason}
                      </p>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
