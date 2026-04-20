'use client';

import { motion } from 'framer-motion';
import { RefreshCw } from 'lucide-react';

interface ReflectingNoteProps {
  feedback: string;
}

export default function ReflectingNote({ feedback }: ReflectingNoteProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start gap-2.5 rounded-lg border border-amber-500/15 bg-amber-500/[0.06] px-3.5 py-2.5"
    >
      <RefreshCw
        size={12}
        className="mt-0.5 shrink-0 text-amber-400 animate-spin [animation-duration:2s]"
      />
      <p className="font-mono text-[11px] text-amber-400/80">
        Re-planning:{' '}
        <span className="text-amber-400">{feedback}</span>
      </p>
    </motion.div>
  );
}
