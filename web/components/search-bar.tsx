"use client";

import { FormEvent, KeyboardEvent } from "react";

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
};

export function SearchBar({ value, onChange, onSubmit, loading }: Props) {
  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit();
  }
  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      onSubmit();
    }
  }
  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        inputMode="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        placeholder="例: 猫、音楽、走る、東京..."
        className="flex-1 rounded-md bg-neutral-900 border border-neutral-800 px-4 py-3 text-base placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-orange-500/60 focus:border-orange-500/60"
        autoFocus
        maxLength={64}
      />
      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="rounded-md bg-orange-500 px-5 py-3 text-sm font-medium text-white disabled:bg-neutral-700 disabled:text-neutral-400 enabled:hover:bg-orange-400 transition-colors"
      >
        {loading ? "検索中..." : "検索"}
      </button>
    </form>
  );
}
