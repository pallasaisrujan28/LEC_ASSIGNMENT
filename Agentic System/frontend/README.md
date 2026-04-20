# AgentCore Frontend

A production-grade Next.js frontend for a Plan-and-Execute AI agent. Streams reasoning steps, tool calls, and answers in real time via SSE.

## Tech Stack

| Layer       | Choice                               |
|-------------|--------------------------------------|
| Framework   | Next.js 15 (App Router)              |
| Styling     | Tailwind CSS v3 + custom CSS tokens  |
| Animations  | Framer Motion                        |
| Markdown    | react-markdown + remark-gfm          |
| Fonts       | Syne · Outfit · IBM Plex Mono        |
| Icons       | lucide-react                         |

## Project Structure

```
agentcore/
├── app/
│   ├── globals.css          # Design tokens, markdown styles, base reset
│   ├── layout.tsx           # Root layout with next/font
│   └── page.tsx             # Entry point
├── components/
│   ├── ChatInterface.tsx    # Main orchestrator — state, SSE, turns
│   ├── Sidebar.tsx          # Left sidebar with thread info + demo toggle
│   ├── TurnView.tsx         # Renders one user query + all agent events
│   ├── EmptyState.tsx       # Welcome screen + example prompts
│   ├── MessageInput.tsx     # Auto-resize textarea + budget control
│   ├── PlanningBlock.tsx    # Collapsible plan with step badges
│   ├── ToolResultBlock.tsx  # Expandable tool result with source links
│   ├── AnswerBlock.tsx      # Markdown answer with copy button
│   ├── BudgetBlock.tsx      # Token/cost footer row
│   ├── ReflectingNote.tsx   # Re-plan feedback pill
│   └── ErrorBlock.tsx       # Red error banner
├── lib/
│   ├── sse.ts               # POST-based SSE parser (not EventSource)
│   ├── demo.ts              # Demo scenarios with realistic delays
│   └── utils.ts             # cn(), tool colour map, formatters
├── types/
│   └── agent.ts             # All TypeScript types for SSE events
├── tailwind.config.ts
├── tsconfig.json
└── next.config.ts
```

## Quick Start

```bash
npm install
npm run dev
```

App runs at http://localhost:3000. **Demo mode is on by default** — no backend needed.

## Connecting to Your Backend

1. Toggle **Demo mode OFF** in the sidebar
2. Your FastAPI backend must expose `POST /agent/stream` with SSE response
3. The frontend sends:
   ```json
   { "query": "...", "budget_limit": 20.0, "thread_id": "thread_abc123" }
   ```
4. Expected SSE event format:
   ```
   event: planning
   data: {"thought": "...", "steps": [...]}

   event: tool_result
   data: {"step_id": "s1", "tool": "wikipedia", "success": true, "result": "..."}

   event: answer
   data: {"final_answer": "..."}

   event: budget
   data: {"total_input_tokens": 2840, ...}

   event: done
   data: {"status": "complete"}
   ```

## Customisation

- **Add a tool colour**: Edit `TOOL_COLORS` in `lib/utils.ts`
- **Add a demo scenario**: Add to `DEMO_SCENARIOS` in `lib/demo.ts`
- **Tweak the palette**: All colours are in `tailwind.config.ts` and `app/globals.css`
- **Change fonts**: Swap `next/font/google` imports in `app/layout.tsx`
