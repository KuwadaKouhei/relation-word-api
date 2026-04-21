#!/usr/bin/env bash
# EC2 断続稼働用の起動/停止/状態確認ヘルパー。
#
# 事前準備:
#   1. aws cli インストール & `aws configure` 済み
#   2. 環境変数 WORD_API_INSTANCE_ID を設定(例: export WORD_API_INSTANCE_ID=i-0123456789abcdef0)
#   3. 環境変数 AWS_REGION を設定(例: export AWS_REGION=ap-northeast-1)
#
# 使い方:
#   deploy/ec2.sh start     # インスタンスを起動(課金開始)
#   deploy/ec2.sh stop      # 停止(EBS 代のみの課金に)
#   deploy/ec2.sh status    # 現在のステータスとパブリックDNSを表示
#   deploy/ec2.sh ssh       # SSH でログイン (要 WORD_API_SSH_KEY)
#
set -euo pipefail

: "${WORD_API_INSTANCE_ID:?set WORD_API_INSTANCE_ID to your EC2 instance id}"
: "${AWS_REGION:=ap-northeast-1}"

cmd=${1:-status}

case "$cmd" in
  start)
    aws ec2 start-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" >/dev/null
    echo "starting $WORD_API_INSTANCE_ID ... (takes ~30s)"
    aws ec2 wait instance-running --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION"
    aws ec2 wait instance-status-ok --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION"
    dns=$(aws ec2 describe-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" \
            --query 'Reservations[0].Instances[0].PublicDnsName' --output text)
    ip=$(aws ec2 describe-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" \
           --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    echo "running. public_dns=$dns public_ip=$ip"
    echo "NOTE: service takes another 1-2 minutes for API + model load."
    ;;
  stop)
    aws ec2 stop-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" >/dev/null
    echo "stopping $WORD_API_INSTANCE_ID ..."
    aws ec2 wait instance-stopped --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION"
    echo "stopped. only EBS will be billed."
    ;;
  status)
    aws ec2 describe-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" \
      --query 'Reservations[0].Instances[0].{state:State.Name,dns:PublicDnsName,ip:PublicIpAddress,type:InstanceType}' \
      --output table
    ;;
  ssh)
    : "${WORD_API_SSH_KEY:?set WORD_API_SSH_KEY to your .pem file path}"
    dns=$(aws ec2 describe-instances --instance-ids "$WORD_API_INSTANCE_ID" --region "$AWS_REGION" \
            --query 'Reservations[0].Instances[0].PublicDnsName' --output text)
    if [ -z "$dns" ] || [ "$dns" = "None" ]; then
      echo "instance is not running" >&2
      exit 1
    fi
    ssh -i "$WORD_API_SSH_KEY" "ec2-user@${dns}"
    ;;
  *)
    echo "usage: $0 {start|stop|status|ssh}" >&2
    exit 2
    ;;
esac
