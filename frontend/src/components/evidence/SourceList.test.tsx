import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { SourceList } from './SourceList'

it('웹 주소 출처만 원문 링크를 단다', () => {
  render(
    <SourceList
      sources={[
        { title: '삼성전자 2023 연결재무제표', url: 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240312000736', locator: '재무제표' },
        { title: 'report.pdf', url: 'data/docs/report.pdf', locator: 'p.3' },
      ]}
    />,
  )

  const links = screen.getAllByRole('link', { name: /원문 보기/ })
  expect(links).toHaveLength(1)
  expect(links[0]).toHaveAttribute('href', 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240312000736')
  expect(screen.getByText('report.pdf')).toBeInTheDocument()
})
