import type { Lineage } from "./api";

type Props = {
  lineage: Lineage;
  changedDataset: string | null;
  changedColumn: string | null;
  affected: string[];
};

const short = (name: string) => name.split(".").slice(-1)[0];

export default function LineageGraph({ lineage, changedDataset, changedColumn, affected }: Props) {
  const sources = lineage.datasets.filter((d) => d.role === "source");
  const report = lineage.datasets.find((d) => d.role === "report")!;
  const affectedSet = new Set(affected);

  const BOX_W = 168;
  const SRC_H = 74;
  const srcX = 16;
  const srcRightX = srcX + BOX_W;
  const srcY = (i: number) => 20 + i * 104;
  const srcCenter = (i: number) => srcY(i) + SRC_H / 2;

  const repX = 486;
  const repW = 232;
  const repY = 12;
  const rowStart = 58;
  const rowStep = 32;
  const colY = (i: number) => repY + rowStart + i * rowStep;

  const path = (x1: number, y1: number, x2: number, y2: number) => {
    const mx = (x1 + x2) / 2;
    return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
  };

  const height = repY + rowStart + report.columns.length * rowStep + 8;

  return (
    <svg className="lineage-svg" viewBox={`0 0 734 ${height}`} role="img"
         aria-label="Column lineage from source tables to the margin report, with the drift path highlighted">
      {/* base dataset edges */}
      {sources.map((s, i) => (
        <path key={`base-${s.name}`} className="edge"
              d={path(srcRightX, srcCenter(i), repX, repY + 40)} />
      ))}

      {/* drift paths: changed dataset -> each affected report column */}
      {changedDataset &&
        sources.map((s, i) =>
          s.name === changedDataset
            ? report.columns.map((c, ci) =>
                affectedSet.has(c.name) ? (
                  <path key={`drift-${c.name}`} className="edge drift"
                        d={path(srcRightX, srcCenter(i), repX, colY(ci) + 10)} />
                ) : null
              )
            : null
        )}

      {/* source dataset boxes */}
      {sources.map((s, i) => {
        const hot = s.name === changedDataset;
        return (
          <g key={s.name}>
            <rect className={`node${hot ? " hot" : ""}`} x={srcX} y={srcY(i)} width={BOX_W} height={SRC_H} rx={6} />
            <text className="node-title" x={srcX + 12} y={srcY(i) + 24}>{short(s.name)}</text>
            <text className="node-sub" x={srcX + 12} y={srcY(i) + 42}>{s.name.split(".").slice(0, -1).join(".")}</text>
            {hot && changedColumn && (
              <text className="node-col hot" x={srcX + 12} y={srcY(i) + 62}>▸ {changedColumn}</text>
            )}
          </g>
        );
      })}

      {/* report box with columns */}
      <rect className="node report" x={repX} y={repY} width={repW} height={height - repY - 4} rx={7} />
      <text className="node-title" x={repX + 14} y={repY + 26}>{short(report.name)}</text>
      <text className="node-sub" x={repX + 14} y={repY + 43}>daily regulatory margin report</text>
      {report.columns.map((c, ci) => {
        const hit = affectedSet.has(c.name);
        return (
          <g key={c.name}>
            {hit && <rect className="row-hit" x={repX + 6} y={colY(ci) - 8} width={repW - 12} height={24} rx={4} />}
            <circle className={`bullet${hit ? " hit" : ""}`} cx={repX + 18} cy={colY(ci) + 4} r={3} />
            <text className={`col-name${hit ? " hit" : ""}`} x={repX + 30} y={colY(ci) + 8}>{c.name}</text>
          </g>
        );
      })}
    </svg>
  );
}
