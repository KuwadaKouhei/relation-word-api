"use client";

import type { RelatedItem, RelatedResponse } from "@/lib/relation-word-api";

type Props = {
  response: RelatedResponse | null;
  loading: boolean;
  onDrill: (item: RelatedItem) => void;
};

function scoreColor(score: number) {
  if (score >= 0.8) return "text-orange-300";
  if (score >= 0.7) return "text-amber-300";
  if (score >= 0.6) return "text-yellow-300/80";
  return "text-neutral-400";
}

export function ResultCards({ response, loading, onDrill }: Props) {
  if (loading && !response) {
    return <SkeletonGrid />;
  }
  if (!response) {
    return (
      <div className="text-sm text-neutral-500 px-1 pt-4">
        単語を入力して検索すると、ここに関連語が並びます。
      </div>
    );
  }
  if (response.results.length === 0) {
    return (
      <div className="text-sm text-neutral-400 px-1 pt-4">
        条件に合う関連語がありませんでした。類似度の下限を下げてみてください。
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <Meta response={response} />
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {response.results.map((r, i) => (
          <button
            key={`${r.word}-${i}`}
            onClick={() => onDrill(r)}
            className="group text-left rounded-md border border-neutral-800 bg-neutral-900/60 px-3 py-2.5 hover:border-orange-500/60 hover:bg-neutral-800/80 transition-colors animate-fade-in-up"
            style={{ animationDelay: `${Math.min(i * 20, 300)}ms` }}
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-medium truncate group-hover:text-orange-300 transition-colors">
                {r.word}
              </span>
              <span className={`text-xs tabular-nums ${scoreColor(r.score)}`}>
                {r.score.toFixed(3)}
              </span>
            </div>
            {r.pos && (
              <div className="text-[10px] text-neutral-500 mt-0.5">{r.pos}</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function Meta({ response }: { response: RelatedResponse }) {
  return (
    <div className="flex items-center gap-3 text-xs text-neutral-500">
      <span>
        <span className="text-neutral-300 font-medium">{response.query}</span> の関連語
      </span>
      <span className="text-neutral-700">·</span>
      <span>{response.results.length} 件</span>
      <span className="text-neutral-700">·</span>
      <span>{response.meta.elapsed_ms}ms</span>
      {response.meta.cached && (
        <>
          <span className="text-neutral-700">·</span>
          <span className="text-emerald-400/70">キャッシュ</span>
        </>
      )}
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 pt-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="rounded-md border border-neutral-800 bg-neutral-900/40 h-[52px] animate-pulse"
        />
      ))}
    </div>
  );
}
