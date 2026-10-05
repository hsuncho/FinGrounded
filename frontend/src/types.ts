export type Confidence = 'high' | 'medium' | 'low'

export interface Source {
  title: string
  url: string | null
  locator: string | null
}

export interface ToolCall {
  name: string
  args: Record<string, unknown>
  ok: boolean | null
}

export interface ComputedValue {
  company: string
  year: string
  ratio: string
  value: number
  unit: string
  /** 계정명 → 금액(예: "92,228,115백만원"). 순서는 [분자, 분모]. */
  inputs: Record<string, string>
}

export interface AskResponse {
  answer: string
  confidence: Confidence
  caveats: string
  sources: Source[]
  tool_calls: ToolCall[]
  computed: ComputedValue[]
}

export type ApiErrorKind = 'not_ready' | 'busy' | 'failed' | 'invalid' | 'network'

export interface Turn {
  id: string
  question: string
  status: 'pending' | 'done' | 'error'
  startedAt: number
  response?: AskResponse
  error?: { kind: ApiErrorKind; message: string }
}
