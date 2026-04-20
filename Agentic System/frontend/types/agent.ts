export interface PlanStep {
  step_id: string;
  tool: string;
  args: Record<string, unknown>;
  depends_on: string[];
  reason: string;
}

export interface PlanningEventData {
  thought: string;
  steps: PlanStep[];
}

export interface ToolResultEventData {
  step_id: string;
  tool: string;
  success: boolean;
  result?: unknown;
  error?: string;
}

export interface ReflectingEventData {
  feedback: string;
}

export interface AnswerEventData {
  final_answer: string;
}

export interface BudgetEventData {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  max_budget_usd: number;
  calls: number;
}

export interface ErrorEventData {
  message: string;
}

export type AgentEvent =
  | { type: 'planning'; data: PlanningEventData }
  | { type: 'tool_result'; data: ToolResultEventData }
  | { type: 'reflecting'; data: ReflectingEventData }
  | { type: 'answer'; data: AnswerEventData }
  | { type: 'budget'; data: BudgetEventData }
  | { type: 'done'; data: { status: string } }
  | { type: 'error'; data: ErrorEventData };

export type StepStatus = 'pending' | 'running' | 'success' | 'failed';

export interface AgentTurn {
  id: string;
  query: string;
  events: AgentEvent[];
  stepStatuses: Record<string, StepStatus>;
  isStreaming: boolean;
}

export interface ConversationMeta {
  id: string;
  threadId: string;
  title: string;
  createdAt: Date;
}
