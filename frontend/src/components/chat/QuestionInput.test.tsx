import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { QuestionInput } from './QuestionInput'

describe('QuestionInput', () => {
  it('Enter로 보내고 입력창을 비운다', async () => {
    const onSubmit = vi.fn()
    render(<QuestionInput onSubmit={onSubmit} pending={false} />)
    const box = screen.getByLabelText('재무 질문')

    await userEvent.type(box, '  부채비율?  {Enter}')

    expect(onSubmit).toHaveBeenCalledWith('부채비율?')
    expect(box).toHaveValue('')
  })

  it('한글 조합 중 Enter는 보내지 않는다', () => {
    const onSubmit = vi.fn()
    render(<QuestionInput onSubmit={onSubmit} pending={false} />)
    const box = screen.getByLabelText('재무 질문')

    fireEvent.change(box, { target: { value: '부채비' } })
    fireEvent.keyDown(box, { key: 'Enter', isComposing: true })

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('Shift+Enter는 줄바꿈', async () => {
    const onSubmit = vi.fn()
    render(<QuestionInput onSubmit={onSubmit} pending={false} />)

    await userEvent.type(screen.getByLabelText('재무 질문'), '첫줄{Shift>}{Enter}{/Shift}둘째줄')

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByLabelText('재무 질문')).toHaveValue('첫줄\n둘째줄')
  })

  it('답변을 기다리는 동안과 빈 입력일 때는 보낼 수 없다', async () => {
    const onSubmit = vi.fn()
    const { rerender } = render(<QuestionInput onSubmit={onSubmit} pending={false} />)
    expect(screen.getByRole('button', { name: '질문하기' })).toBeDisabled()

    rerender(<QuestionInput onSubmit={onSubmit} pending={true} />)
    await userEvent.type(screen.getByLabelText('재무 질문'), '질문{Enter}')
    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '답변 기다리는 중' })).toBeDisabled()
  })
})
