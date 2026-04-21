"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RelatedItem, RelatedResponse } from "@/lib/word-api";
import { searchRelated, type ClientOptions } from "@/lib/client-api";
import { SearchBar } from "./search-bar";
import { OptionsPanel } from "./options-panel";
import { ResultCards } from "./result-cards";
import { History } from "./history";

const DEFAULT_OPTIONS: ClientOptions = {
  top_k: 20,
  min_score: 0.5,
  pos: [],
  use_stopwords: true,
};

type HistoryEntry = { word: string; at: number };

export function Explorer() {
  const [input, setInput] = useState("");
  const [options, setOptions] = useState<ClientOptions>(DEFAULT_OPTIONS);
  const [response, setResponse] = useState<RelatedResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const doSearch = useCallback(
    async (word: string, opts: ClientOptions) => {
      const trimmed = word.trim();
      if (!trimmed) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setLoading(true);
      setError(null);
      try {
        const data = await searchRelated(trimmed, opts, ctrl.signal);
        setResponse(data);
        setHistory(prev => {
          const filtered = prev.filter(h => h.word !== trimmed);
          return [{ word: trimmed, at: Date.now() }, ...filtered].slice(0, 20);
        });
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setError((e as Error).message);
        setResponse(null);
      } finally {
        if (abortRef.current === ctrl) setLoading(false);
      }
    },
    [],
  );

  const handleSubmit = useCallback(() => {
    void doSearch(input, options);
  }, [doSearch, input, options]);

  const handleDrill = useCallback(
    (item: RelatedItem) => {
      setInput(item.word);
      void doSearch(item.word, options);
    },
    [doSearch, options],
  );

  const handleOptionsChange = useCallback(
    (next: ClientOptions) => {
      setOptions(next);
      // re-search with new options if we already have a query
      if (response) void doSearch(response.query, next);
    },
    [doSearch, response],
  );

  // friendly error mapping
  const prettyError = useMemo(() => {
    if (!error) return null;
    if (error === "word_not_in_vocab") return "その単語は語彙に含まれていません。別の表記で試してください。";
    if (error === "model_not_loaded") return "モデル読み込み中です。少し待って再試行してください。";
    if (error.startsWith("word-api 5")) return "APIサーバーがエラーを返しました。時間をおいて再試行してください。";
    if (error.startsWith("word-api 4")) return "リクエストが不正です。";
    return error;
  }, [error]);

  useEffect(() => {
    // cleanup in-flight request on unmount
    return () => abortRef.current?.abort();
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_240px] gap-6">
      <div className="space-y-4">
        <SearchBar
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          loading={loading}
        />
        <OptionsPanel options={options} onChange={handleOptionsChange} />

        {prettyError && (
          <div className="rounded-md border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200">
            {prettyError}
          </div>
        )}

        <ResultCards
          response={response}
          loading={loading}
          onDrill={handleDrill}
        />
      </div>
      <aside className="hidden md:block">
        <History
          entries={history}
          current={response?.query}
          onSelect={(word) => {
            setInput(word);
            void doSearch(word, options);
          }}
          onClear={() => setHistory([])}
        />
      </aside>
    </div>
  );
}
