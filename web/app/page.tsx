import { Explorer } from "@/components/explorer";

export default function Home() {
  return (
    <main className="flex-1 px-4 py-8 md:px-8 md:py-12 max-w-6xl mx-auto w-full">
      <header className="mb-8">
        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">
          関連語エクスプローラー
        </h1>
        <p className="text-sm text-neutral-400 mt-1">
          単語を入力すると、chiVe 単語埋め込みから意味的に近い語を探します。カードをクリックでさらに掘り下げ。
        </p>
      </header>
      <Explorer />
      <footer className="mt-16 text-xs text-neutral-500 border-t border-neutral-800 pt-4">
        Backed by chiVe v1.3 mc5 + hnswlib ANN · 2,530,791 vocab
      </footer>
    </main>
  );
}
