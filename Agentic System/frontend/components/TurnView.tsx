'use client';

import { motion } from 'framer-motion';
import { AgentTurn, AgentEvent } from '@/types/agent';
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
  const planEvent = turn.events.find(
    (e): e is Extract<AgentEvent, { type: 'planning' }> => e.type === 'planning'
  );

  return (
    <div className="flex flex-col gap-1">
      {/* User message */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end mb-2"
      >
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-[#252520] px-4 py-2.5 text-[14px] text-[#e8e4dc] leading-relaxed">
          {turn.query}
        </div>
      </motion.div>

      {/* Agent response — flows naturally, no box */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        {/* Planning — collapsible, subtle */}
        {planEvent && (
          <PlanningBlock data={planEvent.data} stepStatuses={turn.stepStatuses} />
        )}

        {/* Tool results + reflections — collapsible */}
        {turn.events.map((evt, i) => {
          if (evt.type === 'planning') return null;
          if (evt.type === 'tool_result') return <ToolResultBlock key={`tr-${i}`} data={evt.data} />;
          if (evt.type === 'reflecting') return <ReflectingNote key={`ref-${i}`} feedback={evt.data.feedback} />;
          if (evt.type === 'answer') return <AnswerBlock key={`ans-${i}`} markdown={evt.data.final_answer} />;
          if (evt.type === 'budget') return <BudgetBlock key={`bud-${i}`} data={evt.data} />;
          if (evt.type === 'error') return <ErrorBlock key={`err-${i}`} message={evt.data.message} />;
          return null;
        })}
      </motion.div>
    </div>
  );
}
