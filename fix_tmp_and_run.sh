#!/data/data/com.termux/files/usr/bin/bash
# Fix /tmp for Termux if needed, then run the wechat task
export TMPDIR=/data/data/com.termux/files/usr/tmp
mkdir -p "$TMPDIR"

cd /data/data/com.termux/files/home/pypro/termux-mcp-server
python do_wechat_task.py
