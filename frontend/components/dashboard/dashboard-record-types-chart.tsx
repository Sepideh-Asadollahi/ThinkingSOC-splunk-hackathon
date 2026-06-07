"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import { NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { topRecordTypes } from "@/lib/api/dashboard"
import type { CountByType } from "@/lib/api/types"

const chartConfig = {
  count: { label: "Records", color: "hsl(174 72% 46%)" },
} satisfies ChartConfig

function shortenType(type: string): string {
  return type.replace(/^soc_/, "").replace(/_/g, " ")
}

export function DashboardRecordTypesChart({
  counts,
}: {
  counts: CountByType[]
}) {
  const data = topRecordTypes(counts).map((row) => ({
    ...row,
    label: shortenType(row.type),
  }))
  const hasData = data.some((d) => d.count > 0)

  return (
    <NeonGlassCard accent="teal" animatePreset="page">
      <NeonCardHeader
        accent="teal"
        title="Records by type"
        description="Top stored tsoc_record_type values"
        className="px-4 pt-4"
      />
      <div className="min-h-[280px] px-2 pb-4">
        {hasData ? (
          <ChartContainer config={chartConfig} className="h-[280px] w-full aspect-auto">
            <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="label"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                interval={0}
                angle={-24}
                textAnchor="end"
                height={72}
                tick={{ fill: "#94a3b8", fontSize: 11 }}
              />
              <YAxis tickLine={false} axisLine={false} width={36} allowDecimals={false} />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              <Bar dataKey="count" fill="var(--color-count)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        ) : (
          <div className="flex h-[280px] items-center justify-center text-sm text-slate-500">
            No stored records yet
          </div>
        )}
      </div>
    </NeonGlassCard>
  )
}
