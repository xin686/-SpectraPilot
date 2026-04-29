#!/bin/bash
# ============================================================
# 海洋光学 USB2000+ 光谱仪系统 — 一键安装脚本
# 适用于 Raspberry Pi OS (Bullseye / Bookworm)
# ============================================================
set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  USB2000+ 光谱仪系统 — 安装开始          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 1. 系统依赖
echo "[1/5] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv libusb-1.0-0-dev git

# 2. udev 规则（USB2000+ VID: 2457）
echo "[2/5] 配置 USB 设备权限..."
sudo tee /etc/udev/rules.d/99-oceanoptics.rules > /dev/null <<EOF
SUBSYSTEM=="usb", ATTR{idVendor}=="2457", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules
sudo usermod -aG plugdev "$USER" 2>/dev/null || true

# 3. Python 虚拟环境
echo "[3/5] 创建 Python 虚拟环境..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m venv "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"

# 4. Python 依赖
echo "[4/5] 安装 Python 依赖（可能需要几分钟）..."
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q

# 5. systemd 服务（可选）
echo "[5/5] 注册开机自启动服务..."
PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"

sudo tee /etc/systemd/system/spectrometer.service > /dev/null <<EOF
[Unit]
Description=Ocean Optics USB2000+ Spectrometer Web App
After=network.target

[Service]
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_BIN $SCRIPT_DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable spectrometer.service

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  安装完成！                              ║"
echo "╠══════════════════════════════════════════╣"
echo "║  手动启动:                               ║"
echo "║    source venv/bin/activate              ║"
echo "║    python app.py                         ║"
echo "║                                          ║"
echo "║  服务管理:                               ║"
echo "║    sudo systemctl start spectrometer     ║"
echo "║    sudo systemctl stop spectrometer      ║"
echo "║    sudo systemctl status spectrometer    ║"
echo "║                                          ║"
echo "║  访问地址: http://localhost:5000         ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "⚠  请重新插拔 USB 设备后再启动服务"
echo ""
