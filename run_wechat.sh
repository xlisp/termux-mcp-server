#!/data/data/com.termux/files/usr/bin/bash
# Step 1: Launch WeChat
echo "=== Opening WeChat ==="
am start -n com.tencent.mm/.ui.LauncherUI 2>&1
sleep 3

# Step 2: Screenshot
echo "=== Taking screenshot ==="
screencap -p /data/data/com.termux/files/home/screenshot_1.png 2>&1
echo "Screenshot saved to ~/screenshot_1.png"

# Step 3: Dump UI
echo "=== Dumping UI ==="
uiautomator dump /data/data/com.termux/files/home/ui_dump.xml 2>&1
echo "UI dump saved"
