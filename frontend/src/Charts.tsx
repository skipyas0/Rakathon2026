import type { Trend, TrendPoint } from './briefing'
import { fmtDate } from './layout'
import { useSources } from './sources'

const num = (v: number) => v.toLocaleString('cs-CZ', { maximumFractionDigits: 1 })
const t = (d: string) => new Date(d).getTime()

/** One measured value over time: 2px line, ringed dots, reference range as a band. Data comes
 * straight from records (not AI), so it renders as fact; every point opens its source. */
export function TrendChart({ trend }: { trend: Trend }) {
  const show = useSources()
  const { points: pts, ref_low: lo, ref_high: hi } = trend
  if (!pts.length) return null
  const W = 240, H = 96, L = 28, R = 8, T = 8, B = 18 // ≈ rendered px, so 10px text stays 10px
  const x0 = t(pts[0].date), x1 = t(pts[pts.length - 1].date)
  const vals = pts.map((p) => p.value)
  let [y0, y1] = trend.axis ?? [Math.min(...vals, lo ?? Infinity), Math.max(...vals, hi ?? -Infinity)]
  if (!trend.axis) {
    // pad, then snap to clean numbers (e.g. 0–25, 50–200) so the axis labels read cleanly
    const pad = (y1 - y0) * 0.15 || 1
    const step = 10 ** Math.floor(Math.log10(y1 - y0 + 2 * pad)) / 2
    y0 = Math.max(0, Math.floor((y0 - pad) / step) * step)
    y1 = Math.ceil((y1 + pad) / step) * step
  }
  const x = (d: string) => (x1 === x0 ? (L + W - R) / 2 : L + ((t(d) - x0) / (x1 - x0)) * (W - L - R))
  const y = (v: number) => H - B - ((v - y0) / (y1 - y0 || 1)) * (H - T - B)
  const out = (p: TrendPoint) => (lo != null && p.value < lo) || (hi != null && p.value > hi)
  const last = pts[pts.length - 1]
  const delta = last.value - pts[0].value
  const bandTop = y(Math.min(hi ?? y1, y1)), bandBottom = y(Math.max(lo ?? y0, y0))

  return (
    <figure className="trend">
      <figcaption>
        <span className="trend-label">{trend.label}</span>
        <span className="trend-value">
          {num(last.value)} <small>{trend.unit}</small>
        </span>
        {pts.length > 1 && (
          <span className="trend-delta">
            {delta > 0 ? '↑' : delta < 0 ? '↓' : '→'} {num(Math.abs(delta))} od {fmtDate(pts[0].date)}
          </span>
        )}
        {out(last) && <span className="oor">▲ mimo normu</span>}
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${trend.label}: ${pts.map((p) => `${fmtDate(p.date)} ${num(p.value)} ${trend.unit}`).join(', ')}`}
      >
        {(lo != null || hi != null) && (
          <>
            <rect className="band" x={L} y={bandTop} width={W - L - R} height={Math.max(0, bandBottom - bandTop)} />
            <text className="band-label" x={W - R - 2} y={bandTop + 10} textAnchor="end">
              norma
            </text>
          </>
        )}
        <line className="grid" x1={L} x2={W - R} y1={H - B} y2={H - B} />
        <text className="tick" x={L - 6} y={y(y1) + 4} textAnchor="end">
          {num(y1)}
        </text>
        <text className="tick" x={L - 6} y={y(y0) + 4} textAnchor="end">
          {num(y0)}
        </text>
        <text className="tick" x={L} y={H - 4}>
          {fmtDate(pts[0].date)}
        </text>
        {pts.length > 1 && (
          <text className="tick" x={W - R} y={H - 4} textAnchor="end">
            {fmtDate(last.date)}
          </text>
        )}
        <polyline className="line" points={pts.map((p) => `${x(p.date)},${y(p.value)}`).join(' ')} />
        {pts.map((p) => (
          <g
            key={p.date}
            className="pt"
            role="button"
            tabIndex={0}
            onClick={() => show({ title: `${trend.label}: ${num(p.value)} ${trend.unit}`, sources: [p.source] })}
            onKeyDown={(e) => e.key === 'Enter' && show({ title: `${trend.label}: ${num(p.value)} ${trend.unit}`, sources: [p.source] })}
          >
            <title>{`${fmtDate(p.date)}: ${num(p.value)} ${trend.unit}${out(p) ? ' (mimo normu)' : ''}`}</title>
            <circle className="hit" cx={x(p.date)} cy={y(p.value)} r={11} />
            <circle className={`dot ${out(p) ? 'out' : ''}`} cx={x(p.date)} cy={y(p.value)} r={4.5} />
          </g>
        ))}
      </svg>
    </figure>
  )
}
