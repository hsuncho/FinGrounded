import { CONFIDENCE_LABEL } from '../../lib/labels'
import type { AskResponse, Turn } from '../../types'
import { SourceList } from '../evidence/SourceList'
import { ErrorState } from '../status/ErrorState'
import { PendingState } from '../status/PendingState'
import { ComputedValueCard } from './ComputedValueCard'
import { ToolCallList } from './ToolCallList'
import './AnswerTurn.css'

interface Props {
  turn: Turn
  onRetry: (turn: Turn) => void
  retryDisabled: boolean
}

export function AnswerTurn({ turn, onRetry, retryDisabled }: Props) {
  return (
    <article className="turn" aria-busy={turn.status === 'pending'}>
      <h2 className="turn__question">{turn.question}</h2>

      {turn.status === 'pending' && <PendingState startedAt={turn.startedAt} />}
      {turn.status === 'error' && turn.error && (
        <ErrorState message={turn.error.message} onRetry={() => onRetry(turn)} retryDisabled={retryDisabled} />
      )}
      {turn.status === 'done' && turn.response && <AnswerBody response={turn.response} />}
    </article>
  )
}

function AnswerBody({ response }: { response: AskResponse }) {
  // 출처도 계산값도 없으면 Agent가 데이터를 찾지 못해 답을 거부한 경우다.
  const noEvidence = response.sources.length === 0 && response.computed.length === 0

  return (
    <div className="answer">
      <div className="answer__main">
        <div className={noEvidence ? 'answer__prose answer__prose--unsupported' : 'answer__prose'}>
          <p className="answer__provenance">
            {noEvidence ? '근거 데이터 없음' : 'AI가 작성한 설명'}
            <span className="answer__confidence"> 확신도 {CONFIDENCE_LABEL[response.confidence]}</span>
          </p>
          <p className="answer__text">{response.answer}</p>
        </div>

        {response.computed.map((c) => (
          <ComputedValueCard key={`${c.company}|${c.year}|${c.ratio}`} computed={c} sources={response.sources} />
        ))}

        {response.caveats && (
          <p className="answer__caveats">
            <strong>유의사항</strong> {response.caveats}
          </p>
        )}

        <ToolCallList calls={response.tool_calls} />
      </div>

      <aside className="answer__refs" aria-label="출처">
        <h3 className="answer__refs-title">출처</h3>
        <SourceList sources={response.sources} />
      </aside>
    </div>
  )
}
