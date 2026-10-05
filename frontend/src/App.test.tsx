import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import { jsonResponse, RATIO_ANSWER, REFUSAL_ANSWER } from './test/fixtures'

describe('App', () => {
  it('예시 질문 → 대기 → 계산값과 출처가 있는 답변', async () => {
    let resolve!: (r: Response) => void
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise((r) => (resolve = r)))
    render(<App />)

    await userEvent.click(screen.getByRole('button', { name: /삼성전자 2023년 부채비율은 얼마야/ }))

    expect(screen.getByRole('status')).toHaveTextContent('계산하는 중')
    expect(screen.getByRole('button', { name: '답변 기다리는 중' })).toBeDisabled()

    resolve(jsonResponse(RATIO_ANSWER))

    expect(await screen.findByText('삼성전자의 2023년 부채비율은 25.36%입니다.')).toBeInTheDocument()
    expect(screen.getByRole('figure', { name: /부채비율 계산 내역/ })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: '출처' })).toHaveTextContent('삼성전자 2023 연결재무제표')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('거부 답변은 근거 데이터 없음으로 표시한다', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(REFUSAL_ANSWER))
    render(<App />)

    await userEvent.click(screen.getByRole('button', { name: /2019년 부채비율/ }))

    expect(await screen.findByText('근거 데이터 없음')).toBeInTheDocument()
    expect(screen.queryByRole('figure')).not.toBeInTheDocument()
    expect(screen.getByText('이 답변에 쓰인 공시 자료가 없습니다.')).toBeInTheDocument()
  })

  it('실패하면 원인을 보여주고, 다시 시도하면 같은 질문을 다시 보낸다', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ detail: '서비스를 준비 중입니다.' }, 503))
      .mockResolvedValueOnce(jsonResponse(RATIO_ANSWER))
    render(<App />)

    await userEvent.type(screen.getByLabelText('재무 질문'), '삼성전자 부채비율{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent('모델을 불러오는 중')

    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByText(/25.36%입니다/)).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(1) // 실패한 턴은 교체됨
    expect(JSON.parse(fetchMock.mock.calls[1][1]!.body as string)).toEqual({ question: '삼성전자 부채비율' })
  })
})
