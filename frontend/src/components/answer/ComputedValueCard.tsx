import { findSourceFor, formatValue, formulaLines, isWebUrl } from '../../lib/labels'
import type { ComputedValue, Source } from '../../types'
import './ComputedValueCard.css'

interface Props {
  computed: ComputedValue
  sources: Source[]
}

/**
 * 계산 도구가 DB 계정 값으로 계산한 비율을 감사조서 계산표처럼 보여준다.
 * 계정 금액 옆의 ✓(tick mark)는 그 값이 공시 재무제표와 대조됐다는 표시이고, 원문으로 연결된다.
 */
export function ComputedValueCard({ computed, sources }: Props) {
  const lines = formulaLines(computed)
  const source = findSourceFor(computed, sources)
  const heading = `${computed.company} ${computed.year} ${computed.ratio}`

  const tick = source && isWebUrl(source.url) ? (
    <a
      className="calc__tick"
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      title="공시 원문에서 확인"
      aria-label={`${source.title} 원문에서 확인 (새 창)`}
    >
      ✓
    </a>
  ) : (
    <span className="calc__tick" aria-hidden="true">
      ✓
    </span>
  )

  return (
    <figure className="calc" aria-label={`${heading} 계산 내역`}>
      <figcaption className="calc__caption">
        <span className="calc__heading">{heading}</span>
        <span className="calc__provenance">공시 계정으로 계산</span>
      </figcaption>

      <table className="calc__table">
        <tbody>
          {lines ? (
            <>
              {lines.map((line) => (
                <tr key={line.account}>
                  <td className="calc__op">{line.op}</td>
                  <th scope="row">{line.account}</th>
                  <td className="calc__amount num">{line.amount}</td>
                  <td className="calc__mark">{tick}</td>
                </tr>
              ))}
              <tr>
                <td className="calc__op">×</td>
                <th scope="row">100</th>
                <td />
                <td />
              </tr>
            </>
          ) : (
            Object.entries(computed.inputs).map(([account, amount]) => (
              <tr key={account}>
                <td className="calc__op" />
                <th scope="row">{account}</th>
                <td className="calc__amount num">{amount}</td>
                <td className="calc__mark">{tick}</td>
              </tr>
            ))
          )}
        </tbody>
        <tfoot>
          <tr>
            <td className="calc__op">=</td>
            <th scope="row">{computed.ratio}</th>
            <td className="calc__result num">
              {formatValue(computed.value)}
              <span className="calc__unit">{computed.unit}</span>
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
    </figure>
  )
}
