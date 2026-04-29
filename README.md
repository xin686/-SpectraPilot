# 🔬 海洋光学 USB2000+ 光谱仪控制台

基于树莓派 4B + Python 的全功能光谱仪 Web 控制系统。

## 功能特性

| 功能 | 说明 |
|------|------|
| 实时光谱显示 | WebSocket 推送，刷新率可调（50ms ~ 2s） |
| 积分时间设置 | 滑杆控制，范围 1ms ~ 5000ms，实时生效 |
| 扫描平均 | 多次采集均值，降低噪声 |
| 暗背景扣除 | 自动从采集值中扣除热噪声 |
| 反射率测量 | 三步流程：暗背景 → 参考白板 → 样品 |
| 数据保存 | CSV（通用）/ HDF5（科研），含备注与时间戳 |
| 文件下载 | 浏览器一键下载保存的数据文件 |
| 模拟模式 | 无硬件时可用模拟信号测试界面 |
| 开机自启 | systemd 服务，断电重启自动恢复 |

## 快速开始

### 1. 一键安装
```bash
chmod +x install.sh
./install.sh
```

### 2. 手动安装
```bash
# 安装依赖
sudo apt install python3-pip python3-venv libusb-1.0-0-dev
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# USB 权限
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="2457", MODE="0666", GROUP="plugdev"' | \
  sudo tee /etc/udev/rules.d/99-oceanoptics.rules
sudo udevadm control --reload-rules

# 启动
python app.py
```

### 3. 访问界面
浏览器打开：`http://<树莓派IP>:5000`

## 反射率测量流程

1. 点击 **① 采集暗背景** — 盖住探头（或关闭光源）
2. 点击 **② 采集参考白板** — 将探头对准标准白板
3. 点击 **③ 测量反射率** — 将探头对准被测样品

公式：`R(%) = (样品 - 暗) / (参考 - 暗) × 100`

## 文件结构

```
spectrometer_app/
├── app.py              # Flask 主服务（REST + WebSocket）
├── spectrometer.py     # 设备驱动封装（含模拟模式）
├── storage.py          # CSV / HDF5 存储
├── requirements.txt    # Python 依赖
├── install.sh          # 一键安装脚本
├── templates/
│   └── index.html      # Web 控制界面
└── spectrometer_data/  # 数据输出目录（自动创建）
```

## 数据格式

### CSV
```
# 海洋光学 USB2000+ 数据
# 时间,20240101_120000
# 备注,样品A
wavelength_nm,intensity_counts
340.0000,512.0000
...
```

### HDF5
```
/
├── wavelengths         # float64 array, 单位 nm
├── intensity_counts    # float64 array（或 reflectance_pct）
└── attrs: instrument, timestamp, note
```

## API 参考

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/connect` | POST | `{"mock": false}` |
| `/api/integration_time` | POST | `{"ms": 100}` |
| `/api/scans_average` | POST | `{"count": 3}` |
| `/api/dark` | POST | 采集暗背景 |
| `/api/reference` | POST | 采集参考白板 |
| `/api/spectrum` | GET | 获取当前光谱 |
| `/api/reflectance` | GET | 获取反射率 |
| `/api/save` | POST | `{"type":"spectrum","format":"csv","note":""}` |
| `/api/files` | GET | 列出已保存文件 |
| `/api/download/<filename>` | GET | 下载文件 |

## 硬件要求

- 树莓派 4B（推荐 4GB RAM）
- 海洋光学 USB2000+（USB-A）
- Raspberry Pi OS Bullseye 或 Bookworm（64-bit）

## 许可

MIT License
