import { NeonBadge } from "@/components/neon-glass"
import { riskScoreClass } from "@/lib/api/graph/risk-score"
import { cn } from "@/lib/utils"

export function RiskScoreBadge({ score }: { score: number }) {
  return (
    <NeonBadge
      className={cn("border font-mono tabular-nums", riskScoreClass(score))}
    >
      {score}
    </NeonBadge>
  )
}
