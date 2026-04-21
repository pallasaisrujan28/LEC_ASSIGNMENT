'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface AnswerBlockProps {
  markdown: string;
}

export default function AnswerBlock({ markdown }: AnswerBlockProps) {
  return (
    <div className="mt-3 answer-md text-[15px] text-[#d4d0c8] leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </div>
  );
}
