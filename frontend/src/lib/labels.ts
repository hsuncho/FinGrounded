import type { ComputedValue, Confidence, Source } from '../types'

export const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: '높음',
  medium: '보통',
  low: '낮음',
}

export const TOOL_LABEL: Record<string, string> = {
  calculate_financial_ratio: '재무비율 계산',
  compare_by_industry: '동종업계 비교',
  search_knowledge_base: '공시 문서 검색',
}

/** backend/tools.py RATIOS의 비율은 모두 (분자 ÷ 분모) × 100 형태다. 새 비율을 추가하면 여기도 확인한다. */
const RATIO_OF_TWO_ACCOUNTS = new Set(['부채비율', '유동비율', 'ROE', '영업이익률', '순이익률'])

export interface FormulaLine {
  op: '' | '÷'
  account: string
  amount: string
}

/** 계산식으로 보여줄 수 있으면 줄 목록을, 형태를 모르는 비율이면 null을 돌려준다. */
export function formulaLines(c: ComputedValue): FormulaLine[] | null {
  const entries = Object.entries(c.inputs)
  if (!RATIO_OF_TWO_ACCOUNTS.has(c.ratio) || entries.length !== 2 || c.unit !== '%') return null
  const [[numName, numAmt], [denName, denAmt]] = entries
  return [
    { op: '', account: numName, amount: numAmt },
    { op: '÷', account: denName, amount: denAmt },
  ]
}

/** 계산값의 근거가 된 재무제표 출처를 찾는다(tools._account_source의 제목 규칙과 맞춤). */
export function findSourceFor(c: ComputedValue, sources: Source[]): Source | undefined {
  const title = `${c.company} ${c.year} 연결재무제표`
  return sources.find((s) => s.title === title)
}

export function isWebUrl(url: string | null | undefined): url is string {
  if (!url) return false
  try {
    const { protocol } = new URL(url)
    return protocol === 'https:' || protocol === 'http:'
  } catch {
    return false
  }
}

export function formatValue(value: number): string {
  return value.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
