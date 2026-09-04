#!/bin/bash
# Install macos-dynamic-wallpaper: the tool into ~/.local/bin, the refresh
# timer into the user systemd tree, and -- only when there is none yet -- a
# starter config into ~/.config/omarchy/dynamic-wallpaper.json.
#
# Idempotent: every step converges or says why it skipped. A reinstall never
# overwrites your config and never re-enables a timer you turned off.
set -euo pipefail
cd "$(dirname "$0")"

BIN="$HOME/.local/bin"
UNITS="$HOME/.config/systemd/user"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/dynamic-wallpaper.json"

note() { printf '    %s\n' "$*"; }

mkdir -p "$BIN" "$UNITS" "$(dirname "$CFG")"

install -m755 bin/macos-dynamic-wallpaper "$BIN/"
note "installed $BIN/macos-dynamic-wallpaper"

# The timer is a user choice, so only a first install turns it on. Decide
# before the unit files land, or the check always sees its own copy.
first_install=1
[[ -e $UNITS/macos-dynamic-wallpaper.timer ]] && first_install=0
install -m644 systemd/macos-dynamic-wallpaper.{service,timer} "$UNITS/"
systemctl --user daemon-reload

# Your location and your wallpaper sets live here. Clobbering it on every
# install is how a reinstall silently moves someone back to Cupertino.
if [[ -e $CFG ]]; then
	note "kept your ${CFG/#$HOME/\~}"
else
	install -m644 examples/dynamic-wallpaper.json "$CFG"
	note "seeded ${CFG/#$HOME/\~} -- set latitude/longitude, or switch mode to \"fixed\""
fi

if (( first_install )); then
	systemctl --user enable --now macos-dynamic-wallpaper.timer >/dev/null
	note "timer enabled (refreshes every 5 minutes)"
else
	note "timer left as you had it ($(systemctl --user is-enabled macos-dynamic-wallpaper.timer 2>/dev/null || echo unknown))"
fi

printf '\nInstalled. Check it with: macos-dynamic-wallpaper status\n'
