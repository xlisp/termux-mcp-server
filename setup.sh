#!/data/data/com.termux/files/usr/bin/bash
#
# Termux MCP Server 一键设置脚本
#
echo "============================================"
echo "  Termux MCP Server Setup"
echo "============================================"

# 1. Install packages
echo ""
echo ">>> 1. 安装必要的包..."
pkg install -y python android-tools termux-api 2>/dev/null

# 2. Python deps
echo ""
echo ">>> 2. 安装 Python MCP 库..."
pip install "mcp[cli]" 2>/dev/null

# 3. Storage permission
echo ""
echo ">>> 3. 请求存储权限..."
termux-setup-storage

# 4. ADB setup guide
echo ""
echo "============================================"
echo "  关键步骤：设置 ADB 无线调试"
echo "============================================"
echo ""
echo "Android 12+ 需要通过 ADB 才能控制屏幕。"
echo "请按以下步骤操作："
echo ""
echo "  1. 打开手机 [设置] → [开发者选项]"
echo "     (没有开发者选项？去 [关于手机] 连点7次版本号)"
echo ""
echo "  2. 打开 [无线调试] (Wireless Debugging)"
echo ""
echo "  3. 点击 [使用配对码配对设备]"
echo "     记下 配对码(code) 和 端口(port)"
echo ""
echo "  4. 回到这个终端，运行："
echo "     adb pair localhost:<配对端口>"
echo "     然后输入配对码"
echo ""
echo "  5. 配对成功后，回到 [无线调试] 页面"
echo "     记下 IP地址和端口 (例如 localhost:xxxxx)"
echo ""
echo "  6. 运行："
echo "     adb connect localhost:<连接端口>"
echo ""
echo "  7. 验证："
echo "     adb devices"
echo "     应该显示 'localhost:xxxxx  device'"
echo ""
echo "============================================"
echo ""
echo "ADB 连接成功后，运行测试："
echo "  python do_wechat_task.py"
echo ""
echo "或启动 MCP Server："
echo "  python termux_mcp_server.py"
echo ""

# 5. Remind about Termux:API app
echo "============================================"
echo "  还需要安装 Termux:API App (可选)"
echo "============================================"
echo ""
echo "从 F-Droid 下载安装 Termux:API app："
echo "  https://f-droid.org/packages/com.termux.api/"
echo ""
echo "这样 termux-battery-status、termux-clipboard-set"
echo "等命令才能正常使用。"
echo ""
echo "注意：必须从 F-Droid 安装，不要用 Play Store 版本！"
echo "      Termux 和 Termux:API 必须来自同一来源。"
echo ""
