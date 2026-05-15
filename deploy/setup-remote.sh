#!/bin/bash
# 在远端裸服务器上首次部署 lilibear-transcard。
#
# 用法（在本地）：
#   1) 配置远端的 SSH 免密登录或 sshpass
#   2) 默认 DOMAIN=transcard.xmu-cuisine.club，REPO=Deep-Thinks/lilibear-transcard
#      sshpass -p 'a1b2c3d4<>++' ssh root@101.33.32.162 'bash -s' < deploy/setup-remote.sh
#   3) 把本地 .env 拷过去：
#      sshpass -p 'a1b2c3d4<>++' scp .env root@101.33.32.162:/opt/lilibear_transcard/.env
#   4) 申请 HTTPS 证书（DNS A 记录必须先做好）：
#      sshpass -p 'a1b2c3d4<>++' ssh root@101.33.32.162 \
#        "certbot --nginx -d transcard.xmu-cuisine.club --redirect --agree-tos -m dev@xmu-cuisine.club -n"
#   5) 启动：
#      sshpass -p 'a1b2c3d4<>++' ssh root@101.33.32.162 "systemctl start transcard && systemctl status transcard"
#
# 注意：脚本不会写 .env，需要部署后手动拷贝本地 .env 内容到 /opt/lilibear_transcard/.env。

set -euo pipefail

PROJECT="${PROJECT:-/opt/lilibear_transcard}"
REPO="${REPO:-https://github.com/Deep-Thinks/lilibear-transcard.git}"
DOMAIN="${DOMAIN:-transcard.xmu-cuisine.club}"

echo "==> 检查依赖"
command -v python3 >/dev/null || { echo "需要 python3"; exit 1; }
command -v nginx >/dev/null || { echo "需要 nginx（请先 apt install nginx）"; exit 1; }
command -v git >/dev/null || { echo "需要 git"; exit 1; }

echo "==> 安装 Python 依赖（仅 Pillow 用于读取长宽比；其余走标准库）"
apt-get install -y python3-pil 2>/dev/null || \
    python3 -m pip install --break-system-packages Pillow

echo "==> 克隆代码到 $PROJECT"
if [ -d "$PROJECT/.git" ]; then
    echo "    项目目录已存在，跳过 clone"
else
    mkdir -p "$(dirname "$PROJECT")"
    git clone "$REPO" "$PROJECT"
fi

echo "==> 准备 logs 目录"
mkdir -p "$PROJECT/logs/images"

echo "==> 装 post-merge git hook"
cp "$PROJECT/deploy/post-merge" "$PROJECT/.git/hooks/post-merge"
chmod +x "$PROJECT/.git/hooks/post-merge"

echo "==> 装 systemd unit"
cp "$PROJECT/deploy/transcard.service" /etc/systemd/system/transcard.service
systemctl daemon-reload
systemctl enable transcard

echo "==> 装 nginx vhost（HTTP only，certbot 后续会改成 HTTPS）"
sed "s/transcard.xmu-cuisine.club/$DOMAIN/g" "$PROJECT/deploy/nginx-transcard.conf" \
    > /etc/nginx/sites-available/$DOMAIN
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN
nginx -t

echo "==> 重载 nginx"
systemctl reload nginx

echo ""
echo "✅ 自动化完成。剩下三步手动操作："
echo ""
echo "  1) 写 .env：在 $PROJECT/.env 填入 IMAGE_API_KEY / GEMINI_API_KEY"
echo "     从本地拷贝："
echo "       sshpass -p '<root密码>' scp .env root@<remote>:$PROJECT/.env"
echo ""
echo "  2) 申请 HTTPS 证书（DNS A 记录必须先做好）："
echo "       certbot --nginx -d $DOMAIN --redirect --agree-tos -m dev@xmu-cuisine.club -n"
echo ""
echo "  3) 启动服务："
echo "       systemctl start transcard"
echo "       systemctl status transcard"
echo "       journalctl -u transcard -f"
