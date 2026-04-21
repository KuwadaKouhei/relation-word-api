# AWS EC2 断続稼働デプロイ手順

個人利用・コスト最優先で、必要なときだけ EC2 を起動する運用向け。
月額目安は **稼働時だけ $1-5**(停止中は EBS 代のみ約 $3/月)。

## 目次

1. [前提条件](#前提条件)
2. [AWS 側の初期構築(初回のみ)](#aws-側の初期構築初回のみ)
3. [初回デプロイ](#初回デプロイ)
4. [日常運用(起動/停止)](#日常運用起動停止)
5. [更新デプロイ](#更新デプロイ)
6. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

- AWS アカウント + IAM ユーザ(`EC2FullAccess` と `IAMReadOnlyAccess` 相当)
- ローカルに `aws cli` 設定済み(`aws configure`)
- SSH 鍵ペアを AWS で作成済み(`.pem` ファイルを安全な場所に保管)
- モデルファイル (`models/chive-1.3-mc5_gensim/*` 合計 6.6GB) をローカル保持

---

## AWS 側の初期構築(初回のみ)

### 1. セキュリティグループ作成

```bash
aws ec2 create-security-group \
  --group-name relation-word-api-sg \
  --description "relation-word-api public" \
  --region ap-northeast-1

# 22 (SSH, 自分のIPのみ) / 80 (Let's Encrypt) / 443 (HTTPS)
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress --group-name relation-word-api-sg \
  --protocol tcp --port 22 --cidr "${MY_IP}/32"
aws ec2 authorize-security-group-ingress --group-name relation-word-api-sg \
  --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name relation-word-api-sg \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

### 2. EC2 インスタンス作成

推奨スペック(モデル全量を mmap):

| 用途 | タイプ | vCPU | メモリ | 月額(稼働100%) |
|------|-------|------|-------|----------------|
| 断続稼働(推奨) | **t4g.large** | 2 | 8GB | 約 $24(1日1hなら $1) |
| 軽量化モデル用 | t4g.medium | 2 | 4GB | 約 $12 |

**注意**: chiVe mc5 + ANN インデックスは合計 6.6GB。t4g.medium (4GB) では swap 前提の動作になるため、個人利用でも **t4g.large 推奨**。

```bash
# Amazon Linux 2023 ARM の最新 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-arm64" "Name=state,Values=available" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' --output text \
  --region ap-northeast-1)

aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type t4g.large \
  --key-name <YOUR_KEY_NAME> \
  --security-groups relation-word-api-sg \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=30,VolumeType=gp3}' \
  --user-data file://cloud-init.yaml \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=relation-word-api}]' \
  --region ap-northeast-1
```

出力 `InstanceId` (`i-xxxx`) を控える。

### 3. ローカル環境変数設定

```bash
export RELATION_WORD_API_INSTANCE_ID=i-xxxxxxxxxxxxxxxxx
export RELATION_WORD_API_SSH_KEY=~/.ssh/relation-word-api.pem
export AWS_REGION=ap-northeast-1
```

---

## 初回デプロイ

### 1. インスタンス起動

```bash
./deploy/ec2.sh start
```

インスタンスが `running` になった後、cloud-init が完走するまで 1-2 分待つ。

### 2. コードとモデルを転送

**重要**: モデルファイルは 6.6GB あるのでアップロードに時間がかかる(回線次第で10分〜1時間)。
初回は S3 経由を推奨(再開可能・並列DL可)。

```bash
# S3 バケット作成
aws s3 mb s3://my-relation-word-api-models --region ap-northeast-1

# ローカルからアップロード
aws s3 sync ./models s3://my-relation-word-api-models/models \
  --exclude "*" --include "chive-1.3-mc5*"

# EC2 にログインして S3 から同期
./deploy/ec2.sh ssh
# --- 以下は EC2 内 ---
cd relation-word-api
aws configure  # EC2ロール無し運用なら一時的にキー入れる(後述 IAM Role を推奨)
aws s3 sync s3://my-relation-word-api-models/models ./models
exit
```

**IAM Role 推奨**: EC2 に S3 読み取り Role を付与すれば `aws configure` 不要で `aws s3 sync` できる。

### 3. アプリソース転送

```bash
DNS=$(aws ec2 describe-instances --instance-ids "$RELATION_WORD_API_INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicDnsName' --output text)

# モデル以外を rsync で転送
rsync -avz -e "ssh -i $RELATION_WORD_API_SSH_KEY" \
  --exclude models --exclude __pycache__ --exclude .venv --exclude .env \
  ./ "ec2-user@${DNS}:~/relation-word-api/"
```

### 4. 本番 .env 作成

```bash
./deploy/ec2.sh ssh
# --- EC2 内 ---
cd relation-word-api
cp .env.prod.example .env.prod

# API キー生成
echo "API_KEYS=$(openssl rand -hex 32)" >> .env.prod

# ドメインなしで試す場合(自己署名 TLS)
# Caddyfile の 1行目を `{$DOMAIN}` → `:443` に変えて、
# その下に `tls internal` を追加。詳細は下記参照。

# nip.io を使う場合(独自ドメイン不要、EC2 IPでTLS自動取得)
IP=$(curl -s https://checkip.amazonaws.com)
echo "DOMAIN=${IP}.nip.io" >> .env.prod
```

### 5. systemd 登録 + 起動

```bash
# --- EC2 内(継続) ---
sudo cp deploy/relation-word-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable relation-word-api
sudo systemctl start relation-word-api

# 起動確認(初回はモデルロードに 1-2 分)
docker compose -f docker-compose.prod.yml logs -f api
# ann_available=true が見えたら Ctrl+C で抜ける
```

### 6. 動作確認

```bash
# EC2 内から
curl -H "X-API-Key: <your-api-key>" \
  "https://${DOMAIN}/v1/related?word=猫&top_k=5"

# ローカル PC から(証明書の検証が必要)
curl -H "X-API-Key: <your-api-key>" \
  "https://your-domain.nip.io/v1/related?word=猫&top_k=5"
```

---

## 日常運用(起動/停止)

### 使いたいとき

```bash
./deploy/ec2.sh start
# 約1分後、https://<domain>/ が使える
```

### 使い終わったら必ず停止

```bash
./deploy/ec2.sh stop
# 停止中は EBS 30GB = 月約$3 のみ
```

### 状態確認

```bash
./deploy/ec2.sh status
```

### 自動停止(安心のため)

EventBridge で「毎日深夜 0:00 に停止」を設定すると消し忘れを防げる:

```bash
# 保存予定スケジュール(cron 形式・UTC)
# 日本時間 0:00 = UTC 15:00
aws scheduler create-schedule --name relation-word-api-auto-stop \
  --schedule-expression 'cron(0 15 * * ? *)' \
  --target '{"Arn":"arn:aws:scheduler:::aws-sdk:ec2:stopInstances","RoleArn":"<ROLE_ARN>","Input":"{\"InstanceIds\":[\"i-xxx\"]}"}' \
  --flexible-time-window '{"Mode":"OFF"}'
```

---

## 更新デプロイ

コード変更を反映するとき:

```bash
./deploy/ec2.sh start   # まだ停止中なら起動
DNS=$(aws ec2 describe-instances --instance-ids "$RELATION_WORD_API_INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicDnsName' --output text)

# コード転送(モデルは再送不要)
rsync -avz -e "ssh -i $RELATION_WORD_API_SSH_KEY" \
  --exclude models --exclude __pycache__ --exclude .venv --exclude .env \
  ./ "ec2-user@${DNS}:~/relation-word-api/"

# 再ビルド & 再起動
./deploy/ec2.sh ssh
cd relation-word-api
docker compose -f docker-compose.prod.yml up -d --build api
```

---

## トラブルシューティング

### 起動時のモデルロードで OOM kill される

t4g.medium (4GB) 使用時に発生しやすい。cloud-init で 2GB swap を追加済みだが、
不足なら swap を 4GB に拡張するか t4g.large に昇格する。

### Caddy が TLS 取得に失敗する

- ポート 80 / 443 が SG で開いているか
- `DOMAIN` が EC2 の実パブリックIPに解決されるか (`dig api.example.com` で確認)
- `docker compose logs caddy` で Let's Encrypt のエラー内容確認

nip.io 使用時は `DOMAIN=<IP>.nip.io` の形式で、IPが変わるたびに変更要。
**Elastic IP を割り当て**ておくと IP 固定できる(月約$0〜$3.6。関連付け中は無料、未関連付け時のみ課金)。

### 料金が想定より高い

- `aws ec2 describe-instances` で停止していない古いインスタンスが残っていないか確認
- EBS ボリュームが未アタッチで残っていないか(`aws ec2 describe-volumes --filters "Name=status,Values=available"`)
- Elastic IP が未関連付けで残っていないか(`aws ec2 describe-addresses`)

### SSH 接続できない

- `./deploy/ec2.sh status` で状態確認
- Public IP が再起動で変わっているので、`$DNS` を取り直す
- SG の 22 番が自宅IPに開いているか(自宅IP変更時は更新要)

---

## コスト試算(ap-northeast-1, 2026年想定)

| 項目 | オンデマンド | 断続稼働 (日1h×30日) |
|------|------------|---------------------|
| t4g.large | $0.0544/h × 730h = $39.7 | $0.0544 × 30 = **$1.63** |
| EBS gp3 30GB | $3.6 | $3.6 |
| データ転送 1GB/月 | $0.114 | $0.114 |
| **合計** | **約$43** | **約$5.3** |

Elastic IP 使用時は関連付け中は無料、停止時は $3.6/月追加で合計 **約$9/月** 程度。
