// SVG-side mirror of the color tokens in app/globals.css. Recharts sets
// fill/stroke as SVG presentation ATTRIBUTES, which cannot resolve CSS
// var() — so charts import these constants instead. If a value changes
// in globals.css, change it here too; these two files are the only
// places a color literal may appear.
export const chart = {
  accent: "#4338ca", // --accent
  positive: "#15803d", // --positive
  negative: "#b91c1c", // --negative
  neutral: "#52525b", // --neutral
  grid: "#e3e3de", // gridlines legible on --surface-sunken
  axisLine: "#d4d4cf", // --border-emphasis
  tick: "#8e8e99", // --text-muted
  tickSoft: "#52525b", // --text-secondary
  cursor: "#dcdcf2", // --border-machine
  cursorFill: "rgba(67, 56, 202, 0.05)",
} as const;
