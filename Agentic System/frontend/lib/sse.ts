export async function streamAgent(
  query: string,
  budgetLimit: number,
  threadId: string,
  onEvent: (eventType: string, data: unknown) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch('/agent/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      budget_limit: budgetLimit,
      thread_id: threadId,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (currentEvent) {
              onEvent(currentEvent, data);
            }
          } catch {
            // ignore malformed JSON
          }
        } else if (line === '') {
          // empty line = event boundary, reset event name
          currentEvent = '';
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
