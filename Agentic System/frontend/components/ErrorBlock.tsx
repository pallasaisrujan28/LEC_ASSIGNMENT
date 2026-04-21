'use client';

interface ErrorBlockProps {
  message: string;
}

export default function ErrorBlock({ message }: ErrorBlockProps) {
  return (
    <div className="my-2 text-[13px] text-red-400">
      Error: {message}
    </div>
  );
}
