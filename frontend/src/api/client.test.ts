import { describe, expect, it, vi } from 'vitest'
import { jsonResponse, RATIO_ANSWER } from '../test/fixtures'
import { ApiError, askQuestion, toApiError } from './client'

describe('toApiError', () => {
  it('구분: 풀 고갈 503과 로딩 중 503', () => {
    expect(toApiError(503, '요청이 많아 처리할 수 없습니다.').kind).toBe('busy')
    expect(toApiError(503, '서비스를 준비 중입니다.').kind).toBe('not_ready')
  })

  it('422는 입력 오류, 그 밖의 오류는 실패', () => {
    expect(toApiError(422, '').kind).toBe('invalid')
    expect(toApiError(502, '').kind).toBe('failed')
    expect(toApiError(500, '').kind).toBe('failed')
  })
})

describe('askQuestion', () => {
  it('질문을 JSON으로 보내고 응답을 돌려준다', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(RATIO_ANSWER))

    const res = await askQuestion('부채비율?')

    expect(res.computed[0].value).toBe(25.36)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/ask')
    expect(JSON.parse(init!.body as string)).toEqual({ question: '부채비율?' })
  })

  it('HTTP 오류는 ApiError로 바꾼다', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ detail: '답변 생성 오류' }, 502))
    await expect(askQuestion('q')).rejects.toMatchObject({ kind: 'failed', status: 502 })
  })

  it('서버에 닿지 못하면 network 오류', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    const err = await askQuestion('q').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.kind).toBe('network')
  })
})
