import { TOOL_LABEL } from '../../lib/labels'
import type { ToolCall } from '../../types'

interface Props {
  calls: ToolCall[]
}

function summarizeArgs(args: Record<string, unknown>): string {
  return Object.values(args)
    .filter((v) => typeof v === 'string' || typeof v === 'number')
    .join(', ')
}

export function ToolCallList({ calls }: Props) {
  if (calls.length === 0) return null

  return (
    <details className="answer__tools">
      <summary>Agent가 실행한 도구 {calls.length}개</summary>
      <ol>
        {calls.map((c, i) => (
          <li key={i}>
            <span>{TOOL_LABEL[c.name] ?? c.name}</span>
            {summarizeArgs(c.args) && <span className="answer__tool-args"> ({summarizeArgs(c.args)})</span>}
            <span className={c.ok ? 'answer__tool-ok' : 'answer__tool-fail'}>
              {c.ok ? ' 성공' : ' 데이터 없음'}
            </span>
          </li>
        ))}
      </ol>
    </details>
  )
}
