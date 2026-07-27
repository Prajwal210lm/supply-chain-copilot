/* ---------------------------------------------------------------------------
   Minimal SQL tokenizer for display only. Not a parser — it never validates
   or rewrites the SQL, it just slices the string into spans so the compiled
   query is readable at a glance. The SQL itself is produced by the backend's
   compiler and is rendered verbatim.
--------------------------------------------------------------------------- */

export type SqlTokenKind = "kw" | "fn" | "str" | "num" | "param" | "comment" | "punct" | "text";
export type SqlToken = { kind: SqlTokenKind; text: string };

// Split into two sets so functions and clause keywords can be coloured
// differently — clause structure reads first, aggregates second.
const KEYWORDS = new Set(
  `SELECT FROM WHERE JOIN LEFT RIGHT INNER OUTER FULL CROSS ON AS AND OR NOT IN IS
   NULL GROUP ORDER BY HAVING LIMIT OFFSET UNION ALL DISTINCT CASE WHEN THEN ELSE
   END WITH VALUES EXISTS BETWEEN ASC DESC FILTER OVER PARTITION USING TRUE FALSE`
    .split(/\s+/)
    .filter(Boolean),
);

const FUNCTIONS = new Set(
  `COUNT SUM AVG MIN MAX ROUND CAST COALESCE NULLIF DATE_TRUNC EXTRACT ABS
   GREATEST LEAST LAG LEAD ROW_NUMBER`
    .split(/\s+/)
    .filter(Boolean),
);

// Order matters: comments and strings must win over word matching.
const PATTERN = /(--[^\n]*)|('(?:''|[^'])*')|(\?)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|([(),.;*=<>!|+\-/]+)/g;

export function tokenizeSql(sql: string): SqlToken[] {
  const out: SqlToken[] = [];
  let last = 0;

  for (const m of sql.matchAll(PATTERN)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push({ kind: "text", text: sql.slice(last, idx) });

    const [full, comment, str, param, num, word, punct] = m;
    if (comment) out.push({ kind: "comment", text: full });
    else if (str) out.push({ kind: "str", text: full });
    else if (param) out.push({ kind: "param", text: full });
    else if (num) out.push({ kind: "num", text: full });
    else if (word) {
      const upper = word.toUpperCase();
      if (KEYWORDS.has(upper)) out.push({ kind: "kw", text: full });
      else if (FUNCTIONS.has(upper)) out.push({ kind: "fn", text: full });
      else out.push({ kind: "text", text: full });
    } else if (punct) out.push({ kind: "punct", text: full });

    last = idx + full.length;
  }
  if (last < sql.length) out.push({ kind: "text", text: sql.slice(last) });
  return out;
}

/** Tokenize per line so a line-number gutter can stay aligned with the code. */
export function tokenizeSqlLines(sql: string): SqlToken[][] {
  return sql.split("\n").map(tokenizeSql);
}

export const SQL_TOKEN_CLASS: Record<SqlTokenKind, string> = {
  kw: "text-[#a9a2f5] font-medium",
  fn: "text-[#8fd6c4]",
  str: "text-[#e8b473]",
  num: "text-[#e8b473]",
  param: "rounded bg-[#3b3529] px-1 text-[#f0c987]",
  comment: "text-ink-on-code-muted italic",
  punct: "text-ink-on-code-muted",
  text: "",
};
