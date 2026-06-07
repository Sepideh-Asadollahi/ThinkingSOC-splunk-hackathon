"use client"

import type { Components } from "react-markdown"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { tsocNativeScrollbarClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

const markdownComponents: Components = {
  table: ({ children }) => (
    <div
      className={cn(
        "my-3 max-w-full overflow-x-auto rounded-lg border border-white/10",
        tsocNativeScrollbarClasses
      )}
    >
      <table className="min-w-full border-collapse text-left text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-white/5 text-[10px] uppercase tracking-wide text-slate-400">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="border border-white/10 px-2 py-1.5 font-medium text-slate-200">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border border-white/10 px-2 py-1.5 align-top text-slate-300">{children}</td>
  ),
  tr: ({ children }) => <tr className="even:bg-white/[0.02]">{children}</tr>,
  pre: ({ children }) => (
    <pre
      className={cn(
        "my-2 overflow-x-auto rounded-lg border border-white/10 bg-black/50 p-3 font-mono text-xs leading-relaxed text-teal-100/90",
        tsocNativeScrollbarClasses
      )}
    >
      {children}
    </pre>
  ),
}

/** Render SAIA / LiteLLM fallback answers with GFM markdown (tables, code, emphasis). */
export function McpMarkdownContent({ content, className }: { content: string; className?: string }) {
  const trimmed = content.trim()
  if (!trimmed) return null

  return (
    <div
      className={cn(
        "mcp-markdown w-full min-w-0 space-y-3 text-sm leading-relaxed text-slate-300",
        "[&_h1]:text-base [&_h1]:font-semibold [&_h1]:text-slate-100",
        "[&_h2]:text-sm [&_h2]:font-semibold [&_h2]:text-slate-100",
        "[&_h3]:text-sm [&_h3]:font-medium [&_h3]:text-slate-200",
        "[&_strong]:font-semibold [&_strong]:text-slate-100",
        "[&_em]:italic [&_em]:text-slate-200",
        "[&_hr]:my-4 [&_hr]:border-white/10",
        "[&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5",
        "[&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5",
        "[&_p]:leading-relaxed",
        "[&_code]:rounded [&_code]:bg-black/40 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[11px] [&_code]:text-teal-200/90",
        "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-inherit",
        className
      )}
      data-testid="mcp-markdown-content"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {trimmed}
      </ReactMarkdown>
    </div>
  )
}
