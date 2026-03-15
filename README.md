# Termux MCP Server

通过 MCP 协议让 Claude Desktop 远程控制 Android 手机。运行在 Termux 上，提供 **45+ 工具**，支持 UI 自动化操作。

## 功能

| 分类 | 工具 | 说明 |
|------|------|------|
| 📱 设备信息 | `get_battery_status` `get_device_info` `get_storage_info` | 电池、型号、存储 |
| 📍 定位 | `get_location` | GPS/网络定位 |
| 📶 网络 | `get_wifi_info` `scan_wifi` `get_telephony_info` | WiFi、蜂窝网络 |
| 📦 应用 | `list_android_packages` `open_app` `open_url` `get_current_app` | 查看/启动应用 |
| 🖥️ UI自动化 | `take_screenshot` `dump_ui` `tap_screen` `swipe_screen` `find_and_tap` | **核心：控制任意App** |
| ⌨️ 输入 | `input_text` `input_chinese_text` `input_keyevent` `long_press` | 打字、按键、长按 |
| 🏠 导航 | `go_home` `go_back` `open_recent_apps` | Home/返回/最近 |
| 📷 相机/图片 | `take_photo` `get_camera_info` `list_photos` `read_photo` | 拍照、浏览图片 |
| 💬 通信 | `list_sms` `send_sms` `list_contacts` | 短信、通讯录 |
| 📋 剪贴板 | `get_clipboard` `set_clipboard` | 读写剪贴板 |
| 🔔 通知 | `send_notification` `show_toast` | 发送通知/Toast |
| 🔊 系统控制 | `set_volume` `get_volume` `toggle_torch` `vibrate` | 音量、手电筒、震动 |
| 🗣️ TTS | `text_to_speech` | 文字转语音 |
| 🎵 媒体 | `media_player` | 播放/暂停/停止音频 |
| 📁 文件 | `list_directory` `read_file` `write_file` | 文件读写 |
| ⚡ 命令 | `execute_command` | 执行Shell命令 |
| 🔆 屏幕 | `get_screen_brightness` `set_screen_brightness` `get_screen_size` | 屏幕亮度/分辨率 |
| 📡 传感器 | `get_sensor_list` `read_sensor` | 读取传感器数据 |
| 🔗 分享 | `share_file` `download_file` | 分享/下载文件 |
| 🔐 生物识别 | `get_fingerprint` | 指纹认证 |

## UI 自动化：控制任意 App

**核心能力**：通过截图 → 分析 → 点击的循环，可以操控手机上任意应用。

### 工作流程

```
take_screenshot → Claude 看到屏幕内容
      ↓
dump_ui        → 获取所有UI元素及坐标
      ↓
tap_screen     → 点击目标位置
input_text     → 输入文字
      ↓
take_screenshot → 确认操作结果，继续下一步
```

### 示例：用微信给某人发消息

Claude 会自动执行以下步骤：
1. `open_app("com.tencent.mm")` — 打开微信
2. `take_screenshot()` — 查看当前屏幕
3. `dump_ui()` — 获取UI元素坐标
4. `find_and_tap("通讯录")` — 点击通讯录
5. `find_and_tap("搜索")` — 点击搜索框
6. `input_chinese_text("张三")` — 输入联系人名字
7. `find_and_tap("张三")` — 点击搜索结果
8. `find_and_tap("发消息")` — 点击发消息
9. `tap_screen(x, y)` — 点击输入框
10. `input_chinese_text("你好，明天几点见面？")` — 输入消息
11. `find_and_tap("发送")` — 发送

你只需要对 Claude 说："**打开微信给张三发消息说明天几点见面**"，Claude 会自动完成以上全部步骤。

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

**基础操作：**
- "查看手机电量"
- "手机现在连着什么WiFi"
- "拍一张照片"
- "打开手电筒"
- "手机在哪里"（GPS定位）

**App 控制（UI 自动化）：**
- "打开微信给张三发消息说明天见"
- "帮我打开抖音"
- "截个屏让我看看手机画面"
- "点击屏幕上的xxx按钮"
- "在当前输入框输入xxx"

**通信：**
- "给 13800138000 发短信说我到了"
- "查看最近的短信"
- "查看通讯录"

**系统控制：**
- "把手机音量调到5"
- "用手机说一句你好"
- "手机震动一下"

## 测试

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python termux_mcp_server.py
```
