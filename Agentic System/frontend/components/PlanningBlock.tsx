'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import { PlanningEventData, StepStatus } from '@/types/agent';

interface PlanningBlockProps {
  data: PlanningEventData;
  stepStatuses: Record<string, StepStatus>;
}

const STATUS_ICON: Record<StepStatus, string> = {
  pending: '○',
  running: '◎',
  success: '✓',
  failed: '✗',
};

export default function PlanningBlock({ data, stepStatuses }: PlanningBlockProps) {
  const [open, setOpen] = useState(false);

  const completedCount = Object.values(stepStatuses).filter(
    (s) => s === 'success' || s === 'failed'
  ).length;
  const totalCount = data.steps.length;
  const label = totalCount > 0
    ? `Planned ${totalCount} step${totalCount !== 1 ? 's' : ''}, executed ${completedCount}`
    : data.thought;

  return (
    <div className="my-1">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[13px] text-[#7a7568] hover:text-[#a09888] transition-colors"
      >
        <ChevronRight
          size={14}
          className={`transition-transform duration-150 ${open ? 'rotate-90' : ''}`}
        />
        <span className="italic">{label}</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="ml-5 mt-2 flex flex-col gap-1.5">
              <p className="text-[12px] text-[#5a5548] italic">{data.thought}</p>
              {data.steps.map((step, idx) => {
                const status = stepStatuses[step.step_id] ?? 'pending';
                return (
                  <div key={step.step_id} className="flex items-start gap-2 text-[12px]">
                    <span className={`mt-0.5 ${status === 'success' ? 'text-emerald-500' : status === 'failed' ? 'text-red-400' : 'text-[#5a5548]'}`}>
                      {STATUS_ICON[status]}
                    </span>
                    <div>
                      <span className="text-[#8a8478] font-mono">{step.tool}</span>
                      <span className="text-[#5a5548]"> — {step.reason}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
