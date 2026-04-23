# Relation Word API

単語(日本語)を渡すと関連性のある言葉・連想語を返す API。
chiVe の日本語単語埋め込みをベースに類似語を返します。


## 設計と思想
### なぜ作ったのか
起源は
- 自動生成されるマインドマップアプリを作りたいという思い
- 「連想」という人間のらしい考え方をプログラミングで実装出来るのかという興味
この思いをもとにAIに壁打ちしながらアプローチと技術選定を行った。

### 必須要件
今回APIを設計する上で必須要件として以下を挙げた。
- 日本語に対応していること
- 人間が見ても連想されていると感じるワードを返すこと
- 別プロジェクト([MindSource](https://github.com/KuwadaKouhei/MindSource))でAPIを使用することを視野にいれ、使いやすい形で設計すること

## このプロジェクトの技術領域

Claude Codeと壁打ちを行い、要件を満たす技術アプローチと技術領域を選定

### 技術アプローチ
「連想」をアルゴリズム的にアプローチするには以下の要素を用いる
- 日本語の単語を取り込んだ辞書ファイルにベクトルを埋め込む
- ベクトル近傍検索（ANN）を用いて意味が近い言葉を検索

### 自然言語処理 (NLP)

| 技術 | 役割 | 選定理由 |
| ---- | ---- | -------- |
| chiVe | 日本語単語埋め込み (約130万〜250万語) | 日本語特化・学習済み公開モデル。自前学習を避ける |
| gensim KeyedVectors | ベクトルのロード・類似度計算 | chiVe が `.kv` 形式。`mmap="r"` で常駐メモリ削減 |
| SudachiPy | 形態素解析・品詞フィルタ | chiVe の学習時トークナイザと揃えて語彙ヒット率を上げる |

### ベクトル近傍探索 (ANN)

| 技術 | 役割 | 選定理由 |
| ---- | ---- | -------- |
| gensim 線形探索 | 既定パス (~120ms/req) | 追加依存ゼロ。インデックス未構築でも動作 |
| hnswlib | 近似最近傍 (5〜10倍高速化) | 軽量 (C++ コア)。FAISS は ARM64 で依存過剰 |

### Web API / バックエンド

| 技術 | 役割 | 選定理由 |
| ---- | ---- | -------- |
| FastAPI + gunicorn/uvicorn | API サーバ | Pydantic 直結・OpenAPI 自動生成。本番はワーカ複数でコア使い切り |
| Redis | レート制限カウンタ + 共有キャッシュ | 複数ワーカ横断でレート制限/キャッシュを共有 |
| slowapi | レート制限実装 | FastAPI 統合。429 + `Retry-After` 標準対応 |
| X-API-Key 認証 | プロジェクト単位の認可 | 共有 API 用途。OAuth/JWT はオーバースペック |

### インフラ / 運用

| 技術 | 役割 | 選定理由 |
| ---- | ---- | -------- |
| Docker / docker-compose | 環境統一 | ネイティブ依存 (hnswlib, Sudachi) の吸収。本番/ローカル同構成 |
| AWS EC2 t4g.large | 本番ホスト | モデル常駐で数 GB 使うためサーバーレス不向き。Graviton で安価 |
| Caddy | HTTPS 終端 | Let's Encrypt 自動更新がゼロ設定 |
| Prometheus | メトリクス | `prometheus-fastapi-instrumentator` で `/metrics` が即立つ |
| structlog | 構造化ログ | `request_id` コンテキスト付与が宣言的。`X-Request-Id` と相関 |

### 付属フロントエンド

`web/` に検索 UI が同居。動作確認兼デモ。

## 本番エンドポイント

デプロイ済みの共有APIです。新しいプロジェクトからは **パターンA(共通バックエンド方式)** でそのまま利用できます。

- **エンドポイント**: `https://13-193-92-78.nip.io`
- **Swagger UI**: `https://13-193-92-78.nip.io/docs`
- **認証**: `X-API-Key` ヘッダ
- **インフラ**: AWS EC2 t4g.large (ap-northeast-1) + Elastic IP
- **運用**: 断続稼働(使わないときは EC2 停止)

**他プロジェクトから利用する方法** → [docs/CLIENTS.md](docs/CLIENTS.md)

**新規プロジェクト向けのAPIキー発行**:

```bash
./scripts/manage-api-keys.sh add my-new-project
```

## Web フロントエンド

この API を叩くシンプルな検索UIが `web/` に同居しています。
単語を入れるとカードで関連語が並び、クリックで深堀り検索できます。

- ローカル起動: `cd web && npm install && npm run dev`
- 詳細: [web/README.md](web/README.md)

## 構成

- FastAPI + gunicorn/uvicorn
- gensim KeyedVectors (chiVe)
- hnswlib (オプショナルなANN近似最近傍検索)
- SudachiPy (日本語形態素解析 + 品詞フィルタ)
- Redis (レート制限 + 共有キャッシュ)
- slowapi (レート制限)
- Prometheus (メトリクス)
- structlog (構造化ログ + request_id トラッキング)

## クイックスタート (Docker)

1. chiVe モデルを `./models/chive-1.3-mc5_gensim/` 配下に配置
   - `chive-1.3-mc5.kv`
   - `chive-1.3-mc5.kv.vectors.npy`
2. `.env` を作成

   ```bash
   cp .env.example .env
   ```

3. 起動

   ```bash
   docker compose up --build
   ```

4. レディ確認

   ```bash
   curl http://localhost:8000/v1/ready
   ```

## API

### `GET /v1/related`

```bash
curl -H "X-API-Key: dev-key-1" \
  "http://localhost:8000/v1/related?word=猫&top_k=5&min_score=0.5"
```

パラメータ:

| 名前 | 型 | 既定 | 説明 |
| ---- | -- | ---- | ---- |
| `word` | string | (必須) | 対象単語 |
| `top_k` | int | 10 | 返却件数 (最大100) |
| `min_score` | float | 0.5 | 類似度閾値 |
| `exclude` | string | - | カンマ区切りで除外語 |
| `pos` | string | - | 品詞フィルタ (例: `名詞,動詞,形容詞`) |
| `use_stopwords` | bool | true | システム既定ストップワードを除外 |

### `GET /v1/similarity`

```bash
curl -H "X-API-Key: dev-key-1" \
  "http://localhost:8000/v1/similarity?word1=猫&word2=犬"
```

### `POST /v1/related/batch`

```bash
curl -H "X-API-Key: dev-key-1" -H "Content-Type: application/json" \
  -d '{"items":[{"word":"猫"},{"word":"犬"}],"top_k":5,"min_score":0.5}' \
  http://localhost:8000/v1/related/batch
```

### `POST /v1/analogy`

アナロジー検索(ベクトル演算)。例: `女王 - 王 + 男 ≒ 女`

```bash
curl -H "X-API-Key: dev-key-1" -H "Content-Type: application/json" \
  -d '{"positive":["女王","男"],"negative":["王"],"top_k":5}' \
  http://localhost:8000/v1/analogy
```

### `POST /v1/cascade`

多世代連想探索。1単語から連想を `depth` 世代繰り返し、DAGグラフとして返します。

```bash
curl -H "X-API-Key: dev-key-1" -H "Content-Type: application/json" \
  -d '{"word":"猫","depth":2,"top_k":3}' \
  http://localhost:8000/v1/cascade
```

主要パラメータ:

- `word` (必須): 起点の単語
- `depth` (1-4、既定2): 連想を繰り返す世代数
- `top_k` (1-20、既定5): 各世代・各親から取る連想語数(全世代共通)
- `top_k_per_gen` (任意): 世代別の件数指定。配列長 = depth。例: `[10, 5, 3]`
- `min_score` (0.0-1.0、既定0.5): 類似度下限(全世代共通)
- `pos` (任意): 品詞フィルタ。例: `["名詞"]`
- `exclude` (任意): 除外語の配列
- `use_stopwords` (既定true): 既定ストップワード除外
- `max_nodes` (10-500、既定200): 総ノード数の上限。到達で `meta.truncated=true`

レスポンスは `nodes`(各ノード: `id`, `word`, `generation`, `score`, `parent`)と `edges`(`from`, `to`, `score`)のグラフ形式。同じ単語は1ノードに集約(DAG化)。

### `GET /v1/health` / `GET /v1/ready`

readiness はモデルロード完了で 200 を返します。

### `GET /metrics`

Prometheus エクスポジション形式のメトリクス。リクエスト数、レイテンシ分布など。

## 認証 / レート制限

- APIキーは `X-API-Key` ヘッダで送信
- 既定レート制限: `60/minute` (`.env` の `RATE_LIMIT_DEFAULT` で変更)
- 超過時は 429 + `Retry-After` ヘッダ

## ANN インデックス(オプション・性能向上用)

デフォルトは gensim の線形探索(130万語で ~120ms/req)。スループットが必要な場合は
hnswlib インデックスを事前構築すると 5-10倍高速化できます。

1. インデックスをビルド(初回のみ、250万語で約10分)

   Docker 経由(推奨・hnswlib を別途インストール不要):

   ```bash
   docker compose exec api python scripts/build_ann_index.py
   ```

   ローカル Python で直接:

   ```bash
   py scripts/build_ann_index.py
   ```

   `models/chive-1.3-mc5_gensim/chive-1.3-mc5.ann.bin` と `.labels.npy` が生成されます。

2. `docker-compose.yml` / `.env` で以下の環境変数が設定されていることを確認
   (既定で設定済み)

   ```env
   ANN_INDEX_PATH=/models/chive-1.3-mc5_gensim/chive-1.3-mc5.ann.bin
   ANN_LABELS_PATH=/models/chive-1.3-mc5_gensim/chive-1.3-mc5.labels.npy
   ```

3. API を再起動すると自動で ANN を利用

   ```bash
   docker compose restart api
   ```

   起動ログの `ann_available=true` を確認。

ファイルが無い/未設定の場合は自動で gensim フォールバックになるため、手順をスキップしても動作します。

## 開発

```bash
pip install -e ".[dev]"
pytest
```

テストはダミー埋め込みで API を回すので、実モデルファイル無しで全パスします。

## ログ

JSON 構造化ログを stdout に出力。各リクエストに `request_id` が付与され、レスポンスヘッダ `X-Request-Id` で相関可能。

```json
{"request_id":"8ca84c85e2c045c1","path":"/v1/related","method":"GET","status":200,"elapsed_ms":42,"event":"request_complete"}
```

## 今後の展望
- 連想精度の向上
- 応答速度の高速化

- 品詞タグに基づくカテゴリ絞り込み(語彙クラスタリング)
- NSFW/差別語フィルタ
- 文脈考慮 (BERT系とのハイブリッド)
- PostgreSQL での APIキー管理・利用量課金
- Sentry 統合
- Cloud Run / AWS App Runner / ECS Fargate へのデプロイ
