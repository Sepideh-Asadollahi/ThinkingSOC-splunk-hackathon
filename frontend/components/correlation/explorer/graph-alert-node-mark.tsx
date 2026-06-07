/** SVG alert node — hex ring + risk score (no generic "ALE" label). */

export type AlertNodeTier = "critical" | "elevated" | "low"

export function alertNodeTier(risk: number | undefined): AlertNodeTier {
  const score = typeof risk === "number" ? risk : 0
  if (score >= 70) return "critical"
  if (score >= 40) return "elevated"
  return "low"
}

const TIER_STYLES: Record<
  AlertNodeTier,
  { accent: string; glow: string; fill: string; ring: string }
> = {
  critical: {
    accent: "#f87171",
    glow: "rgba(248,113,113,0.45)",
    fill: "rgba(127,29,29,0.55)",
    ring: "rgba(252,165,165,0.85)",
  },
  elevated: {
    accent: "#fbbf24",
    glow: "rgba(251,191,36,0.4)",
    fill: "rgba(120,53,15,0.5)",
    ring: "rgba(253,224,71,0.85)",
  },
  low: {
    accent: "#34d399",
    glow: "rgba(52,211,153,0.35)",
    fill: "rgba(6,78,59,0.45)",
    ring: "rgba(110,231,183,0.85)",
  },
}

/** Flat-top hexagon path centered at 0,0 */
export function hexagonPath(radius: number): string {
  const points: string[] = []
  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI / 180) * (60 * i - 30)
    points.push(`${(radius * Math.cos(angle)).toFixed(2)},${(radius * Math.sin(angle)).toFixed(2)}`)
  }
  return `M ${points.join(" L ")} Z`
}

export type GraphAlertNodeMarkProps = {
  x: number
  y: number
  radius: number
  risk?: number
  selected?: boolean
  hover?: boolean
}

export function GraphAlertNodeMark({
  x,
  y,
  radius,
  risk,
  selected = false,
  hover = false,
}: GraphAlertNodeMarkProps) {
  const tier = alertNodeTier(risk)
  const style = TIER_STYLES[tier]
  const active = selected || hover
  const outerR = radius + (active ? 3 : 0)
  const score =
    typeof risk === "number" && Number.isFinite(risk) ? Math.round(risk) : "—"

  return (
    <g transform={`translate(${x}, ${y})`} pointerEvents="none">
      {active ? (
        <polygon
          d={hexagonPath(outerR + 5)}
          fill="none"
          stroke={style.glow}
          strokeWidth={2}
          opacity={0.65}
        />
      ) : null}
      <polygon
        d={hexagonPath(outerR)}
        fill={style.fill}
        stroke={style.ring}
        strokeWidth={active ? 2.25 : 1.5}
      />
      <circle
        r={outerR * 0.58}
        fill="#0a0a12"
        stroke={style.accent}
        strokeWidth={1.25}
        opacity={0.98}
      />
      <text
        y={1}
        textAnchor="middle"
        dominantBaseline="middle"
        className="select-none font-bold"
        fill={style.accent}
        fontSize={Math.max(12, outerR * 0.52)}
      >
        {score}
      </text>
    </g>
  )
}
