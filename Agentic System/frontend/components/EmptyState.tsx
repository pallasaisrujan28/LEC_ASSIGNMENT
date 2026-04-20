'use client';

import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';

const EXAMPLES = [
  'What is the population of Japan and what is 3% of it?',
  'What is the GDP of Germany divided by its population?',
  'Search for the latest AI news and summarize the Transformer architecture.',
  'What is the area of Australia vs India? How many times bigger?',
];

interface EmptyStateProps {
  onPrompt: (query: string) => void;
}

const container = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } };
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

export default function EmptyState({ onPrompt }: EmptyStateProps) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-20 text-center"
      variants={container}
      initial="hidden"
      animate="show"
    >
      <motion.div variants={item} className="mb-6">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-500/10 to-orange-500/10">
          <Brain size={28} className="text-amber-400" />
        </div>
      </motion.div>

      <motion.h1 variants={item} className="font-syne text-2xl font-bold tracking-tight text-[#f0ece4]">
        Agentic System
      </motion.h1>
      <motion.p variants={item} className="mt-2 max-w-sm font-outfit text-sm text-[#5a5548] leading-relaxed">
        Ask a complex, multi-step question. Watch the agent plan, call tools, and reason — live.
      </motion.p>

      <motion.div variants={item} className="mt-8 grid grid-cols-2 gap-2.5 w-full max-w-lg">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => onPrompt(ex)}
            className="rounded-xl border border-white/[0.06] bg-[#141210] p-3.5 text-left font-outfit text-[12.5px] text-[#5a5548] leading-snug transition-all hover:border-amber-500/20 hover:bg-[#1a1814] hover:text-[#8a8478]"
          >
            {ex}
          </button>
        ))}
      </motion.div>
    </motion.div>
  );
}
