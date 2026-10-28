# Clean up a rooted LG webOS 22 TV

Turn off LG's promotions and content recognition (ACR), stop unused apps being kept in memory, and hide the
built-in apps you never open from the Home screen, on a **rooted** LG TV running **webOS 22**. Nothing is
deleted, the read-only system partition is never touched, and one command puts everything back.

Inspired by [cleanyourtv](https://github.com/Gathin23/cleanyourtv), which does this for Android TV and Google TV
over ADB but cannot reach LG's webOS. This is an independent project, not affiliated with it or with LG.

## What it changes

| Command | What it does | Takes effect |
|---|---|---|
| `promos-off` | Sets to `off`: home promotions, live TV promotions, promotional videos, the promotion streamer, sports alerts, **Live Plus (ACR)** and content recommendations. Only keys your TV reports are written. | At once |
| `preload-off` | Stops LG keeping apps such as LG Channels, the browser and Alexa loaded in memory after boot, by setting them to `false` in `/var/preferences/webos-preload-manager-conf.json`. They still open, a little slower the first time. | Next cold boot |
| `hide-apps` | Hides built-in system apps from Home by adding them to webOS's own list of removed system apps (`deletedSystemAppList.json`, where LG keeps the preinstalled apps you delete). System apps that LG updated run from a copy in `/media/system/apps`, which that list does not reach: those get `"visible":false` in their `appinfo.json`. While hidden, an app cannot be opened. | After a reboot |
| `show-app <id>` | Brings back one hidden app and leaves the others hidden. | After a reboot |
| `apply` | All three, with the default lists. | |
| `restore` | `promos-on`, `preload-on` and `show-apps`: everything back as it was before the first run. | After a reboot |
| `status` | Shows all of the above. Changes nothing. | |

Every file and setting is backed up to `/var/lib/webos-clean/` on the TV **the first time** it is changed, so
`restore` always goes back to the state before you started, however many times you run it.

Some apps can never be hidden or taken out of memory: Live TV, Home, the LG Content Store (you need it to update
apps), Settings, inputs and HDMI, channel setup, software update and the Homebrew Channel. The script refuses them.

## What you need

- An LG TV on **webOS 22** (webOS 7.x, 2022 models; firmware `04.xx`). Other versions may work in part:
  `status` and `-n` show what would happen without changing anything. Reports are welcome.
- **Root** with the [Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel), and **SSH** turned
  on in its settings. How to root depends on your firmware: see [RootMyTV](https://rootmy.tv),
  [DejaVuln](https://github.com/throwaway96/dejavuln-autoroot) and the
  [crashd method](https://gist.github.com/Maximetinu/bc454b92e92a50bf0b21d1b849c46b69). **Do not update your
  TV's firmware**: LG patches every root method, and the Homebrew Channel blocks updates for that reason.
- A computer on the same network with `ssh`, `scp` and `bash` (Linux, macOS, or WSL on Windows), and Python 3.8+
  for `lgtv.py`.

## Quick start

```sh
git clone https://github.com/Reveal80/lg-webos-debloat.git && cd lg-webos-debloat
tools/lgclean <tv-ip> status                       # look first
tools/lgclean <tv-ip> -n apply                     # dry run: prints what would change
tools/lgclean <tv-ip> promos-off
tools/lgclean <tv-ip> preload-off examples/lg-65qned866qa-webos22/preload.txt
tools/lgclean <tv-ip> hide-apps   examples/lg-65qned866qa-webos22/hide.txt
ssh root@<tv-ip> reboot
```

Changed your mind: `tools/lgclean <tv-ip> restore`, then reboot.

`tools/lgclean` copies `tools/webos-clean.sh` (and the list, if you give one) to `/tmp/webos-clean` on the TV and
runs it there over SSH. You can also copy the script yourself and run `sh webos-clean.sh <command>` on the TV.
Extra ssh options go in `LGCLEAN_SSH`, for example `LGCLEAN_SSH="-i ~/.ssh/lgtv" tools/lgclean ...`.

### With a coding assistant

Paste [`PROMPT.md`](PROMPT.md) into Claude Code, Codex, Gemini CLI or another assistant with shell access, on a
computer on the same network as the TV. It checks your TV, asks which apps you use and builds your own lists.

## Remote control from your computer: `lgtv.py`

`tools/lgtv.py` (Python, standard library only) gives you the TV's everyday functions from a terminal or a
script, over the same SSH connection:

```sh
tools/lgtv.py <tv-ip> status                     # power, app on screen, volume, model, MAC
tools/lgtv.py <tv-ip> screenshot shot.jpg        # what is on screen, menus and Live TV included
tools/lgtv.py <tv-ip> toast "Dinner is ready"    # message in the corner, goes away by itself
tools/lgtv.py <tv-ip> alert "Bedtime" --title Home   # message box that stays until OK is pressed
tools/lgtv.py <tv-ip> pair                       # once: accept the prompt on the TV, then:
tools/lgtv.py <tv-ip> key down down ok back      # remote buttons: arrows, ok, back, home, menu, colours...
tools/lgtv.py <tv-ip> channels                   # numbers, names and ids
tools/lgtv.py <tv-ip> channel 5                  # by number or by channel id
tools/lgtv.py <tv-ip> app netflix | input 2 | live
tools/lgtv.py <tv-ip> volume 15 | mute on
tools/lgtv.py <tv-ip> picture backlight=30 pictureMode=cinema
tools/lgtv.py <tv-ip> off                        # and to turn it on again:
tools/lgtv.py <tv-ip> wake --mac <MAC from status>
```

`tools/lgtv.py -h` lists everything. A few things it took a while to find out:

- **Arrow keys** cannot be sent with `luna-send` on webOS. `key` sends them through LG's own remote API (SSAP,
  `getPointerInputSocket`), using a small script that runs on the TV with the TV's own `node`
  ([`tools/ssap-button.js`](tools/ssap-button.js)). That API wants pairing once; the key is kept in
  `~/.config/lgtv/`.
- **Changing channel** with `launch` and a `channelId` does nothing when Live TV is already on screen; `channel`
  uses `openChannel`, which always retunes.
- **Turning off** over SSH used to hang for minutes, because the TV drops off the network without closing the
  connection. `off` starts the power-off detached on the TV (`setsid -f`) and returns at once.
- **Wake-on-LAN** needs *Turn on via Wi-Fi* (or LAN) enabled in the TV's settings.
- **Scheduled messages** need nothing special: put `toast` or `alert` in cron.
  `0 21 * * 1-5 /path/to/tools/lgtv.py 192.168.0.50 toast "Bedtime"` shows it at 21:00 on weekdays. If the TV is off,
  the message is lost.
- **Screenshots without Android's limits.** On Android TV, a screenshot of Live TV, an HDMI input or a DRM app
  comes out black, because Android refuses to capture protected video. On webOS, `screenshot` asks LG's capture
  service as root for the whole display (`executeOneShot`, method `DISPLAY`), so **Live TV comes out as you see
  it** (tested). HDMI inputs and DRM apps such as Netflix are not tested yet: reports welcome.

## Lists

A list is one app id per line; `#` starts a comment. Find the ids on your TV with `status` or with
`luna-send -n 1 luna://com.webos.applicationManager/listLaunchPoints '{}'`. Tested lists, one folder per model:
[`examples/`](examples/). Without a list, `hide-apps` hides Sports alerts, Home Dashboard, Art Gallery, Amazon Alexa
and LG Channels, and `preload-off` handles LG Channels and Alexa.

## Blocking LG's ads on the network

The TV still shows ads that come from LG's servers. Block those with DNS: [docs/DNS.md](docs/DNS.md) explains how
to use [lg-tv-ad-block](https://github.com/hugobatista/lg-tv-ad-block) in Pi-hole **for the TV only**, because the
list also blocks domains other devices in your home need.

## Things learned the hard way

- `blockedAppList/<country>.json` in `/var/preferences/com.webos.applicationManager/` looks like the right place
  to hide apps, but webOS 22 rewrites it at every boot. `deletedSystemAppList.json` persists.
- `blockedSystemAppList`, which newer webOS versions use, does not exist on webOS 22.
- Restarting SAM (the app manager) to make it reread the lists is what gave other tools a black picture. This
  project only ever asks for a normal reboot.
- `luna-send` prints nothing for large replies when it has no terminal: the script runs it under `script(1)`.
- An SSH session to the TV can hang for many minutes when the TV powers off, because it drops off the network
  without closing the connection. `lgclean` uses `ServerAliveInterval`.

## Disclaimer

This runs as root on your TV. The methods were tested on one TV (see `examples/`), hiding apps and showing them
again included, but your model and firmware may differ. Use `-n` first. You use it at your own risk. Not affiliated with LG
Electronics. LG, webOS and other names are trademarks of their owners.

## License

[GPL-3.0](LICENSE).
