import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}

export function formatCost(usd: number): string {
  if (usd < 0.001) return `< $0.001`;
  return `$${usd.toFixed(4)}`;
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}

export const TOOL_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  wikipedia:  { bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/20' },
  calculator: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
  web_search: { bg: 'bg-blue-500/10',   text: 'text-blue-400',   border: 'border-blue-500/20'   },
  memory:     { bg: 'bg-pink-500/10',   text: 'text-pink-400',   border: 'border-pink-500/20'   },
  default:    { bg: 'bg-cyan-500/10',   text: 'text-cyan-400',   border: 'border-cyan-500/20'   },
};

export function getToolColors(tool: string) {
  return TOOL_COLORS[tool] ?? TOOL_COLORS.default;
}
