'use client';

import { motion } from 'framer-motion';
import { AgentTurn, AgentEvent } from '@/types/agent';
import { Zap } from 'lucide-react';
import PlanningBlock from './PlanningBlock';
import ToolResultBlock from './ToolResultBlock';
import AnswerBlock from './AnswerBlock';
import BudgetBlock from './BudgetBlock';
import ReflectingNote from './ReflectingNote';
import ErrorBlock from './ErrorBlock';

interface TurnViewProps {
  turn: AgentTurn;
}

export default function TurnView({ turn }: TurnViewProps) {
  const planEvent = turn.events.find((e): e is Extract<AgentEvent, { type: 'planning' }> => e.type === 'planning');

  return (
    <div className="flex flex-col gap-4">
      {/* User message */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end"
      >
        <div className="max-w-[80%] rounded-2xl rounded-br-sm border border-white/[0.08] bg-[#252520] px-4 py-3 font-outfit text-sm text-[#e8e4dc] leading-relaxed shadow-lg">
          {turn.query}
        </div>
      </motion.div>

      {/* Agent events */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.15 }}
        className="flex flex-col gap-3"
      >
        {/* Agent label */}
        <div className="flex items-center gap-2">
          <img src="/lec-logo.png" alt="LEC" className="h-5 w-5 rounded object-contain" />
          <span className="font-mono text-[10px] uppercase tracking-[1.5px] text-[#5a5548]">
            LEC Agent
          </span>
        </div>

        {/* Planning block — shown once, updated as tool results arrive */}
        {planEvent && (
          <PlanningBlock
            data={planEvent.data}
            stepStatuses={turn.stepStatuses}
          />
        )}

        {/* Remaining events in order */}
        {turn.events.map((evt, i) => {
          if (evt.type === 'planning') return null;
          if (evt.type === 'tool_result') {
            return (
              <ToolResultBlock key={`tr-${i}`} data={evt.data} />
            );
          }
          if (evt.type === 'reflecting') {
            return <ReflectingNote key={`ref-${i}`} feedback={evt.data.feedback} />;
          }
          if (evt.type === 'answer') {
            return <AnswerBlock key={`ans-${i}`} markdown={evt.data.final_answer} />;
          }
          if (evt.type === 'budget') {
            return <BudgetBlock key={`bud-${i}`} data={evt.data} />;
          }
          if (evt.type === 'error') {
            return <ErrorBlock key={`err-${i}`} message={evt.data.message} />;
          }
          return null;
        })}
      </motion.div>
    </div>
  );
}
