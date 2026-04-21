'use client';

import { BudgetEventData } from '@/types/agent';

interface BudgetBlockProps {
  data: BudgetEventData;
}

export default function BudgetBlock({ data }: BudgetBlockProps) {
  const pct = ((data.total_cost_usd / data.max_budget_usd) * 100).toFixed(1);
  return (
    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] font-mono text-[#4a4538]">
      <span>in {data.total_input_tokens.toLocaleString()} tok</span>
      <span>out {data.total_output_tokens.toLocaleString()} tok</span>
      <span>calls {data.calls}</span>
      <span>cost ${data.total_cost_usd.toFixed(4)}</span>
      <span>({pct}% of ${data.max_budget_usd} budget)</span>
    </div>
  );
}
