import { useEffect, useRef } from 'react'
import { AnswerTurn } from './components/answer/AnswerTurn'
import { EmptyState } from './components/chat/EmptyState'
import { QuestionInput } from './components/chat/QuestionInput'
import { useAsk } from './hooks/useAsk'
import './App.css'

export default function App() {
  const { turns, pending, ask, retry } = useAsk()
  const lastTurnRef = useRef<HTMLLIElement>(null)

  useEffect(() => {
    if (turns.length === 0) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    lastTurnRef.current?.scrollIntoView?.({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
  }, [turns.length])

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">FinGrounded</h1>
        <p className="app-lede">
          상장기업 공시 데이터로 재무비율을 계산하고, 모든 답에 출처를 붙입니다.
        </p>
      </header>

      <main className="app-main">
        {turns.length === 0 ? (
          <EmptyState onPick={ask} disabled={pending} />
        ) : (
          <ol className="turn-list" aria-label="질문과 답변">
            {turns.map((turn, i) => (
              <li key={turn.id} ref={i === turns.length - 1 ? lastTurnRef : undefined}>
                <AnswerTurn turn={turn} onRetry={retry} retryDisabled={pending} />
              </li>
            ))}
          </ol>
        )}
      </main>

      <footer className="app-composer">
        <QuestionInput onSubmit={ask} pending={pending} />
      </footer>
    </div>
  )
}
