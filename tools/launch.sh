#!/bin/sh
# Launches build/switch/sh2-nx.nro on the test Switch and streams its log to build/nxlink.log:
# sys-remote closes the foreground app, starts hbmenu (title takeover: full memory), opens sphaira
# (the first entry), then nxlink sends the NRO to sphaira's netloader with the stdio server on.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
PY=.venv/bin/python3
taskkill //F //IM nxlink.exe >/dev/null 2>&1 || true
$PY tools/swremote.py "KILL fg" "sleep 3" STARTHBM "sleep 4" "PRESS B" "sleep 2" "PRESS A" "sleep 8" FGAPP
# hbmenu sometimes ignores the first A after its netloader closes: press it again until sphaira listens.
for i in 1 2 3 4; do
    (exec 3<>/dev/tcp/${SWITCH_IP:-172.31.99.188}/28280) 2>/dev/null && break
    $PY tools/swremote.py "PRESS A" "sleep 8" >/dev/null
done
"${DEVKITPRO:-/c/devkitPro}/tools/bin/nxlink.exe" -a "${SWITCH_IP:-172.31.99.188}" -s build/switch/sh2-nx.nro \
    > build/nxlink.log 2>&1 &
echo "nxlink started (log: build/nxlink.log)"
