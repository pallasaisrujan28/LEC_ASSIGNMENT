'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Sparkles } from 'lucide-react';

interface AnswerBlockProps {
  markdown: string;
}

export default function AnswerBlock({ markdown }: AnswerBlockProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="relative overflow-hidden rounded-xl border border-cyan-500/20 bg-[#0c0c18] shadow-[0_0_32px_rgba(0,229,255,0.08)]"
    >
      {/* Gradient top border accent */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.04] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Sparkles size={12} className="text-cyan-400" />
          <span className="font-mono text-[10px] uppercase tracking-[1.5px] text-cyan-400">
            Answer
          </span>
        </div>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 rounded-md border border-white/[0.06] bg-white/[0.03] px-2.5 py-1 font-mono text-[10px] text-[#5a6070] transition-all hover:border-white/[0.12] hover:text-[#8890a8]"
        >
          {copied ? (
            <>
              <Check size={10} className="text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy size={10} />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Markdown content */}
      <div className="px-5 py-4">
        <div className="answer-md">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        </div>
      </div>
    </motion.div>
  );
}
