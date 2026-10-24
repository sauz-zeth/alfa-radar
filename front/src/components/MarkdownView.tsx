import { useMemo, type ReactNode } from "react";
import "./markdown.css";

type Align = "left" | "center" | "right";

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "table"; headers: string[]; alignments: Align[]; rows: string[][] }
  | { type: "code"; language: string; code: string }
  | { type: "quote"; text: string }
  | { type: "hr" };

const LIST_RE = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
const HEADING_RE = /^(#{1,6})\s+(.*)$/;
const FENCE_RE = /^```([\w-]*)\s*$/;
const HR_RE = /^\s*([-*_])(?:\s*\1){2,}\s*$/;
const INLINE_RE =
  /(\*\*[^*]+\*\*|__[^_]+__|~~[^~]+~~|`[^`]+`|\[[^\]]+\]\([^)]+\)|\*[^*]+\*|_[^_]+_)/g;

function isTableSeparator(line: string): boolean {
  const cells = splitTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function splitTableRow(line: string): string[] {
  let value = line.trim();
  if (value.startsWith("|")) value = value.slice(1);
  if (value.endsWith("|")) value = value.slice(0, -1);
  const cells: string[] = [];
  let current = "";
  let escaped = false;
  for (const char of value) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }
    if (char === "\\") {
      escaped = true;
      continue;
    }
    if (char === "|") {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }
  cells.push(current.trim());
  return cells;
}

function alignmentOf(cell: string): Align {
  const trimmed = cell.trim();
  if (trimmed.startsWith(":") && trimmed.endsWith(":")) return "center";
  if (trimmed.endsWith(":")) return "right";
  return "left";
}

function startsBlock(line: string, next: string | undefined): boolean {
  return (
    HEADING_RE.test(line) ||
    FENCE_RE.test(line) ||
    /^\s*>\s?/.test(line) ||
    LIST_RE.test(line) ||
    HR_RE.test(line) ||
    (line.includes("|") && next !== undefined && isTableSeparator(next))
  );
}

function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(FENCE_RE);
    if (fence) {
      const code: string[] = [];
      let cursor = index + 1;
      while (cursor < lines.length && !/^```\s*$/.test(lines[cursor] ?? "")) {
        code.push(lines[cursor] ?? "");
        cursor += 1;
      }
      blocks.push({ type: "code", language: fence[1] ?? "", code: code.join("\n") });
      index = Math.min(cursor + 1, lines.length);
      continue;
    }

    const heading = line.match(HEADING_RE);
    if (heading) {
      blocks.push({
        type: "heading",
        level: Math.min(6, heading[1]?.length ?? 1),
        text: (heading[2] ?? "").replace(/\s+#+\s*$/, ""),
      });
      index += 1;
      continue;
    }

    if (HR_RE.test(line)) {
      blocks.push({ type: "hr" });
      index += 1;
      continue;
    }

    const next = lines[index + 1];
    if (line.includes("|") && next !== undefined && isTableSeparator(next)) {
      const headers = splitTableRow(line);
      const alignments = splitTableRow(next).map(alignmentOf);
      const rows: string[][] = [];
      let cursor = index + 2;
      while (cursor < lines.length) {
        const row = lines[cursor] ?? "";
        if (!row.trim() || !row.includes("|")) break;
        rows.push(splitTableRow(row));
        cursor += 1;
      }
      blocks.push({ type: "table", headers, alignments, rows });
      index = cursor;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote: string[] = [];
      let cursor = index;
      while (cursor < lines.length && /^\s*>\s?/.test(lines[cursor] ?? "")) {
        quote.push((lines[cursor] ?? "").replace(/^\s*>\s?/, ""));
        cursor += 1;
      }
      blocks.push({ type: "quote", text: quote.join(" ") });
      index = cursor;
      continue;
    }

    const list = line.match(LIST_RE);
    if (list) {
      const ordered = /^\d/.test(list[2] ?? "");
      const items: string[] = [];
      let cursor = index;
      while (cursor < lines.length) {
        const item = (lines[cursor] ?? "").match(LIST_RE);
        if (!item || /^\d/.test(item[2] ?? "") !== ordered) break;
        items.push(item[3] ?? "");
        cursor += 1;
      }
      blocks.push({ type: "list", ordered, items });
      index = cursor;
      continue;
    }

    const paragraph: string[] = [];
    let cursor = index;
    while (cursor < lines.length) {
      const current = lines[cursor] ?? "";
      if (!current.trim()) break;
      if (cursor > index && startsBlock(current, lines[cursor + 1])) break;
      paragraph.push(current.trim());
      cursor += 1;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    index = cursor;
  }

  return blocks;
}

function safeHref(url: string): string | null {
  try {
    const parsed = new URL(url, window.location.origin);
    return ["http:", "https:", "mailto:"].includes(parsed.protocol) ? url : null;
  } catch {
    return null;
  }
}

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let key = 0;
  const pattern = new RegExp(INLINE_RE.source, "g");
  let match = pattern.exec(text);
  while (match) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];
    key += 1;

    if (token.startsWith("**") || token.startsWith("__")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("~~")) {
      nodes.push(<del key={key}>{token.slice(2, -2)}</del>);
    } else if (token.startsWith("`")) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("[")) {
      const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      const href = link ? safeHref(link[2] ?? "") : null;
      if (link && href) {
        nodes.push(
          <a
            key={key}
            href={href}
            target={href.startsWith("mailto:") ? undefined : "_blank"}
            rel="noreferrer"
          >
            {link[1]}
          </a>,
        );
      } else {
        nodes.push(token);
      }
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }

    last = match.index + token.length;
    match = pattern.exec(text);
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function renderBlock(block: Block, index: number): ReactNode {
  switch (block.type) {
    case "heading": {
      const Tag = `h${block.level}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
      return <Tag key={index}>{renderInline(block.text)}</Tag>;
    }
    case "paragraph":
      return <p key={index}>{renderInline(block.text)}</p>;
    case "list": {
      const Tag = block.ordered ? "ol" : "ul";
      return (
        <Tag key={index}>
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item)}</li>
          ))}
        </Tag>
      );
    }
    case "table":
      return (
        <div key={index} className="markdown-table-wrap">
          <table>
            <thead>
              <tr>
                {block.headers.map((header, cellIndex) => (
                  <th
                    key={cellIndex}
                    className={`is-${block.alignments[cellIndex] ?? "left"}`}
                  >
                    {renderInline(header)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {block.headers.map((_, cellIndex) => (
                    <td
                      key={cellIndex}
                      className={`is-${block.alignments[cellIndex] ?? "left"}`}
                    >
                      {renderInline(row[cellIndex] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "code":
      return (
        <pre key={index}>
          <code className={block.language ? `language-${block.language}` : undefined}>
            {block.code}
          </code>
        </pre>
      );
    case "quote":
      return <blockquote key={index}>{renderInline(block.text)}</blockquote>;
    case "hr":
      return <hr key={index} />;
  }
}

export function MarkdownView({
  markdown,
  className,
}: {
  markdown: string;
  className?: string;
}) {
  const blocks = useMemo(() => parseMarkdown(markdown), [markdown]);
  if (!markdown.trim()) return null;
  return (
    <div className={className ? `markdown-body ${className}` : "markdown-body"}>
      {blocks.map(renderBlock)}
    </div>
  );
}
