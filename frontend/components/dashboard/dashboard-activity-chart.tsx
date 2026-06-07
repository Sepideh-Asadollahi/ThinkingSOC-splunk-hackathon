"use client"

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"

import { NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { formatActivityTimelineForChart, hasChartData } from "@/lib/api/dashboard"
import type { ActivityTimelinePoint } from "@/lib/api/types"

const chartConfig = {
  security: { label: "Security", color: "hsl(174 72% 46%)" },
  observability: { label: "Observability", color: "hsl(270 70% 62%)" },
  correlation: { label: "Correlation", color: "hsl(205 80% 55%)" },
} satisfies ChartConfig

export function DashboardActivityChart({
  timeline,
}: {
  timeline: ActivityTimelinePoint[]
}) {
  const data = formatActivityTimelineForChart(timeline)
  const hasData = hasChartData(
    data.flatMap((d) => [d.security, d.observability, d.correlation])
  )

  return (
    <NeonGlassCard accent="teal" animatePreset="page" className="flex h-full flex-col">
      <NeonCardHeader
        accent="teal"
        title="Pipeline activity"
        description="Stored events per day (last 30 days)"
        className="px-4 pt-4"
      />
      <div className="flex min-h-0 flex-1 items-center justify-center px-4 pb-4 pt-0">
        {hasData ? (
          <ChartContainer config={chartConfig} className="h-[280px] w-full">
            <AreaChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="label"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                minTickGap={24}
              />
              <YAxis tickLine={false} axisLine={false} width={32} allowDecimals={false} />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Area
                type="monotone"
                dataKey="security"
                stackId="a"
                stroke="var(--color-security)"
                fill="var(--color-security)"
                fillOpacity={0.35}
              />
              <Area
                type="monotone"
                dataKey="observability"
                stackId="a"
                stroke="var(--color-observability)"
                fill="var(--color-observability)"
                fillOpacity={0.3}
              />
              <Area
                type="monotone"
                dataKey="correlation"
                stackId="a"
                stroke="var(--color-correlation)"
                fill="var(--color-correlation)"
                fillOpacity={0.25}
              />
            </AreaChart>
          </ChartContainer>
        ) : (
          <div className="flex h-[280px] items-center justify-center text-sm text-slate-500">
            No activity in the selected window
          </div>
        )}
      </div>
    </NeonGlassCard>
  )
}
