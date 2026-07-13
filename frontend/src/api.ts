const BASE = import.meta.env.VITE_API_BASE ?? "";

export type Scenario = {
  id: string;
  label: string;
  dataset: string;
  column: string;
  change_type: string;
  detail: string;
};

export type ColumnDef = { name: string; type: string; native: string; description: string };
export type DatasetNode = { name: string; urn: string; role: "source" | "report"; columns: ColumnDef[] };
export type ColumnEdge = {
  source_dataset: string;
  source_column: string;
  target_dataset: string;
  target_column: string;
  transform: string;
};
export type Lineage = {
  datasets: DatasetNode[];
  column_edges: ColumnEdge[];
  dataset_edges: { source: string; target: string }[];
  report: string;
};

export type Affected = { dataset: string; column: string; transform: string; hops: number };
export type Analysis = {
  dataset: string;
  column: string;
  change_type: string;
  detail: string;
  severity: "hard_break" | "silent_break";
  breaks: boolean;
  summary: string;
  affected: Affected[];
};

export type Narration =
  | { available: false; reason: string }
  | { available: true; narrative: string; business_impact: string; contract: string; remediation: string };

export type WriteResult = {
  ok: boolean;
  live: boolean;
  columns_annotated: number;
  tags_written: number;
  details: string[];
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

type ChangeBody = { dataset: string; column: string; change_type: string; detail: string };

export const api = {
  lineage: () => get<Lineage>("/api/lineage"),
  scenarios: () => get<Scenario[]>("/api/scenarios"),
  analyze: (c: ChangeBody) => post<Analysis>("/api/analyze", c),
  narrate: (c: ChangeBody) => post<Narration>("/api/narrate", c),
  writeback: (c: ChangeBody) => post<WriteResult>("/api/writeback", c),
};
