import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, askQuestion } from '../api/client'
import type { Turn } from '../types'

/**
 * 질문-답변 목록과 진행 상태를 관리한다.
 *
 * - 한 번에 하나의 질문만 보낸다(pending 중에는 ask가 무시됨). 백엔드 연결 풀이 작고
 *   LLM 호출이 비싸서, 연타로 같은 질문이 여러 번 나가는 것을 막는다.
 * - 화면을 떠나면 진행 중인 요청을 취소한다(AbortController).
 */
export function useAsk() {
  const [turns, setTurns] = useState<Turn[]>([])
  const controllerRef = useRef<AbortController | null>(null)
  // crypto.randomUUID()는 HTTPS·localhost에서만 동작하므로 단순 증가 번호를 쓴다.
  const nextIdRef = useRef(0)
  const pending = turns.some((t) => t.status === 'pending')

  useEffect(() => () => controllerRef.current?.abort(), [])

  const ask = useCallback(
    async (question: string) => {
      const q = question.trim()
      if (!q || pending) return

      const id = `turn-${nextIdRef.current++}`
      setTurns((prev) => [...prev, { id, question: q, status: 'pending', startedAt: Date.now() }])

      const controller = new AbortController()
      controllerRef.current = controller

      const update = (patch: Partial<Turn>) =>
        setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)))

      try {
        const response = await askQuestion(q, controller.signal)
        update({ status: 'done', response })
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') return
        const err = e instanceof ApiError ? e : new ApiError('failed', '알 수 없는 오류가 발생했습니다.')
        update({ status: 'error', error: { kind: err.kind, message: err.message } })
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null
      }
    },
    [pending],
  )

  /** 실패한 질문을 목록에서 빼고 같은 질문으로 다시 보낸다. */
  const retry = useCallback(
    (turn: Turn) => {
      if (pending) return
      setTurns((prev) => prev.filter((t) => t.id !== turn.id))
      void ask(turn.question)
    },
    [ask, pending],
  )

  return { turns, pending, ask, retry }
}
