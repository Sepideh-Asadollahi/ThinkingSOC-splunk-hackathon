export type AccentColor = "teal" | "violet" | "orange"

export type SectionId =
  | "dashboard"
  | "inventory"
  | "relationships"
  | "analysis"
  | "splunk"

const THEME_ACCENTS: Record<SectionId, AccentColor> = {
  dashboard: "teal",
  inventory: "teal",
  relationships: "violet",
  analysis: "orange",
  splunk: "teal",
}

export function getAccent(sectionId: SectionId): AccentColor {
  return THEME_ACCENTS[sectionId] ?? "teal"
}
