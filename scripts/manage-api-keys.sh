#!/usr/bin/env bash
# APIキーの発行/削除/一覧を SSH 経由で EC2 上の .env.prod に反映する。
#
# 事前準備(環境変数):
#   export WORD_API_INSTANCE_ID=i-xxxx
#   export WORD_API_SSH_KEY=~/.ssh/word-api.pem
#   export AWS_REGION=ap-northeast-1
#
# 使い方:
#   scripts/manage-api-keys.sh list                   # 登録済みキーの末尾8桁を表示
#   scripts/manage-api-keys.sh add <label>            # 新しいキーを追加(ランダム生成)
#   scripts/manage-api-keys.sh remove <key_or_suffix> # 指定キー(または末尾一致)を削除
#
# 注意:
#   - EC2 が起動していないとSSH接続できないため、止まっていたら事前に起動する
#   - 変更後 systemctl restart word-api でサービス再起動(モデル再ロードに1-2分)
set -euo pipefail

: "${WORD_API_INSTANCE_ID:?set WORD_API_INSTANCE_ID}"
: "${WORD_API_SSH_KEY:?set WORD_API_SSH_KEY}"
: "${AWS_REGION:=ap-northeast-1}"

cmd=${1:-}
shift || true

ensure_running() {
  local state
  state=$(aws ec2 describe-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" \
          --query 'Reservations[0].Instances[0].State.Name' --output text)
  if [ "$state" != "running" ]; then
    echo "ec2 is $state — start it first with: aws ec2 start-instances --instance-ids $WORD_API_INSTANCE_ID --region $AWS_REGION" >&2
    exit 2
  fi
}

get_host() {
  aws ec2 describe-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
}

ssh_exec() {
  local host=$1; shift
  ssh -i "$WORD_API_SSH_KEY" -o StrictHostKeyChecking=accept-new ec2-user@"$host" "$@"
}

case "$cmd" in
  list)
    ensure_running
    host=$(get_host)
    ssh_exec "$host" "grep '^API_KEYS=' /home/ec2-user/word-api/.env.prod | sed 's/API_KEYS=//' | tr ',' '\n' | awk '{n=length(\$0); printf \"%d keys · ...%s\n\", NR, substr(\$0, n-7)}'"
    ;;
  add)
    label=${1:-}
    if [ -z "$label" ]; then
      echo "usage: $0 add <label>" >&2
      exit 2
    fi
    ensure_running
    host=$(get_host)
    new_key=$(openssl rand -hex 32)
    ssh_exec "$host" "cd /home/ec2-user/word-api && cur=\$(grep '^API_KEYS=' .env.prod | sed 's/API_KEYS=//') && sed -i 's|^API_KEYS=.*|API_KEYS='\$cur','\"$new_key\"'|' .env.prod && sudo systemctl restart word-api"
    echo "--- new API key (label: $label) ---"
    echo "$new_key"
    echo "--- service restarting, ready in ~1-2min ---"
    ;;
  remove)
    target=${1:-}
    if [ -z "$target" ]; then
      echo "usage: $0 remove <key_or_suffix>" >&2
      exit 2
    fi
    ensure_running
    host=$(get_host)
    ssh_exec "$host" "cd /home/ec2-user/word-api && cur=\$(grep '^API_KEYS=' .env.prod | sed 's/API_KEYS=//') && new=\$(echo \"\$cur\" | tr ',' '\n' | grep -v \"$target\" | paste -sd, -) && if [ -z \"\$new\" ]; then echo 'ERROR: refusing to remove last key' >&2; exit 1; fi && sed -i 's|^API_KEYS=.*|API_KEYS='\"\$new\"'|' .env.prod && sudo systemctl restart word-api && echo 'removed. service restarting...'"
    ;;
  *)
    echo "usage: $0 {list|add <label>|remove <key_or_suffix>}" >&2
    exit 2
    ;;
esac
