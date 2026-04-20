import { AgentEvent } from '@/types/agent';

export const DEMO_SCENARIOS: Record<string, AgentEvent[]> = {
  default: [
    {
      type: 'planning',
      data: {
        thought:
          "I need to look up Japan's population on Wikipedia, then use the calculator to compute 3% of that figure.",
        steps: [
          {
            step_id: 's1',
            tool: 'wikipedia',
            args: { query: 'Japan population 2024' },
            depends_on: [],
            reason: 'Retrieve current population estimate for Japan',
          },
          {
            step_id: 's2',
            tool: 'calculator',
            args: { expression: '123800000 * 0.03' },
            depends_on: ['s1'],
            reason: 'Compute 3% of the retrieved population figure',
          },
        ],
      },
    },
    {
      type: 'tool_result',
      data: {
        step_id: 's1',
        tool: 'wikipedia',
        success: true,
        result:
          "Japan is an island country in East Asia. As of 2024, Japan's population is approximately 123.8 million, making it the 12th most populous country in the world. The population has been declining since 2010 due to low birth rates.",
      },
    },
    {
      type: 'tool_result',
      data: {
        step_id: 's2',
        tool: 'calculator',
        success: true,
        result: '3714000',
      },
    },
    {
      type: 'answer',
      data: {
        final_answer: `## Japan's Population & 3%

Japan's current population is approximately **123.8 million** people (2024 estimate).

**3% of 123,800,000 = 3,714,000**

To put this in context, 3.7 million people is roughly equivalent to:
- The population of **Los Angeles** (3.8M)
- About **2.9%** of the United States' total population

Japan's population has been **declining since 2010**, primarily due to one of the world's lowest birth rates at approximately 1.2 children per woman.`,
      },
    },
    {
      type: 'budget',
      data: {
        total_input_tokens: 2840,
        total_output_tokens: 456,
        total_cost_usd: 0.0089,
        max_budget_usd: 20.0,
        calls: 3,
      },
    },
    { type: 'done', data: { status: 'complete' } },
  ],

  reflect: [
    {
      type: 'planning',
      data: {
        thought: 'I need to find the GDP of Germany and its population to compute GDP per capita.',
        steps: [
          {
            step_id: 's1',
            tool: 'web_search',
            args: { query: 'Germany GDP 2024' },
            depends_on: [],
            reason: 'Fetch latest German GDP figure',
          },
          {
            step_id: 's2',
            tool: 'wikipedia',
            args: { query: 'Germany population' },
            depends_on: [],
            reason: 'Retrieve German population — can run in parallel with GDP search',
          },
          {
            step_id: 's3',
            tool: 'calculator',
            args: { expression: '4456000000000 / 84000000' },
            depends_on: ['s1', 's2'],
            reason: 'Divide GDP by population to get per-capita figure',
          },
        ],
      },
    },
    {
      type: 'tool_result',
      data: {
        step_id: 's1',
        tool: 'web_search',
        success: true,
        result: {
          text: "Germany's GDP in 2024 is approximately $4.456 trillion USD, making it the largest economy in Europe.",
          sources: [
            { url: 'https://worldbank.org/germany-gdp-2024' },
            { url: 'https://statista.com/germany-economy' },
          ],
        },
      },
    },
    {
      type: 'tool_result',
      data: {
        step_id: 's2',
        tool: 'wikipedia',
        success: true,
        result: 'Germany has a population of approximately 84.4 million as of 2024.',
      },
    },
    {
      type: 'reflecting',
      data: {
        feedback:
          'The web search returned a rounded GDP figure. I should verify with a more precise source before calculating.',
      },
    },
    {
      type: 'tool_result',
      data: {
        step_id: 's3',
        tool: 'calculator',
        success: true,
        result: '52952.38',
      },
    },
    {
      type: 'answer',
      data: {
        final_answer: `## Germany: GDP per Capita

| Metric | Value |
|--------|-------|
| GDP (2024) | $4.456 trillion USD |
| Population | ~84.4 million |
| **GDP per capita** | **~$52,952 USD** |

Germany has the **largest economy in Europe** and ranks among the world's top 20 countries by GDP per capita. This figure reflects Germany's strong manufacturing and export sectors, anchored by industries like automotive (BMW, Mercedes, Volkswagen) and industrial machinery.`,
      },
    },
    {
      type: 'budget',
      data: {
        total_input_tokens: 3200,
        total_output_tokens: 580,
        total_cost_usd: 0.0112,
        max_budget_usd: 20.0,
        calls: 4,
      },
    },
    { type: 'done', data: { status: 'complete' } },
  ],
};

export async function runDemoStream(
  query: string,
  onEvent: (eventType: string, data: unknown) => void,
  signal?: AbortSignal
): Promise<void> {
  const lq = query.toLowerCase();
  const scenario =
    lq.includes('gdp') || lq.includes('germany')
      ? DEMO_SCENARIOS.reflect
      : DEMO_SCENARIOS.default;

  const delays = [600, 1400, 2600, query.toLowerCase().includes('reflect') ? 3200 : 99999, 3800, 4400, 4700];

  for (let i = 0; i < scenario.length; i++) {
    if (signal?.aborted) break;
    await sleep(i === 0 ? 700 : delays[i] ?? 800);
    if (signal?.aborted) break;
    const evt = scenario[i];
    onEvent(evt.type, evt.data);
  }
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
