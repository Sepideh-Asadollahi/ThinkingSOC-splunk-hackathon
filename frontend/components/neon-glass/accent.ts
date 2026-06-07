export type NeonAccent = "teal" | "violet" | "orange"

export type AccentClasses = {
  text: string
  textMuted: string
  gradientTitle: string
  iconBox: string
  border: string
  borderHover: string
  bgSubtle: string
  ring: string
  gradientFromOverlay: string
  buttonOutline: string
  /** Main panel: soft border + light gradient glow (not harsh flat white). */
  panelBorder: string
  panelGlow: string
  panelBorderGradient: string
  panelDivider: string
}

const ACCENT_MAP: Record<NeonAccent, AccentClasses> = {
  teal: {
    text: "text-teal-400",
    textMuted: "text-teal-400/80",
    gradientTitle:
      "text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-teal-400/90",
    iconBox: "rounded-lg bg-teal-500/10 border border-teal-500/20 p-2",
    border: "border-teal-500/20",
    borderHover: "hover:border-teal-500/40",
    bgSubtle: "bg-teal-500/10",
    ring: "focus-visible:ring-teal-500/20 focus-visible:border-teal-500/50",
    gradientFromOverlay: "from-teal-500/[22.5%]",
    buttonOutline:
      "border-teal-500/40 text-teal-300 hover:bg-teal-500/10 hover:border-teal-500/60 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-teal-500/[7.5%]",
    panelBorder: "border-white/[0.07]",
    panelGlow:
      "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06),0_0_0_1px_rgba(255,255,255,0.04),0_12px_40px_-16px_rgba(20,184,166,0.11),0_2px_12px_-6px_rgba(0,0,0,0.35)]",
    panelBorderGradient:
      "from-white/[0.1] via-teal-400/[0.06] to-transparent",
    panelDivider: "border-b border-white/[0.06]",
  },
  violet: {
    text: "text-violet-400",
    textMuted: "text-violet-400/80",
    gradientTitle:
      "text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-violet-400/90",
    iconBox: "rounded-lg bg-violet-500/10 border border-violet-500/20 p-2",
    border: "border-violet-500/20",
    borderHover: "hover:border-violet-500/40",
    bgSubtle: "bg-violet-500/10",
    ring: "focus-visible:ring-violet-500/20 focus-visible:border-violet-500/50",
    gradientFromOverlay: "from-violet-500/[22.5%]",
    buttonOutline:
      "border-violet-500/40 text-violet-300 hover:bg-violet-500/10 hover:border-violet-500/60 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-violet-500/[7.5%]",
    panelBorder: "border-white/[0.07]",
    panelGlow:
      "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06),0_0_0_1px_rgba(255,255,255,0.04),0_12px_40px_-16px_rgba(139,92,246,0.11),0_2px_12px_-6px_rgba(0,0,0,0.35)]",
    panelBorderGradient:
      "from-white/[0.1] via-violet-400/[0.06] to-transparent",
    panelDivider: "border-b border-white/[0.06]",
  },
  orange: {
    text: "text-orange-400",
    textMuted: "text-orange-400/80",
    gradientTitle:
      "text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-orange-400/90",
    iconBox: "rounded-lg bg-orange-500/10 border border-orange-500/20 p-2",
    border: "border-orange-500/20",
    borderHover: "hover:border-orange-500/40",
    bgSubtle: "bg-orange-500/10",
    ring: "focus-visible:ring-orange-500/20 focus-visible:border-orange-500/50",
    gradientFromOverlay: "from-orange-500/[22.5%]",
    buttonOutline:
      "border-orange-500/40 text-orange-300 hover:bg-orange-500/10 hover:border-orange-500/60 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-orange-500/[7.5%]",
    panelBorder: "border-white/[0.07]",
    panelGlow:
      "shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06),0_0_0_1px_rgba(255,255,255,0.04),0_12px_40px_-16px_rgba(249,115,22,0.11),0_2px_12px_-6px_rgba(0,0,0,0.35)]",
    panelBorderGradient:
      "from-white/[0.1] via-orange-400/[0.06] to-transparent",
    panelDivider: "border-b border-white/[0.06]",
  },
}

export function getAccentClasses(accent: NeonAccent = "teal"): AccentClasses {
  return ACCENT_MAP[accent]
}
