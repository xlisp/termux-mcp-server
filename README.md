# Termux MCP Server

通过 MCP 协议让 Claude Desktop 远程控制 Android 手机。运行在 Termux 上，提供 30+ 工具。

## 功能

| 分类 | 工具 | 说明 |
|------|------|------|
| 📱 设备信息 | `get_battery_status` `get_device_info` `get_storage_info` | 电池、型号、存储 |
| 📍 定位 | `get_location` | GPS/网络定位 |
| 📶 网络 | `get_wifi_info` `scan_wifi` `get_telephony_info` | WiFi、蜂窝网络 |
| 📦 应用 | `list_android_packages` `open_app` `open_url` `list_running_apps` | 查看/启动应用 |
| 📷 相机/图片 | `take_photo` `get_camera_info` `list_photos` `read_photo` | 拍照、浏览图片 |
| 💬 通信 | `list_sms` `send_sms` `list_contacts` | 短信、通讯录 |
| 📋 剪贴板 | `get_clipboard` `set_clipboard` | 读写剪贴板 |
| 🔔 通知 | `send_notification` `show_toast` | 发送通知/Toast |
| 🔊 系统控制 | `set_volume` `get_volume` `toggle_torch` `vibrate` | 音量、手电筒、震动 |
| 🗣️ TTS | `text_to_speech` | 文字转语音 |
| 🎵 媒体 | `media_player` | 播放/暂停/停止音频 |
| 📁 文件 | `list_directory` `read_file` `write_file` | 文件读写 |
| ⚡ 命令 | `execute_command` | 执行Shell命令 |
| 🔆 屏幕 | `get_screen_brightness` `set_screen_brightness` | 屏幕亮度 |
| 📡 传感器 | `get_sensor_list` `read_sensor` | 读取传感器数据 |
| 🔗 分享 | `share_file` `download_file` | 分享/下载文件 |
| 🔐 生物识别 | `get_fingerprint` | 指纹认证 |

## 安装

### 1. 手机端 (Termux)

```bash
# 安装依赖
pkg install python termux-api

# 安装 Termux:API app (从 F-Droid)
# https://f-droid.org/packages/com.termux.api/

# 授予存储权限
termux-setup-storage

# 进入项目目录
cd ~/pypro/termux-mcp-server

# 创建虚拟环境并安装
python -m venv .venv
source .venv/bin/activate
pip install "mcp[cli]"

# 测试运行
python termux_mcp_server.py
```

### 2. 远程连接 (SSH)

手机端启动 SSH 服务供电脑连接：

```bash
pkg install openssh
sshd  # 默认端口 8022
whoami  # 记住用户名
passwd  # 设置密码
ifconfig  # 记住IP地址
```

### 3. 电脑端 Claude Desktop 配置

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "termux": {
      "command": "ssh",
      "args": [
        "-p", "8022",
        "u0_a123@192.168.1.100",
        "/data/data/com.termux/files/home/pypro/termux-mcp-server/.venv/bin/python",
        "/data/data/com.termux/files/home/pypro/termux-mcp-server/termux_mcp_server.py"
      ]
    }
  }
}
```

> 将 `u0_a123` 替换为 `whoami` 输出，`192.168.1.100` 替换为手机IP。

**免密登录（推荐）：**
```bash
# 电脑端
ssh-keygen -t ed25519
ssh-copy-id -p 8022 u0_a123@192.168.1.100
```

## 使用示例

连接成功后，可以在 Claude Desktop 中直接说：

- "查看手机电量"
- "手机现在连着什么WiFi"
- "打开微信"
- "给 13800138000 发短信说我到了"
- "拍一张照片"
- "手机里有什么图片"
- "打开手电筒"
- "手机在哪里"（获取GPS定位）
- "把手机音量调到5"
- "用手机说一句你好"

## 测试

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python termux_mcp_server.py
```
