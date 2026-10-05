import type { ApiErrorKind, AskResponse } from '../types'

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null

  constructor(kind: ApiErrorKind, message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

/** HTTP 상태를 화면에서 다룰 오류 종류로 바꾼다. 백엔드의 503은 두 가지 의미라 detail로 구분한다. */
export function toApiError(status: number, detail: string): ApiError {
  if (status === 422) return new ApiError('invalid', '질문을 확인해 주세요. 1~500자로 입력할 수 있습니다.', status)
  if (status === 503 && detail.includes('요청이 많아')) {
    return new ApiError('busy', '지금 처리 중인 질문이 많습니다. 잠시 후 다시 시도하세요.', status)
  }
  if (status === 503) return new ApiError('not_ready', '서버가 모델을 불러오는 중입니다. 잠시 후 다시 시도하세요.', status)
  return new ApiError('failed', '답변을 만들지 못했습니다. 다시 시도하세요.', status)
}

async function readDetail(res: Response): Promise<string> {
  try {
    const body = await res.json()
    return typeof body?.detail === 'string' ? body.detail : ''
  } catch {
    return ''
  }
}

export async function askQuestion(question: string, signal?: AbortSignal): Promise<AskResponse> {
  let res: Response
  try {
    res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ApiError('network', 'API 서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.')
  }

  if (!res.ok) throw toApiError(res.status, await readDetail(res))
  return (await res.json()) as AskResponse
}
