import './EmptyState.css'

const EXAMPLES = [
  { question: '삼성전자 2023년 부채비율은 얼마야?', note: '공시 계정으로 비율을 계산합니다' },
  { question: '2023년 반도체 기업들의 부채비율을 비교해줘.', note: '같은 산업 기업을 모두 계산해 비교합니다' },
  { question: '삼성전자 2019년 부채비율은?', note: '데이터가 없으면 추정하지 않고 없다고 답합니다' },
]

interface Props {
  onPick: (question: string) => void
  disabled: boolean
}

export function EmptyState({ onPick, disabled }: Props) {
  return (
    <section className="empty-state" aria-labelledby="empty-title">
      <h2 id="empty-title" className="empty-state__title">
        질문을 고르거나 직접 입력하세요
      </h2>
      <p className="empty-state__scope">
        삼성전자, SK하이닉스, NAVER, 카카오, 현대차의 2022~2024년 사업보고서를 다룹니다.
      </p>
      <ul className="empty-state__list">
        {EXAMPLES.map((ex) => (
          <li key={ex.question}>
            <button type="button" onClick={() => onPick(ex.question)} disabled={disabled}>
              <span className="empty-state__q">{ex.question}</span>
              <span className="empty-state__note">{ex.note}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
