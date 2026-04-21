export type RelatedItem = {
  word: string;
  score: number;
  pos: string | null;
};

export type Meta = {
  model: string;
  cached: boolean;
  elapsed_ms: number;
};

export type RelatedResponse = {
  query: string;
  results: RelatedItem[];
  meta: Meta;
};

export type RelatedParams = {
  word: string;
  top_k?: number;
  min_score?: number;
  pos?: string[];
  use_stopwords?: boolean;
  exclude?: string[];
};

export type WordApiError = {
  error: string;
  word?: string;
  [k: string]: unknown;
};

function buildUrl(base: string, path: string, params: Record<string, string>) {
  const u = new URL(path, base);
  for (const [k, v] of Object.entries(params)) {
    if (v !== "") u.searchParams.set(k, v);
  }
  return u.toString();
}

export async function fetchRelated(params: RelatedParams): Promise<RelatedResponse> {
  const base = process.env.RELATION_WORD_API_URL;
  const key = process.env.RELATION_WORD_API_KEY;
  if (!base || !key) throw new Error("RELATION_WORD_API_URL / RELATION_WORD_API_KEY not configured");

  const query: Record<string, string> = {
    word: params.word,
    top_k: String(params.top_k ?? 10),
    min_score: String(params.min_score ?? 0.5),
  };
  if (params.pos && params.pos.length > 0) query.pos = params.pos.join(",");
  if (params.exclude && params.exclude.length > 0) query.exclude = params.exclude.join(",");
  if (params.use_stopwords === false) query.use_stopwords = "false";

  const url = buildUrl(base, "/v1/related", query);
  const res = await fetch(url, {
    headers: { "X-API-Key": key },
    cache: "no-store",
  });
  const body = await res.text();
  if (!res.ok) {
    let detail: unknown = body;
    try {
      detail = JSON.parse(body);
    } catch {}
    const err = new Error(`relation-word-api ${res.status}`) as Error & { status: number; detail: unknown };
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return JSON.parse(body) as RelatedResponse;
}
