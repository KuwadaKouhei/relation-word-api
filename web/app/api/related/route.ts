import { NextRequest, NextResponse } from "next/server";
import { fetchRelated } from "@/lib/word-api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const word = sp.get("word");
  if (!word) {
    return NextResponse.json({ error: "missing_word" }, { status: 400 });
  }

  const top_k = Number(sp.get("top_k") ?? "10");
  const min_score = Number(sp.get("min_score") ?? "0.5");
  const pos = sp.get("pos") ? sp.get("pos")!.split(",").map(s => s.trim()).filter(Boolean) : undefined;
  const exclude = sp.get("exclude") ? sp.get("exclude")!.split(",").map(s => s.trim()).filter(Boolean) : undefined;
  const use_stopwords = sp.get("use_stopwords") !== "false";

  try {
    const data = await fetchRelated({ word, top_k, min_score, pos, exclude, use_stopwords });
    return NextResponse.json(data);
  } catch (e) {
    const err = e as Error & { status?: number; detail?: unknown };
    const status = err.status ?? 500;
    return NextResponse.json(
      { error: err.message, detail: err.detail ?? null },
      { status },
    );
  }
}
