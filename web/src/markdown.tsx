// A small Markdown reader for the legal documents in web/legal/: headings, paragraphs, lists, tables, quotes,
// rules, bold, italics, code and links. It builds React elements, never raw HTML, so a document can't inject a script.
import type { ReactNode } from "react";
import { go } from "./api";

const slug = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function inline(text: string, key: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g);
  return parts.filter(Boolean).map((part, i) => {
    const k = `${key}-${i}`;
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={k}>{inline(part.slice(2, -2), k)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={k}>{part.slice(1, -1)}</code>;
    const link = part.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/);
    if (link) {
      const [, label, href] = link;
      return href.startsWith("/")
        ? <a key={k} href={href} onClick={go(href)}>{label}</a>
        : <a key={k} href={href} target="_blank" rel="noreferrer">{label}</a>;
    }
    if (part.length > 2 && part.startsWith("*") && part.endsWith("*")) return <em key={k}>{part.slice(1, -1)}</em>;
    return part;
  });
}

const cells = (row: string) => row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

export function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const key = `b${i}`;
    if (!line.trim()) { i++; continue; }
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      const Tag = (["h1", "h2", "h3", "h4"] as const)[level - 1];
      out.push(<Tag key={key} id={slug(heading[2])}>{inline(heading[2], key)}</Tag>);
      i++;
      continue;
    }
    if (/^---+\s*$/.test(line)) { out.push(<hr key={key} />); i++; continue; }
    if (line.startsWith("|")) {
      const rows: string[] = [];
      while (i < lines.length && lines[i].startsWith("|")) rows.push(lines[i++]);
      const [head, , ...body] = rows; // the second row is the |---| line
      out.push(
        <div key={key} className="table-wrap">
          <table className="table">
            <thead><tr>{cells(head).map((c, j) => <th key={j}>{inline(c, `${key}h${j}`)}</th>)}</tr></thead>
            <tbody>{body.map((r, n) => <tr key={n}>{cells(r).map((c, j) => <td key={j}>{inline(c, `${key}r${n}c${j}`)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    const listItem = /^(\s*)(?:[-*]|\d+\.)\s+/;
    if (listItem.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items: string[] = [];
      while (i < lines.length && (listItem.test(lines[i]) || (lines[i].startsWith("  ") && lines[i].trim() && items.length))) {
        if (listItem.test(lines[i])) items.push(lines[i].replace(listItem, ""));
        else items[items.length - 1] += " " + lines[i].trim(); // a wrapped line continues its item
        i++;
      }
      const List = ordered ? "ol" : "ul";
      out.push(<List key={key}>{items.map((it, n) => <li key={n}>{inline(it, `${key}i${n}`)}</li>)}</List>);
      continue;
    }
    if (line.startsWith(">")) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].startsWith(">")) quote.push(lines[i++].replace(/^>\s?/, ""));
      out.push(<blockquote key={key}>{inline(quote.join(" "), key)}</blockquote>);
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\||>|---|\s*(?:[-*]|\d+\.)\s)/.test(lines[i])) para.push(lines[i++].trim());
    out.push(<p key={key}>{inline(para.join(" "), key)}</p>);
  }
  return <>{out}</>;
}
