# 関連語エクスプローラー (Web)

chiVe 日本語単語埋め込みをベースにした `relation-word-api` のフロントエンド。
Next.js 16 + React 19 + Tailwind CSS v4。

## 特徴

- 検索ボックスに単語を入れると、意味的に近い語がカードで並ぶ
- カードをクリックして連想を深掘り(履歴付き)
- 件数 / 類似度下限 / 品詞フィルタ / ストップワード除外をオプションで調整
- APIキーは**サーバーサイド(Route Handler)**のみで利用、ブラウザには露出しない

## ローカル開発

```bash
cp .env.local.example .env.local
# .env.local を編集して RELATION_WORD_API_URL / RELATION_WORD_API_KEY を設定

npm install
npm run dev
```

`http://localhost:3000` でアクセス。

## 環境変数

| 変数 | 必須 | 用途 |
| --- | --- | --- |
| `RELATION_WORD_API_URL` | ✓ | relation-word-api のベース URL(例: `https://api.example.com`) |
| `RELATION_WORD_API_KEY` | ✓ | relation-word-api が発行した API キー。サーバーサイドのみ参照 |

## ディレクトリ

```
app/
├── api/related/route.ts   # relation-word-api へのプロキシ Route Handler
├── layout.tsx             # ルートレイアウト(ダークテーマ)
└── page.tsx               # トップページ(サーバーコンポーネント)
components/
├── explorer.tsx           # 検索状態・履歴管理の親コンポーネント
├── search-bar.tsx         # 入力 + 送信ボタン
├── options-panel.tsx      # 折りたたみ式オプション
├── result-cards.tsx       # 関連語カードグリッド
└── history.tsx            # 検索履歴サイドバー
lib/
├── relation-word-api.ts   # サーバーサイド用 fetcher + 型
└── client-api.ts          # ブラウザ → /api/related クライアント
```

## Vercel へのデプロイ

### 1. Vercel にプロジェクトを作る

リポジトリをGitHubに push したあと:

```bash
npx vercel --cwd . link
npx vercel --cwd . env add RELATION_WORD_API_URL production
npx vercel --cwd . env add RELATION_WORD_API_KEY production
npx vercel --cwd . deploy --prod
```

または `vercel.com` のコンソールから:

1. New Project → このリポジトリを import
2. **Root Directory** を `web` に設定(relation-word-api モノレポなので重要)
3. Framework Preset: **Next.js**(自動検出)
4. Environment Variables:
   - `RELATION_WORD_API_URL` = `https://<your-nip.io-domain>`
   - `RELATION_WORD_API_KEY` = `<your-api-key>`
5. Deploy

### 2. 注意

- relation-word-api が **EC2 断続稼働** の場合、EC2 停止中はフロントから叩いても 502/504 になります
- EC2 の Public IP が変わるたびに `RELATION_WORD_API_URL` の再設定が必要(Elastic IP 化を検討)
