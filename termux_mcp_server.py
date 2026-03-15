"""
Termux MCP Server - Control Android phone from Claude Desktop.

Provides tools for:
- Device info (battery, WiFi, telephony)
- Location tracking
- App management (list running apps, launch apps)
- UI automation (tap, swipe, type text, screenshot, UI dump)
- Media (camera, photos, media player)
- Communication (SMS, contacts, clipboard, notifications)
- System control (volume, torch, vibrate, TTS)
- File browsing and command execution
"""

import os
import subprocess
import json
import base64
import asyncio
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("termux-control")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BLOCKED_COMMANDS = {
    'rm', 'rmdir', 'mkfs', 'dd', 'format',
    'shutdown', 'reboot', 'halt', 'poweroff',
}

HOME = '/data/data/com.termux/files/home'

# Android system commands that must go through adb shell on Android 12+
_ADB_REQUIRED_CMDS = {
    'screencap', 'uiautomator', 'input', 'am', 'pm', 'wm',
    'settings', 'getprop', 'dumpsys', 'monkey', 'cmd', 'content',
}

def _ensure_path_env() -> dict:
    """Return env dict with /system/bin in PATH."""
    env = os.environ.copy()
    path = env.get('PATH', '')
    if '/system/bin' not in path:
        env['PATH'] = f"/system/bin:{path}"
    return env


def _adb_connected() -> bool:
    """Check if adb is connected to the device."""
    try:
        r = subprocess.run(
            ['adb', 'devices'], capture_output=True, text=True, timeout=5,
            env=_ensure_path_env(),
        )
        # Look for a device line like "localhost:5555	device"
        for line in r.stdout.strip().split('\n')[1:]:
            if '\tdevice' in line:
                return True
    except Exception:
        pass
    return False


def _adb_shell(cmd: str, timeout: int = 30) -> dict:
    """Run a command via 'adb shell'. Used on Android 12+ where direct calls fail."""
    try:
        result = subprocess.run(
            ['adb', 'shell', cmd],
            capture_output=True, text=True,
            timeout=timeout, encoding='utf-8', errors='replace',
            env=_ensure_path_env(),
        )
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': f'Timed out after {timeout}s'}
    except FileNotFoundError:
        return {'success': False, 'error': 'adb not found. Run: pkg install android-tools'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _run(cmd: list[str] | str, timeout: int = 30, shell: bool = False) -> dict:
    """Run a command. Auto-routes through adb shell if needed on Android 12+."""
    env = _ensure_path_env()

    # Detect if this is an Android system command that needs adb shell
    if shell and isinstance(cmd, str):
        first_word = cmd.strip().split()[0] if cmd.strip() else ''
    elif isinstance(cmd, list) and cmd:
        first_word = os.path.basename(cmd[0])
    else:
        first_word = ''

    if first_word in _ADB_REQUIRED_CMDS and _adb_connected():
        # Route through adb shell
        if shell and isinstance(cmd, str):
            return _adb_shell(cmd, timeout=timeout)
        elif isinstance(cmd, list):
            return _adb_shell(' '.join(cmd), timeout=timeout)

    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            timeout=timeout, encoding='utf-8', errors='replace',
            env=env,
        )
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': f'Timed out after {timeout}s'}
    except FileNotFoundError:
        cmd_name = cmd if isinstance(cmd, str) else cmd[0]
        return {'success': False, 'error': f'Command not found: {cmd_name}. Make sure termux-api package is installed (pkg install termux-api).'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _termux(cmd: str, args: list[str] | None = None, timeout: int = 30) -> str:
    """Run a termux-api command and return output or error message."""
    full_cmd = [cmd] + (args or [])
    r = _run(full_cmd, timeout=timeout)
    if not r.get('success'):
        return f"Error: {r.get('error', r.get('stderr', 'Unknown error'))}"
    return r.get('stdout', '')


def _format_json(raw: str) -> str:
    """Pretty-format JSON output, or return raw if not JSON."""
    try:
        data = json.loads(raw)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return raw

# ---------------------------------------------------------------------------
# Device Information
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_battery_status() -> str:
    """Get phone battery status including level, charging state, temperature, etc."""
    return _format_json(_termux('termux-battery-status'))


@mcp.tool()
async def get_wifi_info() -> str:
    """Get current WiFi connection information (SSID, IP, signal strength, etc.)."""
    return _format_json(_termux('termux-wifi-connectioninfo'))


@mcp.tool()
async def scan_wifi() -> str:
    """Scan for nearby WiFi networks."""
    return _format_json(_termux('termux-wifi-scaninfo', timeout=15))


@mcp.tool()
async def get_telephony_info() -> str:
    """Get telephony device info (carrier, phone type, SIM state, etc.)."""
    return _format_json(_termux('termux-telephony-deviceinfo'))


@mcp.tool()
async def get_telephony_cell_info() -> str:
    """Get detailed cellular network information."""
    return _format_json(_termux('termux-telephony-cellinfo'))

# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_location(provider: str = "gps", request: str = "once") -> str:
    """Get the phone's current GPS location.

    Args:
        provider: Location provider - 'gps', 'network', or 'passive' (default: gps)
        request: 'once' for single reading, 'last' for last known location, 'updates' for continuous
    """
    return _format_json(_termux('termux-location', ['-p', provider, '-r', request], timeout=60))

# ---------------------------------------------------------------------------
# ADB Setup (required on Android 12+ for system commands)
# ---------------------------------------------------------------------------

@mcp.tool()
async def adb_setup_status() -> str:
    """Check if ADB is set up and connected. On Android 12+, ADB is required
    for screencap, input, uiautomator, am, etc. to work from Termux.

    If not connected, follow the instructions in the output to set up.
    """
    # Check if adb is installed
    r = _run(['which', 'adb'], timeout=5)
    if not r['success']:
        return ("ADB not installed.\n"
                "Run: pkg install android-tools\n"
                "Then use adb_connect tool to connect.")

    connected = _adb_connected()
    if connected:
        devices = _run(['adb', 'devices'], timeout=5)
        return f"ADB is connected!\n{devices.get('stdout', '')}"

    return ("ADB is installed but not connected.\n\n"
            "To connect (do this on the phone):\n"
            "1. Go to Settings → Developer Options → Wireless Debugging → ON\n"
            "2. Tap 'Pair device with pairing code'\n"
            "3. Note the pairing code and port\n"
            "4. Use the adb_connect tool with the pairing info")


@mcp.tool()
async def adb_connect(pair_code: str = "", pair_port: str = "", connect_port: str = "") -> str:
    """Connect ADB to this device wirelessly. Required on Android 12+.

    Step 1: If pair_code and pair_port are given, pair first.
    Step 2: If connect_port is given (or after pairing), connect.

    Find these in: Settings → Developer Options → Wireless Debugging

    Args:
        pair_code: Pairing code from wireless debugging (for first-time pairing)
        pair_port: Pairing port from wireless debugging (e.g. '37123')
        connect_port: Connection port shown on wireless debugging main page (e.g. '5555' or '45678')
    """
    results = []

    # Step 1: Pair if needed
    if pair_code and pair_port:
        # adb pair needs the code via stdin
        try:
            proc = subprocess.Popen(
                ['adb', 'pair', f'localhost:{pair_port}'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=_ensure_path_env(),
            )
            stdout, stderr = proc.communicate(input=f'{pair_code}\n', timeout=15)
            results.append(f"Pair: {stdout.strip()} {stderr.strip()}")
        except Exception as e:
            results.append(f"Pair error: {e}")

    # Step 2: Connect
    if connect_port:
        r = _run(f'adb connect localhost:{connect_port}', shell=True, timeout=10)
        results.append(f"Connect: {r.get('stdout', '')} {r.get('stderr', '')}")
    elif not pair_code:
        # Try common port
        r = _run('adb connect localhost:5555', shell=True, timeout=10)
        results.append(f"Connect: {r.get('stdout', '')} {r.get('stderr', '')}")

    # Verify
    connected = _adb_connected()
    results.append(f"\nADB connected: {'Yes ✓' if connected else 'No ✗'}")

    if not connected:
        results.append("\nTip: Make sure 'Wireless debugging' is ON in Developer Options.")
        results.append("Then provide the correct connect_port from the wireless debugging page.")

    return "\n".join(results)


# ---------------------------------------------------------------------------
# App Management
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_running_apps() -> str:
    """List currently running processes/apps on the phone with CPU and memory usage."""
    r = _run(['ps', '-eo', 'pid,user,%cpu,%mem,args', '--sort=-%cpu'], timeout=10)
    if not r['success']:
        # fallback
        r = _run('ps aux', shell=True, timeout=10)
    return r.get('stdout', r.get('error', 'Failed to list processes'))


@mcp.tool()
async def list_installed_packages() -> str:
    """List all installed Termux packages."""
    return _termux('dpkg', ['--list'])


@mcp.tool()
async def open_url(url: str) -> str:
    """Open a URL in the default browser on the phone.

    Args:
        url: The URL to open
    """
    return _termux('termux-open-url', [url])


@mcp.tool()
async def open_app(package_or_action: str) -> str:
    """Launch an Android app or activity using am (Activity Manager).

    Args:
        package_or_action: Package name (e.g. 'com.whatsapp') or intent action.
            Common examples:
            - com.whatsapp
            - com.tencent.mm (WeChat)
            - com.android.chrome
            - com.android.settings
            - com.android.camera2
    """
    # Try monkey approach first (simplest way to launch an app)
    r = _run(['am', 'start', '-n',
              f'{package_or_action}/.MainActivity'], timeout=10)
    if not r['success']:
        # fallback: use monkey to launch
        r = _run(['monkey', '-p', package_or_action, '-c',
                   'android.intent.category.LAUNCHER', '1'], timeout=10)
    if not r['success']:
        # final fallback: am start with package
        r = _run(f'am start $(pm resolve-activity --brief {package_or_action} | tail -1)', shell=True, timeout=10)
    return r.get('stdout', '') + ('\n' + r.get('stderr', '') if r.get('stderr') else '')


@mcp.tool()
async def list_android_packages(filter_keyword: str = "") -> str:
    """List installed Android apps/packages.

    Args:
        filter_keyword: Optional keyword to filter package names (e.g. 'camera', 'wechat')
    """
    if filter_keyword:
        r = _run(f'pm list packages | grep -i {filter_keyword}', shell=True, timeout=15)
    else:
        r = _run(['pm', 'list', 'packages'], timeout=15)
    return r.get('stdout', r.get('error', 'Failed to list packages'))

# ---------------------------------------------------------------------------
# UI Automation (tap, swipe, type, screenshot, UI hierarchy)
# ---------------------------------------------------------------------------

@mcp.tool()
async def take_screenshot(output_path: str = "/data/data/com.termux/files/home/screenshot.png") -> str:
    """Take a screenshot of the current phone screen. Returns the screenshot as base64 image data.

    Args:
        output_path: Where to save the screenshot file
    """
    # adb shell screencap can't write to Termux's private dir, use /sdcard/ as intermediary
    tmp_path = '/sdcard/mcp_screenshot.png'
    if _adb_connected():
        r = _adb_shell(f'screencap -p {tmp_path}', timeout=10)
        if r['success']:
            # Copy from /sdcard/ to our output path
            import shutil
            sdcard_real = '/storage/emulated/0/mcp_screenshot.png'
            try:
                shutil.copy2(sdcard_real, output_path)
            except Exception:
                # Try adb pull as fallback
                _run(f'adb pull {tmp_path} {output_path}', shell=True, timeout=10)
    else:
        r = _run(f'screencap -p {output_path}', shell=True, timeout=10)

    if not r.get('success'):
        return f"Error taking screenshot: {r.get('error', r.get('stderr', 'Unknown'))}"

    path = Path(output_path)
    if not path.exists() or path.stat().st_size == 0:
        return "Error: Screenshot file was not created or is empty"

    # Return base64 so Claude can see the screen
    try:
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        return f"Screenshot saved to {output_path} ({path.stat().st_size:,} bytes)\n\ndata:image/png;base64,{data}"
    except Exception as e:
        return f"Screenshot saved to {output_path} but failed to encode: {e}"


@mcp.tool()
async def get_screen_size() -> str:
    """Get the phone screen resolution (width x height in pixels)."""
    r = _run('wm size', shell=True, timeout=5)
    return r.get('stdout', r.get('error', 'Failed'))


@mcp.tool()
async def tap_screen(x: int, y: int) -> str:
    """Tap the screen at specific coordinates.

    Use take_screenshot + dump_ui first to find the right coordinates.

    Args:
        x: X coordinate (pixels from left)
        y: Y coordinate (pixels from top)
    """
    r = _run(f'input tap {x} {y}', shell=True, timeout=5)
    if r['success']:
        return f"Tapped at ({x}, {y})"
    return f"Error: {r.get('error', r.get('stderr', 'Failed'))}"


@mcp.tool()
async def long_press(x: int, y: int, duration_ms: int = 1000) -> str:
    """Long press at specific screen coordinates.

    Args:
        x: X coordinate
        y: Y coordinate
        duration_ms: Press duration in milliseconds (default: 1000)
    """
    r = _run(f'input swipe {x} {y} {x} {y} {duration_ms}', shell=True, timeout=10)
    if r['success']:
        return f"Long pressed at ({x}, {y}) for {duration_ms}ms"
    return f"Error: {r.get('error', r.get('stderr', 'Failed'))}"


@mcp.tool()
async def swipe_screen(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Swipe on the screen from one point to another.

    Args:
        x1: Start X coordinate
        y1: Start Y coordinate
        x2: End X coordinate
        y2: End Y coordinate
        duration_ms: Swipe duration in milliseconds (default: 300)
    """
    r = _run(f'input swipe {x1} {y1} {x2} {y2} {duration_ms}', shell=True, timeout=10)
    if r['success']:
        return f"Swiped from ({x1},{y1}) to ({x2},{y2}) in {duration_ms}ms"
    return f"Error: {r.get('error', r.get('stderr', 'Failed'))}"


@mcp.tool()
async def input_text(text: str) -> str:
    """Type text into the currently focused input field.

    Note: This works best with ASCII text. For Chinese/Unicode text,
    use set_clipboard + input_keyevent(keycode='279') (paste) instead.

    Args:
        text: Text to type (spaces are supported)
    """
    # Replace spaces with %s for 'input text'
    escaped = text.replace(' ', '%s')
    r = _run(f'input text "{escaped}"', shell=True, timeout=10)
    if r['success']:
        return f"Typed: {text}"
    return f"Error: {r.get('error', r.get('stderr', 'Failed'))}"


@mcp.tool()
async def input_chinese_text(text: str) -> str:
    """Input Chinese/Unicode text by copying to clipboard and pasting.

    This is the reliable way to input non-ASCII text (Chinese, Japanese, emoji, etc.).

    Args:
        text: The text to input (any language)
    """
    # Step 1: Set clipboard
    clip_result = _termux('termux-clipboard-set', [text])
    if clip_result and 'Error' in clip_result:
        return f"Failed to set clipboard: {clip_result}"
    # Step 2: Paste (Ctrl+V = KEYCODE_PASTE = 279)
    r = _run('input keyevent 279', shell=True, timeout=5)
    if r['success']:
        return f"Pasted text: {text}"
    # Fallback: try Ctrl+V combo
    r = _run('input keyevent --longpress 113 50', shell=True, timeout=5)
    return f"Attempted paste of: {text}"


@mcp.tool()
async def input_keyevent(keycode: str) -> str:
    """Send a key event to the phone.

    Args:
        keycode: Android keycode name or number. Common ones:
            - '3' or 'KEYCODE_HOME' = Home button
            - '4' or 'KEYCODE_BACK' = Back button
            - '26' or 'KEYCODE_POWER' = Power button
            - '24' = Volume Up, '25' = Volume Down
            - '66' or 'KEYCODE_ENTER' = Enter/Confirm
            - '67' or 'KEYCODE_DEL' = Backspace/Delete
            - '61' or 'KEYCODE_TAB' = Tab
            - '82' or 'KEYCODE_MENU' = Menu
            - '187' or 'KEYCODE_APP_SWITCH' = Recent apps
            - '279' or 'KEYCODE_PASTE' = Paste
            - '84' or 'KEYCODE_SEARCH' = Search
    """
    r = _run(f'input keyevent {keycode}', shell=True, timeout=5)
    if r['success']:
        return f"Sent keyevent: {keycode}"
    return f"Error: {r.get('error', r.get('stderr', 'Failed'))}"


@mcp.tool()
async def dump_ui(output_path: str = "/data/data/com.termux/files/home/ui_dump.xml") -> str:
    """Dump the current UI hierarchy (XML). Shows all visible UI elements with their
    text, content-desc, bounds (coordinates), class name, and clickable state.

    Use this to find the right element/coordinates before tapping.

    Args:
        output_path: Where to save the XML dump
    """
    # uiautomator needs to dump to a path it can write to
    tmp_dump = '/sdcard/mcp_ui_dump.xml'
    sdcard_real = '/storage/emulated/0/mcp_ui_dump.xml'

    if _adb_connected():
        r = _adb_shell(f'uiautomator dump {tmp_dump}', timeout=15)
        if r['success']:
            import shutil
            try:
                shutil.copy2(sdcard_real, output_path)
            except Exception:
                _run(f'adb pull {tmp_dump} {output_path}', shell=True, timeout=10)
    else:
        r = _run(f'uiautomator dump {output_path}', shell=True, timeout=15)

    if not r.get('success'):
        return f"Error dumping UI: {r.get('error', r.get('stderr', 'Unknown'))}"

    path = Path(output_path)
    if not path.exists():
        return "Error: UI dump file was not created"

    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        return f"Error reading dump: {e}"

    # Parse into readable summary
    import re
    nodes = re.findall(
        r'<node[^>]*?'
        r'text="([^"]*)"[^>]*?'
        r'resource-id="([^"]*)"[^>]*?'
        r'class="([^"]*)"[^>]*?'
        r'content-desc="([^"]*)"[^>]*?'
        r'clickable="([^"]*)"[^>]*?'
        r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        content
    )

    if not nodes:
        # Try alternate attribute order
        nodes = re.findall(
            r'text="([^"]*)".*?resource-id="([^"]*)".*?class="([^"]*)".*?'
            r'content-desc="([^"]*)".*?clickable="([^"]*)".*?'
            r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            content
        )

    lines = [f"UI Elements on screen ({len(nodes)} found):\n"]
    for text, res_id, cls, desc, clickable, x1, y1, x2, y2 in nodes:
        # Calculate center point for tapping
        cx = (int(x1) + int(x2)) // 2
        cy = (int(y1) + int(y2)) // 2
        short_cls = cls.split('.')[-1] if '.' in cls else cls

        label_parts = []
        if text:
            label_parts.append(f'"{text}"')
        if desc:
            label_parts.append(f'[{desc}]')
        if res_id:
            short_id = res_id.split('/')[-1] if '/' in res_id else res_id
            label_parts.append(f'({short_id})')

        label = ' '.join(label_parts) or '(no label)'
        click_mark = ' *clickable*' if clickable == 'true' else ''

        lines.append(f"  {short_cls}: {label} → tap({cx}, {cy}){click_mark}")

    lines.append(f"\nFull XML saved to: {output_path}")
    return "\n".join(lines)


@mcp.tool()
async def find_and_tap(text: str) -> str:
    """Find a UI element by its text and tap on it.

    This combines dump_ui + tap_screen: dumps the UI hierarchy, finds an element
    matching the given text, and taps its center.

    Args:
        text: Text to search for in UI elements (partial match, case-insensitive)
    """
    import re

    dump_path = f"{HOME}/ui_dump_tap.xml"
    tmp_dump = '/sdcard/mcp_ui_dump_tap.xml'
    sdcard_real = '/storage/emulated/0/mcp_ui_dump_tap.xml'

    if _adb_connected():
        r = _adb_shell(f'uiautomator dump {tmp_dump}', timeout=15)
        if r.get('success'):
            import shutil
            try:
                shutil.copy2(sdcard_real, dump_path)
            except Exception:
                _run(f'adb pull {tmp_dump} {dump_path}', shell=True, timeout=10)
    else:
        r = _run(f'uiautomator dump {dump_path}', shell=True, timeout=15)

    if not r.get('success'):
        return f"Error dumping UI: {r.get('error', r.get('stderr', 'Unknown'))}"

    path = Path(dump_path)
    if not path.exists():
        return "Error: UI dump file was not created"

    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        return f"Error reading dump: {e}"

    # Find all nodes with bounds
    pattern = r'text="([^"]*)".*?content-desc="([^"]*)".*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
    matches = re.findall(pattern, content)

    text_lower = text.lower()
    for node_text, desc, x1, y1, x2, y2 in matches:
        if text_lower in node_text.lower() or text_lower in desc.lower():
            cx = (int(x1) + int(x2)) // 2
            cy = (int(y1) + int(y2)) // 2
            r = _run(f'input tap {cx} {cy}', shell=True, timeout=5)
            found_label = node_text or desc
            return f"Found \"{found_label}\" → tapped at ({cx}, {cy})"

    return f"No UI element found matching \"{text}\". Try take_screenshot + dump_ui to see what's on screen."


@mcp.tool()
async def go_home() -> str:
    """Press the Home button to go to the home screen."""
    r = _run('input keyevent 3', shell=True, timeout=5)
    return "Home button pressed" if r['success'] else f"Error: {r.get('stderr', 'Failed')}"


@mcp.tool()
async def go_back() -> str:
    """Press the Back button."""
    r = _run('input keyevent 4', shell=True, timeout=5)
    return "Back button pressed" if r['success'] else f"Error: {r.get('stderr', 'Failed')}"


@mcp.tool()
async def open_recent_apps() -> str:
    """Open the recent apps / app switcher."""
    r = _run('input keyevent 187', shell=True, timeout=5)
    return "Recent apps opened" if r['success'] else f"Error: {r.get('stderr', 'Failed')}"


@mcp.tool()
async def get_current_app() -> str:
    """Get the currently focused app (package name and activity)."""
    # Try dumpsys
    r = _run("dumpsys activity activities | grep -E 'mResumedActivity|mCurrentFocus' | head -3",
             shell=True, timeout=10)
    if r['success'] and r.get('stdout'):
        return r['stdout']
    # Fallback
    r = _run("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp' | head -3",
             shell=True, timeout=10)
    return r.get('stdout', r.get('error', 'Failed to get current app'))


# ---------------------------------------------------------------------------
# Camera & Photos
# ---------------------------------------------------------------------------

@mcp.tool()
async def take_photo(camera_id: str = "0", output_path: str = "/data/data/com.termux/files/home/photo.jpg") -> str:
    """Take a photo using the phone camera.

    Args:
        camera_id: Camera ID - '0' for back camera, '1' for front camera
        output_path: Where to save the photo
    """
    result = _termux('termux-camera-photo', ['-c', camera_id, output_path], timeout=15)
    if Path(output_path).exists():
        size = Path(output_path).stat().st_size
        return f"Photo saved to {output_path} ({size:,} bytes)"
    return result or "Failed to take photo"


@mcp.tool()
async def get_camera_info() -> str:
    """Get information about available cameras on the device."""
    return _format_json(_termux('termux-camera-info'))


@mcp.tool()
async def list_photos(directory: str = "/storage/emulated/0/DCIM/Camera", limit: int = 30) -> str:
    """List photo files in a directory.

    Args:
        directory: Directory to list photos from (default: phone camera folder)
        limit: Maximum number of files to list
    """
    path = Path(directory)
    if not path.exists():
        # Try alternate paths
        for alt in ['/storage/emulated/0/DCIM', '/storage/emulated/0/Pictures',
                    '/sdcard/DCIM/Camera', '/sdcard/DCIM', '/sdcard/Pictures']:
            if Path(alt).exists():
                path = Path(alt)
                break
        else:
            return f"Error: Photo directory not found. Tried {directory} and common alternatives."

    photo_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.bmp'}
    photos = []
    try:
        for f in sorted(path.rglob('*'), key=lambda x: x.stat().st_mtime if x.is_file() else 0, reverse=True):
            if f.is_file() and f.suffix.lower() in photo_exts:
                stat = f.stat()
                photos.append(f"{f.name:<50} {stat.st_size:>12,} bytes  {__import__('time').ctime(stat.st_mtime)}")
                if len(photos) >= limit:
                    break
    except PermissionError:
        return f"Error: Permission denied accessing {path}. Run 'termux-setup-storage' first."

    if not photos:
        return f"No photos found in {path}"

    return f"Photos in {path} ({len(photos)} shown):\n\n" + "\n".join(photos)


@mcp.tool()
async def read_photo(file_path: str) -> str:
    """Read a photo file and return it as base64 encoded data for viewing.

    Args:
        file_path: Path to the image file
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if path.stat().st_size > 5 * 1024 * 1024:
        return f"Error: File too large ({path.stat().st_size:,} bytes). Max 5MB."

    try:
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        ext = path.suffix.lower().lstrip('.')
        mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'webp': 'webp'}.get(ext, 'jpeg')
        return f"data:image/{mime};base64,{data}"
    except Exception as e:
        return f"Error reading photo: {e}"

# ---------------------------------------------------------------------------
# Communication: SMS, Contacts, Clipboard
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_sms(limit: int = 10, type: str = "inbox") -> str:
    """List SMS messages.

    Args:
        limit: Number of messages to retrieve (default: 10)
        type: Message type - 'inbox', 'sent', 'draft', 'all' (default: inbox)
    """
    return _format_json(_termux('termux-sms-list', ['-l', str(limit), '-t', type]))


@mcp.tool()
async def send_sms(number: str, message: str) -> str:
    """Send an SMS message.

    Args:
        number: Phone number to send to
        message: Message text
    """
    return _termux('termux-sms-send', ['-n', number, message])


@mcp.tool()
async def list_contacts() -> str:
    """List all contacts from the phone."""
    return _format_json(_termux('termux-contact-list', timeout=30))


@mcp.tool()
async def get_clipboard() -> str:
    """Get the current clipboard content."""
    return _termux('termux-clipboard-get')


@mcp.tool()
async def set_clipboard(text: str) -> str:
    """Set the clipboard content.

    Args:
        text: Text to copy to clipboard
    """
    result = _termux('termux-clipboard-set', [text])
    return result or f"Clipboard set to: {text[:100]}{'...' if len(text) > 100 else ''}"

# ---------------------------------------------------------------------------
# Notifications & UI Feedback
# ---------------------------------------------------------------------------

@mcp.tool()
async def send_notification(title: str, content: str, id: str = "mcp", vibrate: bool = True) -> str:
    """Send a notification to the phone.

    Args:
        title: Notification title
        content: Notification body text
        id: Notification ID for updates/removal
        vibrate: Whether to vibrate (default: True)
    """
    args = ['--title', title, '-c', content, '--id', id]
    if vibrate:
        args.append('--vibrate')
    # termux-notification reads content from the arguments
    return _termux('termux-notification', args) or f"Notification sent: {title}"


@mcp.tool()
async def show_toast(text: str, short: bool = True) -> str:
    """Show a toast message on the phone screen.

    Args:
        text: Text to show
        short: True for short display, False for long (default: True)
    """
    args = [text]
    if not short:
        args = ['-s'] + args
    return _termux('termux-toast', args) or f"Toast shown: {text}"

# ---------------------------------------------------------------------------
# System Control
# ---------------------------------------------------------------------------

@mcp.tool()
async def set_volume(stream: str, volume: int) -> str:
    """Set a volume level on the phone.

    Args:
        stream: Volume stream - 'music', 'ring', 'alarm', 'notification', 'system', 'call'
        volume: Volume level (0-15 typical range, depends on device)
    """
    return _termux('termux-volume', [stream, str(volume)]) or f"Volume '{stream}' set to {volume}"


@mcp.tool()
async def get_volume() -> str:
    """Get current volume levels for all audio streams."""
    return _format_json(_termux('termux-volume'))


@mcp.tool()
async def toggle_torch(enabled: bool = True) -> str:
    """Turn the flashlight (torch) on or off.

    Args:
        enabled: True to turn on, False to turn off
    """
    return _termux('termux-torch', ['on' if enabled else 'off']) or f"Torch {'on' if enabled else 'off'}"


@mcp.tool()
async def vibrate(duration_ms: int = 1000, force: bool = False) -> str:
    """Vibrate the phone.

    Args:
        duration_ms: Vibration duration in milliseconds (default: 1000)
        force: Vibrate even in silent mode (default: False)
    """
    args = ['-d', str(duration_ms)]
    if force:
        args.append('-f')
    return _termux('termux-vibrate', args) or f"Vibrated for {duration_ms}ms"


@mcp.tool()
async def text_to_speech(text: str, language: str = "zh", rate: float = 1.0) -> str:
    """Speak text aloud using text-to-speech.

    Args:
        text: Text to speak
        language: Language code (e.g. 'en', 'zh', 'ja') (default: zh)
        rate: Speech rate, 1.0 is normal (default: 1.0)
    """
    args = ['-l', language, '-r', str(rate), text]
    return _termux('termux-tts-speak', args, timeout=60) or f"Speaking: {text[:80]}"


@mcp.tool()
async def get_fingerprint() -> str:
    """Prompt for fingerprint authentication on the device."""
    return _format_json(_termux('termux-fingerprint', timeout=30))

# ---------------------------------------------------------------------------
# Media Player
# ---------------------------------------------------------------------------

@mcp.tool()
async def media_player(action: str, file_path: str = "") -> str:
    """Control the media player.

    Args:
        action: One of 'play', 'pause', 'stop', 'info'. Use 'play' with file_path to play a file.
        file_path: Path to media file (required for 'play' action)
    """
    if action == 'play' and file_path:
        return _termux('termux-media-player', ['play', file_path])
    elif action in ('pause', 'stop', 'info'):
        return _format_json(_termux('termux-media-player', [action]))
    return "Error: Use action='play' with a file_path, or 'pause'/'stop'/'info'"

# ---------------------------------------------------------------------------
# Sharing & Downloads
# ---------------------------------------------------------------------------

@mcp.tool()
async def share_file(file_path: str) -> str:
    """Share a file using Android's share dialog.

    Args:
        file_path: Path to the file to share
    """
    if not Path(file_path).exists():
        return f"Error: File not found: {file_path}"
    return _termux('termux-share', [file_path]) or f"Share dialog opened for {file_path}"


@mcp.tool()
async def download_file(url: str, description: str = "MCP Download") -> str:
    """Download a file using Android's download manager.

    Args:
        url: URL to download
        description: Download description shown in notification
    """
    return _termux('termux-download', ['-d', description, url]) or f"Download started: {url}"

# ---------------------------------------------------------------------------
# File System & Command Execution
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_directory(directory_path: str = ".", show_hidden: bool = False) -> str:
    """List contents of a directory with file sizes.

    Args:
        directory_path: Path to directory (default: current directory)
        show_hidden: Show hidden files (default: False)
    """
    path = Path(directory_path)
    if not path.exists():
        return f"Error: Directory not found: {directory_path}"
    if not path.is_dir():
        return f"Error: Not a directory: {directory_path}"

    items = []
    try:
        for item in sorted(path.iterdir()):
            if not show_hidden and item.name.startswith('.'):
                continue
            try:
                stat = item.stat()
                kind = "DIR " if item.is_dir() else "FILE"
                size = stat.st_size if item.is_file() else 0
                items.append(f"{kind} {item.name:<45} {size:>12,} bytes")
            except Exception:
                items.append(f"ERR  {item.name}")
    except PermissionError:
        return f"Error: Permission denied: {directory_path}"

    if not items:
        return f"Directory is empty: {path.absolute()}"

    header = f"Contents of: {path.absolute()}\n{'─' * 70}"
    return f"{header}\n" + "\n".join(items)


@mcp.tool()
async def read_file(file_path: str) -> str:
    """Read the contents of a text file.

    Args:
        file_path: Path to the file to read
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if path.stat().st_size > 10 * 1024 * 1024:
        return f"Error: File too large ({path.stat().st_size:,} bytes)"

    for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return f"Error: Cannot decode file with supported encodings"


@mcp.tool()
async def write_file(file_path: str, content: str) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file
        content: Content to write
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return f"Written {len(content)} chars to {file_path}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def execute_command(command: str, working_directory: str = ".", timeout: int = 30) -> str:
    """Execute a shell command on the phone.

    Args:
        command: Shell command to execute
        working_directory: Working directory (default: current)
        timeout: Timeout in seconds (default: 30)
    """
    cmd_parts = command.strip().split()
    if cmd_parts and cmd_parts[0].lower() in BLOCKED_COMMANDS:
        return f"Error: Command '{cmd_parts[0]}' is blocked for safety"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=working_directory,
            encoding='utf-8', errors='replace',
            env=_ensure_path_env(),
        )
        output = []
        if result.stdout.strip():
            output.append(result.stdout.strip())
        if result.stderr.strip():
            output.append(f"[stderr] {result.stderr.strip()}")
        output.append(f"[exit code: {result.returncode}]")
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"

# ---------------------------------------------------------------------------
# Storage Info
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_storage_info() -> str:
    """Get phone storage usage information (disk space)."""
    r = _run('df -h /storage/emulated/0 /data 2>/dev/null || df -h', shell=True, timeout=10)
    return r.get('stdout', r.get('error', 'Failed'))


@mcp.tool()
async def get_device_info() -> str:
    """Get comprehensive device information (model, Android version, etc.)."""
    commands = {
        'Model': 'getprop ro.product.model',
        'Brand': 'getprop ro.product.brand',
        'Android Version': 'getprop ro.build.version.release',
        'SDK Level': 'getprop ro.build.version.sdk',
        'Build': 'getprop ro.build.display.id',
        'Kernel': 'uname -r',
        'Architecture': 'uname -m',
        'Uptime': 'uptime',
    }
    lines = []
    for label, cmd in commands.items():
        r = _run(cmd, shell=True, timeout=5)
        val = r.get('stdout', '').strip() or 'N/A'
        lines.append(f"{label}: {val}")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Screen & Display
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_screen_brightness() -> str:
    """Get current screen brightness level."""
    r = _run('settings get system screen_brightness', shell=True, timeout=5)
    val = r.get('stdout', '').strip()
    return f"Screen brightness: {val}/255" if val else r.get('error', 'Failed')


@mcp.tool()
async def set_screen_brightness(level: int) -> str:
    """Set screen brightness level.

    Args:
        level: Brightness level 0-255
    """
    level = max(0, min(255, level))
    r = _run(f'settings put system screen_brightness {level}', shell=True, timeout=5)
    return r.get('stdout', '') or f"Brightness set to {level}/255"

# ---------------------------------------------------------------------------
# Sensors & Misc
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_sensor_list() -> str:
    """List all available sensors on the device."""
    return _format_json(_termux('termux-sensor', ['-l']))


@mcp.tool()
async def read_sensor(sensor_name: str, count: int = 1) -> str:
    """Read data from a specific sensor.

    Args:
        sensor_name: Name of the sensor (use get_sensor_list to see available sensors)
        count: Number of readings to take (default: 1)
    """
    return _format_json(_termux('termux-sensor', ['-s', sensor_name, '-n', str(count)], timeout=15))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
