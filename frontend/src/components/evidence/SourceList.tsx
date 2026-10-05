import { isWebUrl } from '../../lib/labels'
import type { Source } from '../../types'
import './SourceList.css'

interface Props {
  sources: Source[]
}

/** 답변 근거 목록. 도구 실행 결과에서 시스템이 수집한 출처라 LLM이 지어낼 수 없다. */
export function SourceList({ sources }: Props) {
  if (sources.length === 0) {
    return <p className="sources__empty">이 답변에 쓰인 공시 자료가 없습니다.</p>
  }

  return (
    <ol className="sources">
      {sources.map((s) => (
        <li key={`${s.title}|${s.locator ?? ''}`} className="sources__item">
          <span className="sources__title">{s.title}</span>
          {s.locator && <span className="sources__locator">{s.locator}</span>}
          {isWebUrl(s.url) && (
            <a href={s.url} target="_blank" rel="noopener noreferrer" className="sources__link">
              원문 보기<span className="visually-hidden"> (새 창)</span>
            </a>
          )}
        </li>
      ))}
    </ol>
  )
}
