import { useState, type FormEvent, type KeyboardEvent } from 'react'
import './QuestionInput.css'

const MAX_LEN = 500 // backend/api/schemas.py MAX_QUESTION_LEN

interface Props {
  onSubmit: (question: string) => void
  pending: boolean
}

export function QuestionInput({ onSubmit, pending }: Props) {
  const [value, setValue] = useState('')
  const trimmed = value.trim()
  const canSend = trimmed.length > 0 && trimmed.length <= MAX_LEN && !pending

  const send = () => {
    if (!canSend) return
    onSubmit(trimmed)
    setValue('')
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    send()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 한글 입력 중(조합 중) Enter는 글자 확정용이다. 이때 전송하면 마지막 글자가 잘리거나
    // 같은 질문이 두 번 전송되므로 조합이 끝난 Enter만 전송으로 처리한다.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send()
    }
  }

  return (
    <form className="question-input" onSubmit={handleSubmit}>
      <label htmlFor="question" className="visually-hidden">
        재무 질문
      </label>
      <textarea
        id="question"
        rows={2}
        value={value}
        maxLength={MAX_LEN}
        placeholder="예: 삼성전자 2023년 부채비율은 얼마야?"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        aria-describedby="question-hint"
      />
      <div className="question-input__bar">
        <p id="question-hint" className="question-input__hint">
          Enter로 보내기, Shift+Enter로 줄바꿈 <span className="num">{value.length}/{MAX_LEN}</span>
        </p>
        <button type="submit" disabled={!canSend}>
          {pending ? '답변 기다리는 중' : '질문하기'}
        </button>
      </div>
    </form>
  )
}
