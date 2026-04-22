import type { SalesGauge } from "../lib/leadDisplay";

export function ScoreGauge({ gauge }: { gauge: SalesGauge }) {
  const { value, tier } = gauge;
  const bar =
    tier === "success"
      ? "from-emerald-500 to-teal-400"
      : tier === "danger"
        ? "from-rose-600 to-red-500"
        : "from-zinc-500 to-zinc-400";
  const ring =
    tier === "success"
      ? "text-emerald-400/90"
      : tier === "danger"
        ? "text-rose-400"
        : "text-zinc-400";

  return (
    <div className="flex flex-col items-end gap-1 min-w-[5.5rem]">
      <div className="flex items-baseline gap-1">
        <span className={`text-base font-bold tabular-nums ${ring}`}>{value}</span>
        <span className="text-[10px] text-zinc-600">/100</span>
      </div>
      <div className="w-full h-2 rounded-full bg-zinc-800/90 overflow-hidden border border-zinc-700/50">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${bar} transition-all duration-500 ease-out`}
          style={{ width: `${Math.min(100, Math.max(4, value))}%` }}
        />
      </div>
      <span className="text-[9px] uppercase tracking-wider text-zinc-600">Score IA</span>
    </div>
  );
}
