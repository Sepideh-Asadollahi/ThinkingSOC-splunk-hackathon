"use client"

import { CheckCircle2Icon, CircleIcon, XCircleIcon } from "lucide-react"
import {
  Label,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  RadialBar,
  RadialBarChart,
} from "recharts"

import { NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import type { DashboardIntegrations } from "@/lib/api/types"
import { cn } from "@/lib/utils"

const chartConfig = {
  score: { label: "Health", color: "hsl(174 72% 46%)" },
} satisfies ChartConfig

function IntegrationChip({
  label,
  ok,
}: {
  label: string
  ok: boolean
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs",
        ok
          ? "border-teal-500/30 bg-teal-500/10 text-teal-300"
          : "border-white/10 bg-white/5 text-slate-500"
      )}
    >
      {ok ? (
        <CheckCircle2Icon className="size-3.5 shrink-0" />
      ) : (
        <XCircleIcon className="size-3.5 shrink-0" />
      )}
      {label}
    </div>
  )
}

export function DashboardHealthGauge({
  healthScore,
  integrations,
}: {
  healthScore: number
  integrations: DashboardIntegrations
}) {
  const chartData = [{ name: "health", score: healthScore, fill: "var(--color-score)" }]

  return (
    <NeonGlassCard accent="violet" animatePreset="page" className="flex flex-col">
      <NeonCardHeader
        accent="violet"
        title="Platform health"
        description="Integration readiness score"
        className="px-4 pt-4"
      />
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 pb-4">
        <ChartContainer config={chartConfig} className="mx-auto h-[200px] w-full max-w-[220px] aspect-square">
          <RadialBarChart
            data={chartData}
            startAngle={90}
            endAngle={-270}
            innerRadius={70}
            outerRadius={95}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <PolarGrid
              gridType="circle"
              radialLines={false}
              stroke="none"
              className="fill-white/5"
              polarRadius={[76, 64]}
            />
            <ChartTooltip content={<ChartTooltipContent hideLabel />} />
            <RadialBar dataKey="score" background cornerRadius={8} />
            <PolarRadiusAxis tick={false} tickLine={false} axisLine={false}>
              <Label
                content={({ viewBox }) => {
                  if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                    return (
                      <text
                        x={viewBox.cx}
                        y={viewBox.cy}
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        <tspan
                          x={viewBox.cx}
                          y={viewBox.cy}
                          className="fill-white text-3xl font-semibold"
                        >
                          {healthScore}
                        </tspan>
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy || 0) + 22}
                          className="fill-slate-500 text-xs"
                        >
                          / 100
                        </tspan>
                      </text>
                    )
                  }
                  return null
                }}
              />
            </PolarRadiusAxis>
          </RadialBarChart>
        </ChartContainer>
        <div className="flex flex-wrap justify-center gap-2">
          <IntegrationChip label="PostgreSQL" ok={integrations.postgres} />
          <IntegrationChip label="Neo4j" ok={integrations.neo4j} />
          <IntegrationChip label="LiteLLM" ok={integrations.llm} />
          <IntegrationChip label="Splunk MCP" ok={integrations.mcp} />
        </div>
        <p className="flex items-center gap-1 text-center text-xs text-slate-500">
          <CircleIcon className="size-3" />
          Configure missing integrations under Splunk & Integrations
        </p>
      </div>
    </NeonGlassCard>
  )
}
