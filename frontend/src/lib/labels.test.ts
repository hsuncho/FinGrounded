import { describe, expect, it } from 'vitest'
import { RATIO_ANSWER } from '../test/fixtures'
import { findSourceFor, formatValue, formulaLines, isWebUrl } from './labels'

const computed = RATIO_ANSWER.computed[0]

describe('formulaLines', () => {
  it('분자 ÷ 분모 순서로 줄을 만든다', () => {
    expect(formulaLines(computed)).toEqual([
      { op: '', account: '부채총계', amount: '92,228,115백만원' },
      { op: '÷', account: '자본총계', amount: '363,677,865백만원' },
    ])
  })

  it('형태를 모르는 비율이면 계산식을 만들지 않는다', () => {
    expect(formulaLines({ ...computed, ratio: 'EV/EBITDA' })).toBeNull()
    expect(formulaLines({ ...computed, inputs: { 부채총계: '1' } })).toBeNull()
  })
})

describe('findSourceFor', () => {
  it('회사·연도로 재무제표 출처를 찾는다', () => {
    expect(findSourceFor(computed, RATIO_ANSWER.sources)?.url).toBe('https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240312000736')
    expect(findSourceFor({ ...computed, year: '2022' }, RATIO_ANSWER.sources)).toBeUndefined()
  })
})

it('formatValue는 소수 둘째 자리까지', () => {
  expect(formatValue(25.36)).toBe('25.36')
  expect(formatValue(1234.5)).toBe('1,234.50')
})

describe('isWebUrl', () => {
  it('http(s) 주소만 링크로 허용한다', () => {
    expect(isWebUrl('https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240312000736')).toBe(true)
    expect(isWebUrl('data/docs/삼성전자_사업보고서.pdf')).toBe(false)
    expect(isWebUrl('C:\\FinGrounded\\backend\\data\\docs\\a.pdf')).toBe(false)
    expect(isWebUrl('javascript:alert(1)')).toBe(false)
    expect(isWebUrl(null)).toBe(false)
  })
})
