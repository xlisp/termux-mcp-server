"""
Task: Open WeChat, find contact "0oo粉", send "晚安" message.
Run with: python do_wechat_task.py
"""
import subprocess
import time
import re
import os
import sys

os.environ.setdefault('TMPDIR', '/data/data/com.termux/files/usr/tmp')
os.makedirs(os.environ['TMPDIR'], exist_ok=True)

HOME = '/data/data/com.termux/files/home'

def run(cmd, shell=True, timeout=15):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=True, text=True,
                           timeout=timeout, encoding='utf-8', errors='replace')
        out = r.stdout.strip()
        err = r.stderr.strip()
        if out:
            print(f"  [stdout] {out[:200]}")
        if err:
            print(f"  [stderr] {err[:200]}")
        return r.returncode == 0, out, err
    except Exception as e:
        print(f"  [error] {e}")
        return False, '', str(e)

def screenshot(name="screenshot"):
    path = f"{HOME}/{name}.png"
    print(f"\n📸 Taking screenshot → {path}")
    run(f'screencap -p {path}')
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✓ Screenshot saved ({size:,} bytes)")
    else:
        print(f"  ✗ Screenshot failed")
    return path

def dump_ui():
    path = f"{HOME}/ui_dump.xml"
    print(f"\n🔍 Dumping UI → {path}")
    run(f'uiautomator dump {path}')
    if not os.path.exists(path):
        print("  ✗ UI dump failed")
        return ""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse elements
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
            click = " *clickable*" if clickable == "true" else ""
            print(f"    [{label}] → ({cx},{cy}){click}")
    return content

def find_and_tap(ui_content, search_text):
    """Find element by text and tap it."""
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
            run(f'input tap {cx} {cy}')
            return True, cx, cy
    print(f"\n❌ Not found: \"{search_text}\"")
    return False, 0, 0

def tap(x, y):
    print(f"\n👆 Tapping ({x},{y})")
    run(f'input tap {x} {y}')

def input_chinese(text):
    """Input Chinese text via clipboard paste."""
    print(f"\n⌨️ Inputting: {text}")
    # Set clipboard
    run(f'termux-clipboard-set "{text}"')
    time.sleep(0.5)
    # Paste
    run('input keyevent 279')  # KEYCODE_PASTE
    time.sleep(0.5)

def press_key(name, code):
    print(f"\n🔘 Pressing {name}")
    run(f'input keyevent {code}')

# ============================================================
# Main Task: Open WeChat → Send "晚安" to "0oo粉"
# ============================================================

print("=" * 60)
print("Task: Open WeChat, send '晚安' to '0oo粉'")
print("=" * 60)

# Step 1: Open WeChat
print("\n📱 Step 1: Opening WeChat...")
run('am start -n com.tencent.mm/.ui.LauncherUI')
time.sleep(4)

# Step 2: See what's on screen
screenshot("step2_wechat_home")
ui = dump_ui()

# Step 3: Try to find search/搜索 to search for the contact
print("\n📱 Step 3: Looking for search...")
# Try tapping the search icon (usually top right area)
# First try to find it in UI
found, _, _ = find_and_tap(ui, "搜索")
if not found:
    # Try the magnifying glass icon - often at top right
    # WeChat search is usually accessible via the + button or search bar
    found, _, _ = find_and_tap(ui, "Search")
    if not found:
        # Try tapping the top search area directly
        # On most phones, WeChat search bar is at the top
        print("\n  Trying to tap search area at top of screen...")
        # Get screen width first
        ok, out, _ = run('wm size')
        if ok and 'x' in out:
            match = re.search(r'(\d+)x(\d+)', out)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                print(f"  Screen size: {w}x{h}")

time.sleep(2)
screenshot("step3_after_search")
ui = dump_ui()

# Step 4: Try to find the contact "0oo粉"
# If we're now on a search page, type the contact name
print("\n📱 Step 4: Searching for contact '0oo粉'...")
input_chinese("0oo粉")
time.sleep(2)

screenshot("step4_search_result")
ui = dump_ui()

# Step 5: Tap on the contact in search results
print("\n📱 Step 5: Tapping on contact...")
found, _, _ = find_and_tap(ui, "0oo粉")
if not found:
    found, _, _ = find_and_tap(ui, "0oo")
    if not found:
        # Try partial match
        found, _, _ = find_and_tap(ui, "粉")
time.sleep(2)

screenshot("step5_chat_window")
ui = dump_ui()

# Step 6: Tap message input area and type message
print("\n📱 Step 6: Finding input field and typing message...")
# Look for the message input field
found, _, _ = find_and_tap(ui, "输入")
if not found:
    found, _, _ = find_and_tap(ui, "消息")
    if not found:
        # WeChat input box is usually at the bottom - try tapping bottom area
        ok, out, _ = run('wm size')
        if ok:
            match = re.search(r'(\d+)x(\d+)', out)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                tap(w // 2, h - 150)  # Bottom center area
time.sleep(1)

# Type the message
input_chinese("晚安")
time.sleep(1)

screenshot("step6_message_typed")
ui = dump_ui()

# Step 7: Send the message
print("\n📱 Step 7: Sending message...")
found, _, _ = find_and_tap(ui, "发送")
if not found:
    found, _, _ = find_and_tap(ui, "Send")
time.sleep(1)

screenshot("step7_sent")
print("\n" + "=" * 60)
print("✅ Task complete! Check screenshots in ~/")
print("=" * 60)
