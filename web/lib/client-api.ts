import type { RelatedResponse } from "@/lib/relation-word-api";

export type ClientOptions = {
  top_k: number;
  min_score: number;
  pos: string[];
  use_stopwords: boolean;
};

export async function searchRelated(
  word: string,
  opts: ClientOptions,
  signal?: AbortSignal,
): Promise<RelatedResponse> {
  const params = new URLSearchParams({
    word,
    top_k: String(opts.top_k),
    min_score: String(opts.min_score),
  });
  if (opts.pos.length > 0) params.set("pos", opts.pos.join(","));
  if (!opts.use_stopwords) params.set("use_stopwords", "false");

  const res = await fetch(`/api/related?${params.toString()}`, { signal });
  const body = await res.json();
  if (!res.ok) {
    const msg = body?.detail?.detail?.error ?? body?.detail?.error ?? body?.error ?? `http ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return body as RelatedResponse;
}
