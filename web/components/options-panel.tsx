"use client";

import { useState } from "react";
import type { ClientOptions } from "@/lib/client-api";

type Props = {
  options: ClientOptions;
  onChange: (next: ClientOptions) => void;
};

const POS_CHOICES = ["名詞", "動詞", "形容詞", "副詞"];
const TOP_K_CHOICES = [10, 20, 50, 100];

export function OptionsPanel({ options, onChange }: Props) {
  const [open, setOpen] = useState(false);

  function togglePos(p: string) {
    const next = options.pos.includes(p)
      ? options.pos.filter((x) => x !== p)
      : [...options.pos, p];
    onChange({ ...options, pos: next });
  }

  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-900/50">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full px-4 py-2 text-sm text-left text-neutral-400 hover:text-neutral-200 transition-colors flex items-center justify-between"
      >
        <span>オプション</span>
        <span className="text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="border-t border-neutral-800 px-4 py-4 space-y-4 text-sm">
          <div>
            <label className="block text-neutral-400 mb-2">件数</label>
            <div className="flex gap-2">
              {TOP_K_CHOICES.map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => onChange({ ...options, top_k: k })}
                  className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                    options.top_k === k
                      ? "bg-orange-500 border-orange-500 text-white"
                      : "bg-transparent border-neutral-700 text-neutral-300 hover:border-neutral-500"
                  }`}
                >
                  {k}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-neutral-400 mb-2">
              類似度の下限: <span className="text-neutral-200 tabular-nums">{options.min_score.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={options.min_score}
              onChange={(e) => onChange({ ...options, min_score: Number(e.target.value) })}
              className="w-full accent-orange-500"
            />
          </div>

          <div>
            <label className="block text-neutral-400 mb-2">品詞フィルタ</label>
            <div className="flex flex-wrap gap-2">
              {POS_CHOICES.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => togglePos(p)}
                  className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                    options.pos.includes(p)
                      ? "bg-orange-500 border-orange-500 text-white"
                      : "bg-transparent border-neutral-700 text-neutral-300 hover:border-neutral-500"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="stopwords"
              type="checkbox"
              checked={options.use_stopwords}
              onChange={(e) => onChange({ ...options, use_stopwords: e.target.checked })}
              className="accent-orange-500"
            />
            <label htmlFor="stopwords" className="text-neutral-300 cursor-pointer">
              ノイズ語(代名詞・古語表記等)を除外
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
