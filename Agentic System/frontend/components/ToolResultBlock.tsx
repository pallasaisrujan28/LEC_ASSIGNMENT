'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, Link } from 'lucide-react';
import { ToolResultEventData } from '@/types/agent';
import { getToolColors } from '@/lib/utils';

interface ToolResultBlockProps {
  data: ToolResultEventData;
}

interface ResultWithSources {
  text?: string;
  sources?: { url: string }[];
}

export default function ToolResultBlock({ data }: ToolResultBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const colors = getToolColors(data.tool);

  const raw = data.result ?? data.error ?? '';
  const hasSourcesResult = typeof raw === 'object' && raw !== null && 'sources' in (raw as object);
  const resultWithSources = hasSourcesResult ? (raw as ResultWithSources) : null;
  const resultText = resultWithSources
    ? (resultWithSources.text ?? '')
    : typeof raw === 'string'
    ? raw
    : JSON.stringify(raw, null, 2);
  const sources = resultWithSources?.sources ?? [];

  const preview = resultText.length > 120 ? resultText.slice(0, 120) + '…' : resultText;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-xl border border-white/[0.05] bg-[#0c0c18]"
    >
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left transition-colors hover:bg-white/[0.02]"
      >
        <span className="text-sm">{data.success ? '✅' : '❌'}</span>
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-medium border ${colors.bg} ${colors.text} ${colors.border}`}
        >
          {data.tool}
        </span>
        <span className="flex-1 truncate font-mono text-[11px] text-[#3d4450]">
          {data.success ? preview : (data.error ?? 'Failed')}
        </span>
        <ChevronDown
          size={13}
          className={`shrink-0 text-[#3d4450] transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {expanded && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="border-t border-white/[0.04]"
        >
          {/* Source URLs for web_search */}
          {sources.length > 0 && (
            <div className="flex flex-col gap-1 border-b border-white/[0.04] px-4 py-2">
              {sources.map((s) => (
                <a
                  key={s.url}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 truncate font-mono text-[11px] text-blue-400 transition-colors hover:text-cyan-400"
                >
                  <Link size={10} />
                  {s.url}
                </a>
              ))}
            </div>
          )}

          {/* Result text */}
          <div className="px-4 py-3">
            <pre
              className={`whitespace-pre-wrap break-words font-mono text-[11.5px] leading-relaxed ${
                data.success ? 'text-[#5a6070]' : 'text-red-400'
              }`}
            >
              {data.success ? resultText : data.error}
            </pre>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
