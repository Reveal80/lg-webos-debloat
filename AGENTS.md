# AGENTS.md

Instructions for coding agents (Claude Code, Codex, Gemini CLI and others) working in this repository.

## Cleaning a TV

Follow [PROMPT.md](PROMPT.md) on the real TV. The rules that are not negotiable:

- **Only through `tools/lgclean` / `tools/webos-clean.sh`.** Nothing deleted or uninstalled, the read-only
  rootfs untouched, every change undone by `restore`. Dry run (`-n`) before each real run.
- **No service restarts by hand** (SAM, WebAppMgr, configd): restarting SAM gives a black picture on some
  models. Only a normal `reboot`, and only after asking.
- **No firmware updates**, and do not remove the Homebrew Channel's block on LG's update servers.
- **Never hide or stop preloading** Live TV, Home, the LG Content Store, Settings, inputs/HDMI, channel setup,
  software update or the Homebrew Channel. The script refuses them; do not work around it.
- **Nothing personal in the repo:** no IP, MAC, serial, SSAP client key, SSH keys or Wi-Fi names in examples.

## Changing the repository

- `tools/webos-clean.sh` must run on the TV's BusyBox `ash`: no bash features, no Python, no `jq`. Check with
  `sh -n` and, if you have it, `shellcheck -s sh`.
- Every new change must back up what it changes once to `/var/lib/webos-clean/` and be undone by `restore`.
- New models go in `examples/<brand-model-webosNN>/` with `README.md`, `hide.txt` and `preload.txt`.
- Keep the README tables in step with the commands.
