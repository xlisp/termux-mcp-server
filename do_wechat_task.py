"""
Task: Open WeChat, find contact "0oo粉", send "晚安" message.

Prerequisites:
  1. pkg install android-tools
  2. Enable Wireless Debugging in Developer Options
  3. adb pair localhost:<pair_port>   (enter pairing code)
  4. adb connect localhost:<connect_port>
  5. Verify: adb devices  (should show "device")

Run with: python do_wechat_task.py
"""
import subprocess
import time
import re
import os

os.environ.setdefault('TMPDIR', '/data/data/com.termux/files/usr/tmp')
os.makedirs(os.environ['TMPDIR'], exist_ok=True)

if '/system/bin' not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"/system/bin:{os.environ.get('PATH', '')}"

HOME = '/data/data/com.termux/files/home'
USE_ADB = True  # Android 12+ needs adb shell


def run(cmd, shell=True, timeout=15):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=True, text=True,
                           timeout=timeout, encoding='utf-8', errors='replace')
        out = r.stdout.strip()
        err = r.stderr.strip()
        if out:
            print(f"  [stdout] {out[:300]}")
        if err:
            print(f"  [stderr] {err[:300]}")
        return r.returncode == 0, out, err
    except subprocess.TimeoutExpired:
        print(f"  [timeout] after {timeout}s")
        return False, '', 'timeout'
    except Exception as e:
        print(f"  [error] {e}")
        return False, '', str(e)


def adb(cmd, timeout=15):
    """Run command via adb shell."""
    print(f"  $ adb shell {cmd}")
    return run(f'adb shell {cmd}', timeout=timeout)


def check_adb():
    """Check if adb is connected."""
    ok, out, _ = run('adb devices', timeout=5)
    if ok:
        for line in out.split('\n')[1:]:
            if '\tdevice' in line:
                print(f"  ✓ ADB connected: {line.strip()}")
                return True
    print("  ✗ ADB not connected!")
    print("  Please run:")
    print("    1. Settings → Developer Options → Wireless Debugging → ON")
    print("    2. Tap 'Pair device with pairing code'")
    print("    3. adb pair localhost:<port>  (enter the code)")
    print("    4. adb connect localhost:<port>")
    return False


def screenshot(name="screenshot"):
    tmp = '/sdcard/mcp_screenshot.png'
    path = f"{HOME}/{name}.png"
    print(f"\n📸 Screenshot → {name}.png")
    if USE_ADB:
        adb(f'screencap -p {tmp}')
        # Copy from sdcard to home
        run(f'cp /storage/emulated/0/mcp_screenshot.png {path}')
    else:
        run(f'screencap -p {path}')
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"  ✓ Saved ({os.path.getsize(path):,} bytes)")
    else:
        print(f"  ✗ Failed")
    return path


def dump_ui():
    tmp = '/sdcard/mcp_ui_dump.xml'
    path = f"{HOME}/ui_dump.xml"
    print(f"\n🔍 Dumping UI...")
    if USE_ADB:
        adb(f'uiautomator dump {tmp}')
        run(f'cp /storage/emulated/0/mcp_ui_dump.xml {path}')
    else:
        run(f'uiautomator dump {path}')

    if not os.path.exists(path):
        print("  ✗ UI dump failed")
        return ""

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    nodes = re.findall(
        r'text="([^"]*)".*?content-desc="([^"]*)".*?clickable="([^"]*)".*?'
        r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        content
    )
    print(f"  Found {len(nodes)} UI elements:")
    for text, desc, clickable, x1, y1, x2, y2 in nodes:
        if text or desc:
            cx = (int(x1) + int(x2)) // 2
            cy = (int(y1) + int(y2)) // 2
            label = text or desc
            click = " *click*" if clickable == "true" else ""
            print(f"    [{label}] → ({cx},{cy}){click}")
    return content


def find_and_tap(ui_content, search_text):
    nodes = re.findall(
        r'text="([^"]*)".*?content-desc="([^"]*)".*?'
        r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        ui_content
    )
    search_lower = search_text.lower()
    for text, desc, x1, y1, x2, y2 in nodes:
        if search_lower in text.lower() or search_lower in desc.lower():
            cx = (int(x1) + int(x2)) // 2
            cy = (int(y1) + int(y2)) // 2
            label = text or desc
            print(f"\n👆 Found \"{label}\" → tapping ({cx},{cy})")
            if USE_ADB:
                adb(f'input tap {cx} {cy}')
            else:
                run(f'input tap {cx} {cy}')
            return True, cx, cy
    print(f"\n❌ Not found: \"{search_text}\"")
    return False, 0, 0


def tap(x, y):
    print(f"\n👆 Tapping ({x},{y})")
    if USE_ADB:
        adb(f'input tap {x} {y}')
    else:
        run(f'input tap {x} {y}')


def input_chinese(text):
    """Input Chinese text via ADB broadcast (most reliable method)."""
    print(f"\n⌨️ Inputting: {text}")
    if USE_ADB:
        # Method: Use ADB to set clipboard then paste
        # First, use am broadcast to set clipboard
        escaped = text.replace("'", "'\\''")
        adb(f"am broadcast -a clipper.set -e text '{escaped}'", timeout=5)
        time.sleep(0.3)
        # Try direct input text (works for ASCII)
        # For Chinese, use the clipboard approach
        run(f'termux-clipboard-set "{text}"', timeout=5)
        time.sleep(0.3)
        adb('input keyevent 279')  # PASTE
    else:
        run(f'termux-clipboard-set "{text}"', timeout=5)
        time.sleep(0.3)
        run('input keyevent 279')


def press_back():
    print("\n🔙 Back")
    if USE_ADB:
        adb('input keyevent 4')
    else:
        run('input keyevent 4')


# ============================================================
print("=" * 60)
print("Task: Open WeChat, send '晚安' to '0oo粉'")
print("=" * 60)

# Pre-check: ADB
print("\n🔧 Checking ADB connection...")
if not check_adb():
    exit(1)

# Step 1: Open WeChat
print("\n📱 Step 1: Opening WeChat...")
adb('am start -n com.tencent.mm/.ui.LauncherUI')
time.sleep(4)

# Step 2: See screen
screenshot("step2_home")
ui = dump_ui()

# Step 3: Look for search
print("\n📱 Step 3: Looking for search...")
found, _, _ = find_and_tap(ui, "搜索")
if not found:
    # WeChat has a search icon at the top, try content-desc
    found, _, _ = find_and_tap(ui, "Search")
    if not found:
        # Some WeChat versions: tap the top area to reveal search
        print("  Trying top area for search bar...")
        # Get screen size
        ok, out, _ = adb('wm size') if USE_ADB else run('wm size')
        w, h = 1080, 2400  # defaults
        if ok or out:
            m = re.search(r'(\d+)x(\d+)', out)
            if m:
                w, h = int(m.group(1)), int(m.group(2))
        # Tap magnifying glass (usually top-right area)
        tap(w - 100, 160)

time.sleep(2)
screenshot("step3_search")
ui = dump_ui()

# Step 4: Input contact name
print("\n📱 Step 4: Searching for '0oo粉'...")
input_chinese("0oo粉")
time.sleep(2)

screenshot("step4_results")
ui = dump_ui()

# Step 5: Tap on contact
print("\n📱 Step 5: Tapping on contact...")
found, _, _ = find_and_tap(ui, "0oo粉")
if not found:
    found, _, _ = find_and_tap(ui, "0oo")
    if not found:
        found, _, _ = find_and_tap(ui, "粉")
time.sleep(2)

screenshot("step5_chat")
ui = dump_ui()

# Step 6: Find input field and type message
print("\n📱 Step 6: Typing message...")
found, _, _ = find_and_tap(ui, "输入")
if not found:
    found, _, _ = find_and_tap(ui, "消息")
    if not found:
        # Input field is usually at bottom center
        ok, out, _ = adb('wm size') if USE_ADB else run('wm size')
        w, h = 1080, 2400
        m = re.search(r'(\d+)x(\d+)', out if out else '')
        if m:
            w, h = int(m.group(1)), int(m.group(2))
        tap(w // 2, h - 150)
time.sleep(1)

input_chinese("晚安")
time.sleep(1)

screenshot("step6_typed")
ui = dump_ui()

# Step 7: Send
print("\n📱 Step 7: Sending...")
found, _, _ = find_and_tap(ui, "发送")
if not found:
    found, _, _ = find_and_tap(ui, "Send")
time.sleep(1)

screenshot("step7_done")
print("\n" + "=" * 60)
print("✅ Done! Check ~/step*.png for screenshots")
print("=" * 60)
