#!/data/data/com.termux/files/usr/bin/bash
export PATH="/system/bin:$PATH"

echo "=== 1. 当前用户和ID ==="
id
whoami

echo ""
echo "=== 2. Termux:API 是否安装 ==="
pm list packages | grep termux.api && echo "✓ Termux:API app installed" || echo "✗ Termux:API app NOT installed"
dpkg -l 2>/dev/null | grep termux-api && echo "✓ termux-api package installed" || echo "✗ termux-api package NOT installed"

echo ""
echo "=== 3. 测试 termux-api 命令 ==="
echo "Testing termux-battery-status (5s timeout)..."
timeout 5 termux-battery-status 2>&1 && echo "✓ works" || echo "✗ failed/timeout"

echo ""
echo "=== 4. 测试 am 命令 ==="
am version 2>&1 || echo "am failed"

echo ""
echo "=== 5. 测试 screencap ==="
screencap -p /data/data/com.termux/files/home/test_screen.png 2>&1
ls -la /data/data/com.termux/files/home/test_screen.png 2>&1

echo ""
echo "=== 6. 测试 input ==="
input keyevent 0 2>&1 && echo "✓ input works" || echo "✗ input failed"

echo ""
echo "=== 7. 检查 /data/local/tmp 权限 ==="
ls -la /data/local/ 2>&1
mkdir -p /data/local/tmp 2>&1 && echo "✓ can create /data/local/tmp" || echo "✗ cannot create /data/local/tmp"

echo ""
echo "=== 8. SELinux 状态 ==="
getenforce 2>&1

echo ""
echo "=== 9. 是否 root ==="
su -c "id" 2>&1 && echo "✓ root available" || echo "✗ no root"

echo ""
echo "=== 10. Android 版本 ==="
getprop ro.build.version.release 2>&1
getprop ro.build.version.sdk 2>&1
