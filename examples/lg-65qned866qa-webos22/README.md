# LG 65QNED866QA (QNED86, 2022)

| | |
|---|---|
| webOS | webOS 22, 7.6.0 |
| Firmware | 04.60.91 |
| Region | Spain |
| Root | Homebrew Channel, SSH |
| Tested | 2026-10-28 |

- **promos-off:** `sportsAlarm`, `livePromotion` and `webOSPromotionVideo` were on; the rest were already off.
- **preload-off** with `preload.txt`: works, from the next cold boot.
- **hide-apps** with `hide.txt`: Home went from 22 tiles to 15 after a reboot. Removing an id from the list and
  rebooting brought that app back, so `show-apps` works.
- **LG Channels** runs from an updated copy in `/media/system/apps/...` and ignores `deletedSystemAppList.json`.
  It needs `"visible":false` in that copy's `appinfo.json`; its file has no `visible` key, so the key is added.
- `blockedAppList/ESP.json` is rewritten at every boot; `blockedSystemAppList` does not exist on this firmware.
- The LG Content Store keeps working, so apps such as Netflix still update.
- This model is not on LG's webOS Re:New list (only the 2022 OLEDs and the QNED95/99 are), so it stays on webOS 22.
