'use client';

import { motion } from 'framer-motion';
import { AlertCircle } from 'lucide-react';

interface ErrorBlockProps {
  message: string;
}

export default function ErrorBlock({ message }: ErrorBlockProps) {
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
