'use client';

interface ReflectingNoteProps {
  feedback: string;
}

export default function ReflectingNote({ feedback }: ReflectingNoteProps) {
  return (
    <div className="my-1 text-[12px] text-[#5a5548] italic">
      ↻ Re-planning: {feedback}
    </div>
  );
}
