"use client"

import { Bar, BarChart, Cell, LabelList, Pie, PieChart, XAxis, YAxis } from "recharts"

import { NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { priorityChartData, verdictChartData } from "@/lib/api/dashboard"
import type { CountByPriority, CountByVerdict } from "@/lib/api/types"

export function DashboardVerdictChart({
  items,
}: {
  items: CountByVerdict[]
}) {
  const data = verdictChartData(items)
  const hasData = data.some((d) => d.value > 0)
  const chartConfig = Object.fromEntries(
    data.map((d) => [d.name, { label: d.name, color: d.fill }])
  ) satisfies ChartConfig

  return (
    <NeonGlassCard accent="orange" animatePreset="page" className="flex h-full flex-col">
      <NeonCardHeader
        accent="orange"
        title="Review verdicts"
        description="Distribution across recent analyses"
        className="px-4 pt-4"
      />
      <div className="min-h-[260px] flex-1 px-2 pb-4">
        {hasData ? (
          <ChartContainer config={chartConfig} className="mx-auto h-[260px] w-full aspect-auto">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent nameKey="name" />} />
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} stroke="transparent" />
                ))}
                <LabelList
                  dataKey="value"
                  className="fill-white"
                  stroke="none"
                  fontSize={11}
                  formatter={(value: number) => (value > 0 ? value : "")}
                />
              </Pie>
            </PieChart>
          </ChartContainer>
        ) : (
          <div className="flex h-[260px] items-center justify-center text-sm text-slate-500">
            No triage verdicts yet
          </div>
        )}
      </div>
    </NeonGlassCard>
  )
}

export function DashboardPriorityChart({
  items,
}: {
  items: CountByPriority[]
}) {
  const data = priorityChartData(items)
  const hasData = data.some((d) => d.count > 0)
  const chartConfig = Object.fromEntries(
    data.map((d) => [d.priority, { label: d.priority, color: d.fill }])
  ) satisfies ChartConfig

  return (
    <NeonGlassCard accent="violet" animatePreset="page" className="flex h-full flex-col">
      <NeonCardHeader
        accent="violet"
        title="Investigation priority"
        description="Severity mix from triage scoring"
        className="px-4 pt-4"
      />
      <div className="min-h-[260px] flex-1 px-2 pb-4">
        {hasData ? (
          <ChartContainer config={chartConfig} className="h-[260px] w-full aspect-auto">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ left: 8, right: 16, top: 8, bottom: 0 }}
            >
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="priority"
                tickLine={false}
                axisLine={false}
                width={72}
                tick={{ fill: "#94a3b8", fontSize: 12 }}
              />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {data.map((entry) => (
                  <Cell key={entry.priority} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>
        ) : (
          <div className="flex h-[260px] items-center justify-center text-sm text-slate-500">
            No priority data yet
          </div>
        )}
      </div>
    </NeonGlassCard>
  )
}
