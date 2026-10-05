import { useEffect, useState } from 'react'

interface Props {
  startedAt: number
}

/**
 * 답변을 기다리는 동안 경과 시간을 보여준다.
 * Agent는 도구를 여러 번 호출할 수 있어 10~20초씩 걸리므로, 멈춘 것처럼 보이지 않게 한다.
 * (도구 단계별 진행 표시는 SSE 도입 후 추가)
 */
export function PendingState({ startedAt }: Props) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const seconds = Math.max(0, Math.floor((now - startedAt) / 1000))

  return (
    <p className="status status--pending" role="status">
      <span className="status__pulse" aria-hidden="true" />
      공시 데이터를 조회하고 계산하는 중입니다 <span className="num">{seconds}초</span>
    </p>
  )
}
