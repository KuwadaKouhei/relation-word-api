"use client";

type Entry = { word: string; at: number };

type Props = {
  entries: Entry[];
  current: string | undefined;
  onSelect: (word: string) => void;
  onClear: () => void;
};

export function History({ entries, current, onSelect, onClear }: Props) {
  return (
    <div className="sticky top-6">
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-xs uppercase tracking-wider text-neutral-500">履歴</span>
        {entries.length > 0 && (
          <button
            onClick={onClear}
            className="text-[10px] text-neutral-500 hover:text-neutral-300"
          >
            クリア
          </button>
        )}
      </div>
      {entries.length === 0 ? (
        <div className="text-xs text-neutral-600 px-1">検索すると履歴が残ります</div>
      ) : (
        <ul className="scrollbar-thin overflow-y-auto max-h-[70vh] space-y-1 pr-1">
          {entries.map((e) => (
            <li key={`${e.word}-${e.at}`}>
              <button
                onClick={() => onSelect(e.word)}
                className={`w-full text-left px-2 py-1.5 rounded text-sm transition-colors ${
                  e.word === current
                    ? "bg-orange-500/10 text-orange-300"
                    : "text-neutral-300 hover:bg-neutral-900"
                }`}
              >
                {e.word}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
