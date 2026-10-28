# The prompt

Paste this into Claude Code (or another coding assistant with shell access) on a computer on the same network
as the TV, from a clone of this repository. The TV must already be rooted with the Homebrew Channel, with SSH
turned on in its settings. Keep the TV on.

---

I want to clean up my rooted LG webOS TV with the tools in this repository. My TV model is: <MODEL HERE>.
Its IP address is: <IP HERE, or find it>. Work on the real TV, step by step, and ask me before anything that
depends on my preferences.

Rules
- Use `tools/lgclean` and `tools/webos-clean.sh`. Do not write other scripts that change the TV, do not delete
  or uninstall anything, do not touch the read-only rootfs, and never restart SAM or other webOS services by
  hand: a normal `reboot` is the only restart.
- Never update the TV's firmware and never re-enable LG's update servers: it would remove root.
- Run every command with `-n` first and show me what it will change.

Steps
1. Connect: `ssh root@<ip> true`. If it fails, check with me that SSH is on in the Homebrew Channel and how I log
   in (key or password).
2. Run `tools/lgclean <ip> status` and tell me the webOS version, and which promotion settings, preloaded apps and
   hidden apps it reports. If the webOS version is not 22 (7.x), tell me what may not apply, and stop at anything
   the script reports as missing.
3. Promotions: explain what `promos-off` turns off (promotions, sports alerts, Live Plus/ACR, recommendations),
   ask me, then run it.
4. Preload: list the apps marked `true` in the preload section, ask me which I never use (voice assistants,
   LG Channels, the browser...), write them to `my-tv/preload.txt` and run `preload-off my-tv/preload.txt`.
   Never include Live TV, Home, inputs/HDMI, or apps I said I use.
5. Hide apps: list the system apps on my Home screen (`listLaunchPoints`, entries with `"systemApp":true`), with
   their titles, ask me which to hide, write them to `my-tv/hide.txt` with a comment per line and run
   `hide-apps my-tv/hide.txt`. Explain that a hidden app cannot be opened until `show-apps`.
6. Ask me before rebooting (`ssh root@<ip> reboot`), wait for SSH to come back (about a minute) and run `status`
   again to confirm the hidden apps are gone from Home.
7. Ads on the network: if I use Pi-hole or AdGuard Home, explain docs/DNS.md and offer to set it up for the TV's
   IP only.
8. Show me `tools/lgtv.py` (screenshot, messages, remote keys after `pair`, channels, volume, wake/off) and, if I
   want reminders on screen, help me put `lgtv.py <ip> toast "..."` in cron.
9. Finish with a short summary of what changed and the one command that undoes it all:
   `tools/lgclean <ip> restore` followed by a reboot.

If I want to share my lists, prepare `examples/<brand-model-webosNN>/` with `hide.txt`, `preload.txt` and a
`README.md` like the existing example, without my IP, MAC, serial number or anything else personal.
