import type { AskResponse } from '../types'

// 실제 /api/ask 응답 형태(백엔드 E2E에서 확인한 값)
export const RATIO_ANSWER: AskResponse = {
  answer: '삼성전자의 2023년 부채비율은 25.36%입니다.',
  confidence: 'high',
  caveats: '',
  sources: [
    { title: '삼성전자 2023 연결재무제표', url: 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240312000736', locator: '재무제표' },
  ],
  tool_calls: [
    { name: 'calculate_financial_ratio', args: { company: '삼성전자', year: '2023', ratio: '부채비율' }, ok: true },
  ],
  computed: [
    {
      company: '삼성전자',
      year: '2023',
      ratio: '부채비율',
      value: 25.36,
      unit: '%',
      inputs: { 부채총계: '92,228,115백만원', 자본총계: '363,677,865백만원' },
    },
  ],
}

export const REFUSAL_ANSWER: AskResponse = {
  answer: '삼성전자 2019년 재무데이터를 찾을 수 없습니다.',
  confidence: 'low',
  caveats: '',
  sources: [],
  tool_calls: [{ name: 'calculate_financial_ratio', args: { company: '삼성전자', year: '2019' }, ok: false }],
  computed: [],
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
