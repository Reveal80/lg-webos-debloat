#!/bin/sh
# webos-clean.sh: runs ON a rooted LG webOS TV (root shell, BusyBox ash). Normally started by tools/lgclean.
#
#   sh webos-clean.sh [-n] <command> [list-file]
#
#   status                  what is on/off right now (changes nothing)
#   promos-off | promos-on  home/live promotions, sports alerts, ACR (livePlus), recommendations
#   preload-off | preload-on  stop LG keeping unused apps loaded in memory (takes effect on next boot)
#   hide-apps | show-apps   hide built-in system apps from Home (takes effect on next reboot)
#   show-app <id>           bring back one hidden app, leave the rest hidden (next reboot)
#   apply                   promos-off + preload-off + hide-apps
#   restore                 promos-on + preload-on + show-apps
#
#   -n  dry run: print what would change, change nothing.
#
# Every change is backed up once to /var/lib/webos-clean before it is made, so "restore" always goes back
# to the state the TV was in before the first run. Nothing is deleted and the read-only rootfs is not touched.

set -u
D=/var/lib/webos-clean
DRY=0
[ "${1:-}" = "-n" ] && { DRY=1; shift; }
CMD=${1:-help}
LIST=${2:-}

SETTINGS="general:homePromotion,sportsAlarm option:livePromotion,webOSPromotionVideo,promotionStreamer,livePlus other:contentRecommendation"
PRELOAD=/var/preferences/webos-preload-manager-conf.json
DELETED=/var/preferences/com.webos.applicationManager/deletedSystemAppList.json
UPDATED=/media/system/apps/usr/palm/applications   # system apps updated by LG run from here, not from the rootfs
# Never hidden or kept out of memory: the TV stops being usable without them.
PROTECTED=" com.webos.app.livetv com.webos.app.home com.webos.app.discovery com.webos.app.settings com.palm.app.settings
 com.webos.app.inputcommon com.webos.app.hdmi1 com.webos.app.hdmi2 com.webos.app.hdmi3 com.webos.app.hdmi4
 com.webos.app.externalinput.av1 com.webos.app.livemenu com.webos.app.channeledit com.webos.app.channelsetting
 com.webos.app.softwareupdate com.webos.app.notificationcenter com.webos.app.factorywin org.webosbrew.hbchannel "
DEF_HIDE="com.webos.app.sportsteamsettings com.webos.app.homeconnect com.webos.app.igallery amazon.alexa.view com.webos.app.lgchannels"
DEF_PRELOAD="com.webos.app.lgchannels amazon.alexapr"

say() { printf '%s\n' "$*"; }
die() { say "error: $*" >&2; exit 1; }
do_() { if [ $DRY = 1 ]; then say "  [dry run] $*"; else "$@"; fi; }
valid_id() { printf '%s' "$1" | grep -Eq '^[A-Za-z0-9._-]+$'; }
protected() { case "$PROTECTED" in *" $1 "*) return 0;; esac; return 1; }

# luna-send prints nothing for large replies without a terminal: run it under script(1) for a pty.
luna() {
    printf '%s\n' "luna-send -n 1 $1 '$2'" > /tmp/webos-clean.cmd
    script -q -c "sh /tmp/webos-clean.cmd" /dev/null 2>/dev/null | tr -d '\r'
}
get_settings() {   # $1 category, $2 comma list of keys -> {"key":"value",...} or empty
    q=$(printf '%s' "$2" | sed 's/[^,][^,]*/"&"/g')
    luna luna://com.webos.settingsservice/getSystemSettings "{\"category\":\"$1\",\"keys\":[$q]}" \
        | grep -o '"settings":{[^}]*}' | cut -d: -f2-
}

# ids from a list file (one per line, "#" comments) or the defaults
read_ids() {
    if [ -n "$LIST" ]; then
        [ -r "$LIST" ] || die "cannot read $LIST"
        sed 's/#.*//' "$LIST" | tr -s ' \t' '\n\n' | grep .
    else
        printf '%s\n' $1
    fi
}

backup_once() {   # $1 file, $2 backup name
    [ -e "$D/$2" ] && return 0
    [ $DRY = 1 ] && { say "  [dry run] back up $1 to $D/$2"; return 0; }
    mkdir -p "$D" && cp "$1" "$D/$2" && say "  backed up $1 -> $D/$2"
}

status() {
    say "== webOS"
    say "  $(nyx-cmd OSInfo query webos_release 2>/dev/null) (firmware $(nyx-cmd OSInfo query webos_manufacturing_version 2>/dev/null)), model $(nyx-cmd DeviceInfo query product_id 2>/dev/null)"
    say "== Promotion, ACR and recommendation settings (off is what you want)"
    for s in $SETTINGS; do v=$(get_settings "${s%%:*}" "${s#*:}"); say "  ${s%%:*}: ${v:-not available on this TV}"; done
    say "== Preload (false = not kept in memory)"
    if [ -e "$PRELOAD" ]; then { tr ',' '\n' < "$PRELOAD"; echo; } | tr -d '{}"' | sed 's/^version:[0-9]*//; s/^allowedApps://; /^$/d; s/^/  /'
    else say "  $PRELOAD not found"; fi
    say "== Hidden system apps"
    if [ -e "$DELETED" ]; then say "  $(cat "$DELETED")"; else say "  $DELETED not found"; fi
    for a in "$UPDATED"/*/appinfo.json; do
        [ -e "$a" ] && grep -q '"visible":false' "$a" && say "  visible:false  $(basename "$(dirname "$a")")"
    done
    n=$(luna luna://com.webos.applicationManager/listLaunchPoints '{}' | grep -o '"id":"[^"]*"' | wc -l)
    say "  $n tiles on Home right now"
    say "== Backups in $D"
    if [ -n "$(ls "$D" 2>/dev/null)" ]; then ls "$D" | sed 's/^/  /'; else say "  none yet"; fi
}

promos_off() {
    say "== Promotions off"
    for s in $SETTINGS; do
        cat=${s%%:*}; cur=$(get_settings "$cat" "${s#*:}")
        [ -z "$cur" ] && { say "  $cat: not available on this TV, skipped"; continue; }
        if [ ! -s "$D/settings-$cat.json" ]; then
            if [ $DRY = 1 ]; then say "  [dry run] save $cat $cur"; else mkdir -p "$D"; printf '%s\n' "$cur" > "$D/settings-$cat.json"; fi
        fi
        new=$(printf '%s' "$cur" | sed 's/:"[^"]*"/:"off"/g')   # only keys this TV reported are written
        if [ $DRY = 1 ]; then say "  [dry run] $cat: $cur -> $new"
        else luna luna://com.webos.settingsservice/setSystemSettings "{\"category\":\"$cat\",\"settings\":$new}" | grep -q '"returnValue":true' \
            && say "  $cat: $new" || say "  $cat: FAILED"; fi
    done
}

promos_on() {
    say "== Promotions back to their saved values"
    for s in $SETTINGS; do
        cat=${s%%:*}; f="$D/settings-$cat.json"
        [ -s "$f" ] || { say "  $cat: nothing saved"; continue; }
        if [ $DRY = 1 ]; then say "  [dry run] $cat: $(cat "$f")"
        else luna luna://com.webos.settingsservice/setSystemSettings "{\"category\":\"$cat\",\"settings\":$(cat "$f")}" | grep -q '"returnValue":true' \
            && say "  $cat: $(cat "$f")" || say "  $cat: FAILED"; fi
    done
}

preload_off() {
    say "== Preload off"
    [ -e "$PRELOAD" ] || { say "  $PRELOAD not found on this TV, skipped"; return 0; }
    backup_once "$PRELOAD" preload.json
    for id in $(read_ids "$DEF_PRELOAD"); do
        valid_id "$id" || { say "  skipped bad id: $id"; continue; }
        protected "$id" && { say "  skipped protected: $id"; continue; }
        if grep -q "\"$id\":true" "$PRELOAD"; then do_ sed -i "s/\"$id\":true/\"$id\":false/" "$PRELOAD"; say "  $id: false"
        else say "  $id: already off"; fi
    done
    say "  takes effect on the next cold boot"
}

preload_on() {
    say "== Preload restored"
    [ -e "$D/preload.json" ] || { say "  nothing saved"; return 0; }
    do_ cp "$D/preload.json" "$PRELOAD" && say "  $PRELOAD restored (next cold boot)"
}

hide_apps() {
    say "== Hide system apps"
    [ -e "$DELETED" ] || die "$DELETED not found: this webOS version is not supported yet (tested on webOS 22)"
    backup_once "$DELETED" deletedSystemAppList.json
    for id in $(read_ids "$DEF_HIDE"); do
        valid_id "$id" || { say "  skipped bad id: $id"; continue; }
        protected "$id" && { say "  skipped protected: $id"; continue; }
        if [ -e "$UPDATED/$id/appinfo.json" ]; then   # updated copy: the deleted list does not reach it
            a="$UPDATED/$id/appinfo.json"
            backup_once "$a" "appinfo-$id.json"
            if grep -q '"visible"' "$a"; then do_ sed -i 's/"visible": *true/"visible":false/' "$a"
            else do_ sed -i 's/^{/{"visible":false,/' "$a"; fi
            say "  $id: visible:false (updated copy in $UPDATED)"
        fi
        if grep -q "\"$id\"" "$DELETED"; then say "  $id: already hidden"
        else do_ sed -i "s/\"deletedList\":\[/&\"$id\",/" "$DELETED"; say "  $id: hidden"; fi
    done
    do_ sed -i 's/,]/]/' "$DELETED"
    say "  takes effect after a reboot (run: reboot)"
}

show_apps() {
    say "== Show system apps"
    [ -e "$D/deletedSystemAppList.json" ] && do_ cp "$D/deletedSystemAppList.json" "$DELETED" && say "  $DELETED restored"
    for b in "$D"/appinfo-*.json; do
        [ -e "$b" ] || continue
        id=$(basename "$b" .json); id=${id#appinfo-}
        do_ cp "$b" "$UPDATED/$id/appinfo.json" && say "  $id: appinfo.json restored"
    done
    say "  takes effect after a reboot (run: reboot)"
}

case "$CMD" in status|promos-off|promos-on|preload-off|preload-on|hide-apps|show-apps|show-app|apply|restore) ;;
    *) sed -n '3,18p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;; esac
show_app() {
    id=$LIST
    valid_id "$id" || die "give one app id: show-app <id>"
    say "== Show $id"
    if grep -q "\"$id\"" "$DELETED" 2>/dev/null; then
        re=$(printf '%s' "$id" | sed 's/\./\\./g')
        do_ sed -i -e "s/\"$re\",//" -e "s/,\"$re\"\]/]/" -e "s/\[\"$re\"\]/[]/" "$DELETED"
        say "  removed from $DELETED"
    else say "  not in $DELETED"; fi
    if [ -e "$D/appinfo-$id.json" ]; then do_ cp "$D/appinfo-$id.json" "$UPDATED/$id/appinfo.json"; say "  appinfo.json restored"; fi
    say "  takes effect after a reboot (run: reboot)"
}

[ "$(id -u)" = 0 ] || die "run as root (rooted TV with Homebrew Channel)"
command -v luna-send >/dev/null || die "luna-send not found: this does not look like webOS"
case "$CMD" in
    status) status ;;
    promos-off) promos_off ;;
    promos-on) promos_on ;;
    preload-off) preload_off ;;
    preload-on) preload_on ;;
    hide-apps) hide_apps ;;
    show-apps) show_apps ;;
    show-app) show_app ;;
    apply) LIST=; promos_off; preload_off; hide_apps ;;
    restore) promos_on; preload_on; show_apps ;;
esac
