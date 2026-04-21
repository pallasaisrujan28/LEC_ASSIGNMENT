'use client';

import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { ToolResultEventData } from '@/types/agent';

interface ToolResultBlockProps {
  data: ToolResultEventData;
}

export default function ToolResultBlock({ data }: ToolResultBlockProps) {
  const [open, setOpen] = useState(false);

  const statusIcon = data.success ? '✓' : '✗';
  const statusColor = data.success ? 'text-emerald-500' : 'text-red-400';
  const preview = data.success
    ? typeof data.result === 'string'
      ? data.result.slice(0, 80)
      : JSON.stringify(data.result).slice(0, 80)
    : data.error?.slice(0, 80) ?? 'Failed';

  return (
    <div className="my-0.5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[13px] text-[#7a7568] hover:text-[#a09888] transition-colors"
      >
        <ChevronRight
          size={14}
          className={`transition-transform duration-150 ${open ? 'rotate-90' : ''}`}
        />
        <span className={statusColor}>{statusIcon}</span>
        <span className="font-mono text-[#8a8478]">{data.tool}</span>
        {!open && (
          <span className="text-[#5a5548] truncate max-w-[400px]">— {preview}</span>
        )}
      </button>

      {open && (
        <div className="ml-5 mt-1.5 rounded-lg bg-[#1e1e1c] border border-white/[0.04] p-3 text-[12px] font-mono text-[#a09888] max-h-[200px] overflow-y-auto whitespace-pre-wrap">
          {data.success
            ? typeof data.result === 'string'
              ? data.result
              : JSON.stringify(data.result, null, 2)
            : data.error}
        </div>
      )}
    </div>
  );
}
