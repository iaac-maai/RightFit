// A chart drawn from real curve points, as on the laptop's booster and standby screens (app/review/charts.js)
export const COLOR = { ink: "#15191A", red: "#C4311E", green: "#0E3B2E", grid: "#DCE6DE", quiet: "#6B8073" };
export const ceilTo = (v: number, step: number) => Math.ceil(v / step) * step;

type Pt = [number, number];
export interface Series { pts: Pt[]; color: string; label?: string; at?: Pt; anchor?: "start" | "middle" | "end" }
export interface Point { x: number; y: number; color: string; r?: number; tip?: string; label?: string; dx?: number; dy?: number; anchor?: "start" | "middle" | "end" }
export interface Guide { x1: number; y1: number; x2: number; y2: number; color: string }

export function Chart({ xMax, yMin = 0, yMax, xStep, yStep, xLabel, yLabel, series = [], points = [], guides = [], label }: {
  xMax: number; yMin?: number; yMax: number; xStep: number; yStep: number; xLabel: string; yLabel: string;
  series?: Series[]; points?: Point[]; guides?: Guide[]; label: string;
}) {
  const W = 640, H = 430, L = 62, R = 26, T = 20, B = 56;
  const X = (x: number) => L + (x / xMax) * (W - L - R);
  const Y = (y: number) => T + (1 - (y - yMin) / (yMax - yMin)) * (H - T - B);
  const ticks = (from: number, to: number, step: number) => Array.from({ length: Math.floor((to - from) / step + 1e-9) + 1 }, (_, i) => from + i * step);
  const path = (pts: Pt[]) => pts.filter(([x, y]) => x <= xMax && y >= yMin).map(([x, y], i) => `${i ? "L" : "M"}${X(x).toFixed(1)} ${Y(y).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="chart-svg">
      {ticks(0, xMax, xStep).map((x) => (
        <g key={`x${x}`}>
          <line x1={X(x)} x2={X(x)} y1={T} y2={H - B} stroke={COLOR.grid} />
          <text x={X(x)} y={H - B + 26} textAnchor="middle" fontSize="16">{+x.toFixed(1)}</text>
        </g>
      ))}
      {ticks(yMin, yMax, yStep).map((y) => (
        <g key={`y${y}`}>
          <line x1={L} x2={W - R} y1={Y(y)} y2={Y(y)} stroke={COLOR.grid} />
          <text x={L - 14} y={Y(y) + 5} textAnchor="end" fontSize="16">{+y.toFixed(1)}</text>
        </g>
      ))}
      <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" fontSize="15">{xLabel}</text>
      <text transform={`translate(18 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle" fontSize="15">{yLabel}</text>
      {guides.map((d, i) => (
        <line key={`g${i}`} x1={X(d.x1)} y1={Y(d.y1)} x2={X(d.x2)} y2={Y(d.y2)} stroke={d.color} strokeWidth="2" strokeDasharray="6 6" />
      ))}
      {series.map((s, i) => (
        <g key={`s${i}`}>
          <path d={path(s.pts)} fill="none" stroke={s.color} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
          {s.label && s.at && <text x={X(s.at[0])} y={Y(s.at[1])} style={{ fill: s.color }} fontSize="17" fontWeight="600" textAnchor={s.anchor ?? "start"}>{s.label}</text>}
        </g>
      ))}
      {points.map((p, i) => (
        <g key={`p${i}`}>
          <circle cx={X(p.x)} cy={Y(p.y)} r={p.r ?? 7} fill={p.color} stroke="#fff" strokeWidth="2">{p.tip && <title>{p.tip}</title>}</circle>
          {p.label && <text x={X(p.x) + (p.dx ?? 0)} y={Y(p.y) + (p.dy ?? 0)} style={{ fill: COLOR.ink }} fontSize="16" fontWeight="600" textAnchor={p.anchor ?? "start"}>{p.label}</text>}
        </g>
      ))}
    </svg>
  );
}
