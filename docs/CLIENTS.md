# Word Relation API — クライアント統合ガイド

このAPIは公開HTTPSエンドポイントとして運用しているため、任意のプロジェクト・任意の言語から呼び出せます。本ドキュメントは **新しいプロジェクトで本APIを利用する手順** を示します。

## 基本情報

| 項目 | 値 |
|------|----|
| エンドポイント | `https://13-193-92-78.nip.io` |
| 認証 | `X-API-Key` HTTPヘッダ |
| CORS | 未設定(ブラウザ直接呼び出し不可。サーバーサイド経由必須) |
| レート制限 | 30 req/分(APIキー単位) |
| 可用性 | 断続稼働(使わないときは EC2 停止 → API 応答不可) |

## 新プロジェクトを始めるときの流れ

1. **APIキーを発行**(既存キーの流用は非推奨):
   ```bash
   ./scripts/manage-api-keys.sh add my-new-project
   ```
   → 出力された32バイト hex 文字列を新プロジェクトの環境変数に設定
2. **EC2が停止中なら起動**:
   ```bash
   aws ec2 start-instances --instance-ids i-0ac9d2d3c9f25f35c --region ap-northeast-1
   ```
   起動後約1分で API が応答開始
3. 新プロジェクトで API を呼び出す(下記サンプル参照)
4. 使い終わったら EC2 停止
   ```bash
   aws ec2 stop-instances --instance-ids i-0ac9d2d3c9f25f35c --region ap-northeast-1
   ```

## サンプルコード

### Node.js / Next.js (サーバーサイド)

```ts
const res = await fetch(
  `${process.env.WORD_API_URL}/v1/related?word=${encodeURIComponent("猫")}&top_k=10`,
  { headers: { "X-API-Key": process.env.WORD_API_KEY! } },
);
const data = await res.json();
console.log(data.results);
```

### Python

```python
import os, requests

resp = requests.get(
    f"{os.environ['WORD_API_URL']}/v1/related",
    params={"word": "猫", "top_k": 10, "pos": "名詞"},
    headers={"X-API-Key": os.environ["WORD_API_KEY"]},
    timeout=5,
)
resp.raise_for_status()
print(resp.json()["results"])
```

### curl

```bash
curl -H "X-API-Key: $WORD_API_KEY" \
  "https://13-193-92-78.nip.io/v1/related?word=猫&top_k=10&pos=名詞"
```

### Bash ワンライナー(URLエンコード込み)

```bash
enc() { printf "%s" "$1" | od -An -tx1 | tr -d ' \n' | sed 's/../%&/g'; }
curl -H "X-API-Key: $WORD_API_KEY" \
  "https://13-193-92-78.nip.io/v1/related?word=$(enc 猫)&top_k=5"
```

## エンドポイント一覧

| メソッド | パス | 用途 |
|---------|------|------|
| GET | `/v1/related` | 関連語取得(メイン) |
| GET | `/v1/similarity` | 2語間の類似度 |
| POST | `/v1/related/batch` | 複数単語を一括処理 |
| POST | `/v1/analogy` | アナロジー検索(ベクトル演算) |
| POST | `/v1/cascade` | 多世代連想探索(1単語から連想を depth 世代繰り返し、DAG グラフで返却) |
| GET | `/v1/health` | 生存確認 |
| GET | `/v1/ready` | モデルロード完了確認 |
| GET | `/metrics` | Prometheus 形式メトリクス(認証不要) |

詳細は Swagger UI: `https://13-193-92-78.nip.io/docs`

## 推奨プラクティス

- **APIキーを複数プロジェクトで共有しない**。漏洩時にピンポイントで無効化できるよう、プロジェクトごとに発行する
- **サーバーサイドから呼ぶ**。CORS 未設定のためブラウザから直接叩くと失敗する。Next.js の Route Handler や Cloudflare Workers 等でプロキシを作る
- **キャッシュ活用**。同じ単語は結果をTTLCache/Redisで再利用する(API側でも既に1日キャッシュしているが、クライアント側でも重ねるとベター)
- **リトライ**。一時的な 502/503(EC2起動直後のモデルロード中等)に備えて、指数バックオフリトライを組み込む
- **404 は語彙外**。`word_not_in_vocab` エラーは正常な動作。ユーザー向けには「別の表記で試してください」と案内

## レート制限・エラーコード

| コード | 原因 | 対応 |
|-------|------|------|
| 200 | 成功 | - |
| 400 | パラメータ不正 | リクエスト見直し |
| 401 | APIキー無効/欠落 | `X-API-Key` を確認 |
| 404 | `word_not_in_vocab` | 別の表記で試す |
| 429 | レート制限超過 | `Retry-After` ヘッダ秒数待機 |
| 502/503 | モデルロード中 or EC2起動中 | 数秒後にリトライ |

## リソース制約

本APIの制約は以下の通りです(本番運用で意識する必要あり):

- **語彙**: chiVe v1.3 mc5 の 2,530,791 語。低頻度語や新語・専門用語は含まれない可能性あり
- **言語**: 日本語のみ
- **単語正規化**: Sudachi で正規化されるため、「走った」→「走る」のように活用形は原形に変換される
- **サイズ**: `word` パラメータは 64 文字まで
- **バッチ**: `/v1/related/batch` は1リクエスト最大50語まで

## 開発中のトラブルシュート

**`Connection refused` / タイムアウト**
→ EC2が停止中。`aws ec2 start-instances ...` で起動 → 1分待つ

**401 が返る**
→ APIキーが無効化されている可能性。`./scripts/manage-api-keys.sh list` で有効なキーを確認

**429 が頻発する**
→ デフォルト 30/分 は控えめ。大量アクセス予定なら `.env.prod` の `RATE_LIMIT_DEFAULT` を変更(例: `300/minute`)して `systemctl restart word-api`
