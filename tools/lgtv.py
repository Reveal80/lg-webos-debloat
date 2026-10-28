#!/usr/bin/env python3
"""lgtv.py: control a rooted LG webOS TV from your computer over SSH. Python 3.8+, standard library only.

The same functions as a home-server control panel, one subcommand each:

  lgtv.py <ip> status                      power, app on screen, volume, webOS version, MAC (for wake)
  lgtv.py <ip> wake --mac 00:11:22:33:44:55  Wake-on-LAN (turn on "Turn on via Wi-Fi/LAN" in the TV settings)
  lgtv.py <ip> off | screen-off | screen-on
  lgtv.py <ip> screenshot [file.jpg]       the whole display, Live TV included (unlike Android TV)
  lgtv.py <ip> toast "text"                short message in the corner, goes away by itself
  lgtv.py <ip> alert "text" [--title T]    message box with an OK button, stays until pressed
  lgtv.py <ip> pair                        once: accept the prompt on the TV, so key presses work
  lgtv.py <ip> key up down ok back home menu exit info ...
  lgtv.py <ip> volume [0-100] | mute on|off
  lgtv.py <ip> apps | app <id> | input <1-4> | live
  lgtv.py <ip> channels | channel <channelId|number>
  lgtv.py <ip> picture [key=value ...]     e.g. picture backlight=30 pictureMode=cinema
  lgtv.py <ip> luna <uri> ['<json>']       any luna call, for experiments

Needs root with the Homebrew Channel and SSH on. Extra ssh options: LGTV_SSH="-i ~/.ssh/lgtv".
Scheduled messages: put a toast in cron, e.g. `0 21 * * * /path/tools/lgtv.py 192.168.0.50 toast "Bedtime"`.
"""
import argparse, base64, json, os, re, shlex, socket, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(os.path.expanduser("~"), ".config", "lgtv")
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=6", "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2",
            "-o", "LogLevel=ERROR"] + shlex.split(os.environ.get("LGTV_SSH", ""))
BUTTONS = {"up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT", "ok": "ENTER", "back": "BACK", "menu": "MENU",
           "exit": "EXIT", "info": "INFO", "home": "HOME", "red": "RED", "green": "GREEN", "yellow": "YELLOW", "blue": "BLUE",
           "play": "PLAY", "pause": "PAUSE", "stop": "STOP", "ff": "FASTFORWARD", "rew": "REWIND",
           "ch_up": "CHANNELUP", "ch_down": "CHANNELDOWN", "vol_up": "VOLUMEUP", "vol_down": "VOLUMEDOWN", "mute": "MUTE"}
PICTURE_KEYS = ["pictureMode", "backlight", "contrast", "brightness", "color", "energySaving"]


def die(msg):
    sys.exit(f"lgtv: {msg}")


def ssh(host, cmd, timeout=40, tty=True):
    """Shell command on the TV as root. -tt because luna-send wants a terminal."""
    argv = ["ssh"] + (["-tt"] if tty else []) + SSH_OPTS + [f"root@{host}", cmd + "; exit"]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        die("the TV did not answer in time")
    return r.stdout.replace("\r", ""), r.returncode


def _dq(t):
    return t.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")


def luna_sh(uri, payload="{}"):
    """luna-send wrapped in script(1) for a pty: without one it prints nothing for large replies."""
    inner = f"luna-send -n 1 -f {uri} '{payload.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'"
    return f'script -q -c "{_dq(inner)}" /dev/null 2>/dev/null'


def luna(host, uri, payload="{}", timeout=20):
    out, _ = ssh(host, luna_sh(uri, payload), timeout)
    m = re.search(r"\{.*\}", out, re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}


def ok(d, what):
    if d.get("returnValue"):
        print(what)
    else:
        die(f"{what.split(':')[0]} failed: {d.get('errorText') or d or 'no answer'}")


def settings(host, cat, keys):
    return luna(host, "luna://com.webos.settingsservice/getSystemSettings", json.dumps({"category": cat, "keys": keys})).get("settings", {})


# ------------------------------------------------------------------ commands
def c_status(a):
    h = a.host
    p = luna(h, "luna://com.webos.service.tvpower/power/getPowerState")
    fg = luna(h, "luna://com.webos.applicationManager/getForegroundAppInfo")
    v = luna(h, "luna://com.webos.audio/getVolume")
    info, _ = ssh(h, "nyx-cmd OSInfo query webos_release; nyx-cmd OSInfo query webos_manufacturing_version; "
                     "nyx-cmd DeviceInfo query product_id; for i in wlan0 eth0; do cat /sys/class/net/$i/address 2>/dev/null; done", tty=False)
    i = info.split()
    print(f"power:   {p.get('state', '?')}")
    print(f"on screen: {fg.get('appId') or '-'}")
    print(f"volume:  {v.get('volume', '?')}{' (muted)' if v.get('muteStatus') else ''}")
    if len(i) >= 3:
        print(f"model:   {i[2]}  webOS {i[0]}  firmware {i[1]}")
    for mac in i[3:]:
        print(f"MAC:     {mac}  (for: lgtv.py <ip> wake --mac {mac})")


def c_wake(a):
    if not a.mac or not re.fullmatch(r"([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", a.mac):
        die("give the TV's MAC with --mac (lgtv.py <ip> status shows it while the TV is on)")
    data = bytes.fromhex("FF" * 6 + re.sub(r"[:-]", "", a.mac) * 16)
    bcast = a.broadcast or ".".join(a.host.split(".")[:3] + ["255"])
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for dst in ("255.255.255.255", bcast):
            s.sendto(data, (dst, 9))
    print(f"Wake-on-LAN sent to {a.mac}; the TV takes about 10 s")


def c_off(a):
    # Detached on the TV: it drops off the network without closing SSH, which would hang this command.
    ssh(a.host, "setsid -f sh -c 'sleep 1; luna-send -n 1 luna://com.webos.service.tvpower/power/powerOff "
                "\"{\\\"reason\\\":\\\"remoteKey\\\"}\"' </dev/null >/dev/null 2>&1; sleep 0.3", 20)
    print("power off sent")


def c_screen(a):
    on = a.cmd == "screen-on"
    ok(luna(a.host, f"luna://com.webos.service.tvpower/power/{'turnOnScreen' if on else 'turnOffScreen'}"), f"screen {'on' if on else 'off'}")


def c_screenshot(a):
    out = a.file or "lgtv-screenshot.jpg"
    d = luna(a.host, "luna://com.webos.service.capture/executeOneShot",
             '{"path":"/tmp/lgtv-shot.jpg","method":"DISPLAY","format":"JPG","width":1920,"height":1080}', 30)
    if not d.get("returnValue"):
        die(f"capture failed: {d.get('errorText') or 'no answer'}")
    r = subprocess.run(["scp", "-q"] + SSH_OPTS + [f"root@{a.host}:/tmp/lgtv-shot.jpg", out], capture_output=True, text=True, timeout=40)
    ssh(a.host, "rm -f /tmp/lgtv-shot.jpg", tty=False)
    if r.returncode or not os.path.exists(out):
        die("could not copy the screenshot: " + r.stderr.strip())
    print(f"saved {out} ({os.path.getsize(out) // 1024} KB)")


def c_toast(a):
    ok(luna(a.host, "luna://com.webos.notification/createToast", json.dumps({"message": a.text[:200]}, ensure_ascii=False)), "message shown")


def c_alert(a):
    p = {"title": a.title, "message": a.text[:200], "buttons": [{"label": a.button}]}
    ok(luna(a.host, "luna://com.webos.notification/createAlert", json.dumps(p, ensure_ascii=False)), "alert shown")


def _keyfile(host):
    return os.path.join(CONF, f"client-key-{host}")


def _ssap(host, *args, timeout=20):
    js = base64.b64encode(open(os.path.join(HERE, "ssap-button.js"), "rb").read()).decode()
    cmd = (f"echo {js} | base64 -d > /tmp/ssap-button.js; "
           f"NODE_TLS_REJECT_UNAUTHORIZED=0 node --no-warnings /tmp/ssap-button.js {' '.join(shlex.quote(x) for x in args)}")
    return ssh(host, cmd, timeout, tty=False)


def c_pair(a):
    print("Accept the request on the TV screen (60 s)...")
    out, _ = _ssap(a.host, "--pair", timeout=75)
    m = re.search(r"CLIENT-KEY (\S+)", out)
    if not m:
        die(out.strip() or "pairing failed")
    os.makedirs(CONF, exist_ok=True)
    with open(_keyfile(a.host), "w") as f:
        f.write(m.group(1))
    os.chmod(_keyfile(a.host), 0o600)
    print(f"paired; key saved in {_keyfile(a.host)}")


def c_key(a):
    try:
        key = open(_keyfile(a.host)).read().strip()
    except OSError:
        die("not paired yet: run  lgtv.py <ip> pair  first")
    for k in a.keys:
        if k.lower() not in BUTTONS:
            die(f"unknown key {k}; known: {' '.join(BUTTONS)}")
        out, rc = _ssap(a.host, key, BUTTONS[k.lower()])
        if rc:
            die(out.strip() or f"key {k} failed")
    print("sent: " + " ".join(a.keys))


def c_volume(a):
    if a.level is None:
        v = luna(a.host, "luna://com.webos.audio/getVolume")
        print(f"volume {v.get('volume', '?')}{' (muted)' if v.get('muteStatus') else ''}")
    else:
        n = max(0, min(100, a.level))
        ok(luna(a.host, "luna://com.webos.audio/setVolume", json.dumps({"volume": n})), f"volume {n}")


def c_mute(a):
    ok(luna(a.host, "luna://com.webos.audio/setMute", json.dumps({"mute": a.state == "on"})), f"mute {a.state}")


def c_apps(a):
    d = luna(a.host, "luna://com.webos.applicationManager/listLaunchPoints", timeout=30)
    for p in d.get("launchPoints", []):
        print(f"{p.get('id', ''):45} {p.get('title', '')}{'  (system)' if p.get('systemApp') else ''}")


def _launch(host, app_id, params=None):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", app_id):
        die("bad app id")
    ok(luna(host, "luna://com.webos.applicationManager/launch", json.dumps({"id": app_id, **({"params": params} if params else {})})), f"opened {app_id}")


def c_app(a):
    _launch(a.host, a.id)


def c_input(a):
    _launch(a.host, f"com.webos.app.hdmi{a.n}")


def c_live(a):
    _launch(a.host, "com.webos.app.livetv")


def _channels(host):
    d = luna(host, "luna://com.webos.service.apiadapter/tv/getChannelList", "{}", 40)
    return d.get("channelList") or []


def c_channels(a):
    for c in _channels(a.host):
        print(f"{c.get('channelNumber', ''):>5}  {c.get('channelName', ''):30} {c.get('channelId', '')}{'  (radio)' if c.get('Radio') else ''}")


def c_channel(a):
    cid = a.channel
    if re.fullmatch(r"\d{1,4}", cid):   # a number: look its id up
        m = [c for c in _channels(a.host) if str(c.get("channelNumber")) == cid]
        if not m:
            die(f"no channel number {cid}")
        cid = m[0]["channelId"]
    if not re.fullmatch(r"[0-9_]+", cid):
        die("bad channel id")
    # launch Live TV first; openChannel (not launch with channelId) retunes even when Live TV is already showing
    luna(a.host, "luna://com.webos.applicationManager/launch", '{"id":"com.webos.app.livetv"}')
    ok(luna(a.host, "luna://com.webos.service.apiadapter/tv/openChannel", json.dumps({"channelId": cid})), f"channel {a.channel}")


def c_picture(a):
    if not a.set:
        for k, v in settings(a.host, "picture", PICTURE_KEYS).items():
            print(f"{k:14} {v}")
        return
    s = {}
    for kv in a.set:
        k, _, v = kv.partition("=")
        if k not in PICTURE_KEYS or not v:
            die(f"use key=value with one of: {' '.join(PICTURE_KEYS)}")
        s[k] = v
    ok(luna(a.host, "luna://com.webos.settingsservice/setSystemSettings", json.dumps({"category": "picture", "settings": s})), f"picture: {s}")


def c_luna(a):
    print(json.dumps(luna(a.host, a.uri, a.payload, 40), indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(prog="lgtv.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host", help="TV IP address")
    sp = ap.add_subparsers(dest="cmd", required=True, metavar="command")
    def cmd(name, fn, **kw):
        p = sp.add_parser(name, **kw); p.set_defaults(fn=fn); return p
    cmd("status", c_status)
    p = cmd("wake", c_wake); p.add_argument("--mac"); p.add_argument("--broadcast")
    cmd("off", c_off); cmd("screen-off", c_screen); cmd("screen-on", c_screen)
    p = cmd("screenshot", c_screenshot); p.add_argument("file", nargs="?")
    p = cmd("toast", c_toast); p.add_argument("text")
    p = cmd("alert", c_alert); p.add_argument("text"); p.add_argument("--title", default="Message"); p.add_argument("--button", default="OK")
    cmd("pair", c_pair)
    p = cmd("key", c_key); p.add_argument("keys", nargs="+")
    p = cmd("volume", c_volume); p.add_argument("level", nargs="?", type=int)
    p = cmd("mute", c_mute); p.add_argument("state", choices=["on", "off"])
    cmd("apps", c_apps)
    p = cmd("app", c_app); p.add_argument("id")
    p = cmd("input", c_input); p.add_argument("n", type=int, choices=[1, 2, 3, 4])
    cmd("live", c_live)
    cmd("channels", c_channels)
    p = cmd("channel", c_channel); p.add_argument("channel")
    p = cmd("picture", c_picture); p.add_argument("set", nargs="*")
    p = cmd("luna", c_luna); p.add_argument("uri"); p.add_argument("payload", nargs="?", default="{}")
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
