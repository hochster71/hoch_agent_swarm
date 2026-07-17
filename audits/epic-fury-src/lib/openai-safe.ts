const OPENAI_URL = 'https://api.openai.com/v1/chat/completions'

type ChatRole = 'system' | 'user' | 'assistant'

interface ChatMessage {
  role: ChatRole
  content: string
}

interface ChatOptions {
  model?: string
  maxTokens?: number
  temperature?: number
  timeoutMs?: number
}

function hasValidOpenAIKey(): boolean {
  const key = process.env.OPENAI_API_KEY?.trim() ?? ''
  return key.startsWith('sk-')
}

function redactSecrets(input: string): string {
  return input
    .replace(/sk-[A-Za-z0-9_\-]+/g, 'sk-***')
    .replace(/Incorrect API key provided:[^\n"]+/gi, 'Incorrect API key provided: [redacted]')
}

export async function safeOpenAIChatCompletion(
  messages: ChatMessage[],
  opts: ChatOptions = {},
): Promise<string | null> {
  const apiKey = process.env.OPENAI_API_KEY?.trim()
  if (!apiKey || !hasValidOpenAIKey()) return null

  const model = opts.model ?? 'gpt-4o-mini'
  const maxTokens = opts.maxTokens ?? 512
  const temperature = opts.temperature ?? 0.2
  const timeoutMs = opts.timeoutMs ?? 20_000

  try {
    const res = await fetch(OPENAI_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model,
        messages,
        max_tokens: maxTokens,
        temperature,
        response_format: { type: 'json_object' },
      }),
      signal: AbortSignal.timeout(timeoutMs),
    })

    if (!res.ok) {
      const errText = redactSecrets(await res.text().catch(() => ''))
      console.error(`[openai-safe] ${model} error ${res.status}: ${errText}`)
      return null
    }

    const data = await res.json() as { choices?: Array<{ message?: { content?: string } }> }
    return data.choices?.[0]?.message?.content ?? null
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error(`[openai-safe] request failed: ${msg}`)
    return null
  }
}
