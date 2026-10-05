import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RATIO_ANSWER } from '../../test/fixtures'
import { ComputedValueCard } from './ComputedValueCard'

const computed = RATIO_ANSWER.computed[0]

describe('ComputedValueCard', () => {
  it('계정 금액, 계산식, 결과를 보여준다', () => {
    render(<ComputedValueCard computed={computed} sources={RATIO_ANSWER.sources} />)

    const card = screen.getByRole('figure', { name: '삼성전자 2023 부채비율 계산 내역' })
    expect(within(card).getByText('92,228,115백만원')).toBeInTheDocument()
    expect(within(card).getByText('÷')).toBeInTheDocument()
    expect(within(card).getByText('25.36')).toBeInTheDocument()
  })

  it('대조 표시는 공시 원문으로 연결된다', () => {
    render(<ComputedValueCard computed={computed} sources={RATIO_ANSWER.sources} />)

    const ticks = screen.getAllByRole('link', { name: /원문에서 확인/ })
    expect(ticks).toHaveLength(2)
    expect(ticks[0]).toHaveAttribute('href', 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240312000736')
    expect(ticks[0]).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('출처가 로컬 파일 경로면 링크를 만들지 않는다', () => {
    const local = [{ ...RATIO_ANSWER.sources[0], url: 'data/docs/report.pdf' }]
    render(<ComputedValueCard computed={computed} sources={local} />)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('출처를 못 찾으면 링크 없이 표시만 한다', () => {
    render(<ComputedValueCard computed={computed} sources={[]} />)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
