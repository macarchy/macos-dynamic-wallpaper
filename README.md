# macos-dynamic-wallpaper

The macOS dynamic desktop, for [Omarchy](https://omarchy.org): one wallpaper
set, four times of day, and the background follows the sun where you actually
are.

    macos-dynamic-wallpaper status

A `oneshot` service behind a five-minute timer. It reads a small JSON file,
works out whether it is dawn, day, dusk or night, and applies the matching
image through `omarchy-theme-bg-set`. No daemon, no polling loop, nothing
resident.

## Install

    git clone https://github.com/macarchy/macos-dynamic-wallpaper
    cd macos-dynamic-wallpaper && ./install.sh

The tool lands in `~/.local/bin`, the timer in your user systemd tree, and — 
only if you do not already have one — a starter config at
`~/.config/omarchy/dynamic-wallpaper.json`. Re-running never overwrites your
config and never re-enables a timer you turned off.

It ships as part of [macarchy-install](https://github.com/macarchy/macarchy-install),
so on a macarchy machine you already have it.

## Configuration

Everything lives in `~/.config/omarchy/dynamic-wallpaper.json`
([full example](examples/dynamic-wallpaper.json)):

```json
{
  "theme": "apple-glass",
  "mode": "solar",
  "latitude": 37.3230,
  "longitude": -122.0322,
  "twilight_margin_minutes": 45,
  "set": "tahoe-beach",
  "sets": {
    "tahoe-beach": {
      "dawn": "26-tahoe-beach-dawn.jpg",
      "day":  "26-tahoe-beach-day.jpg",
      "dusk": "26-tahoe-beach-dusk.jpg",
      "night": "26-tahoe-beach-night.jpg"
    }
  }
}
```

| Key | What it does |
| --- | --- |
| `theme` | Only touch the background while this theme is active. Leave it empty to manage every theme. |
| `mode` | `solar` for real sunrise/sunset at your coordinates, `fixed` for clock times. |
| `latitude` / `longitude` | Required in `solar` mode. Decimal degrees, east and north positive. |
| `twilight_margin_minutes` | How long dawn and dusk last around sunrise and sunset when civil twilight is unavailable. |
| `schedule` | Required in `fixed` mode: `HH:MM` for each of the four phases. |
| `set` | Which entry of `sets` to use. |
| `sets` | Named four-image sets. Filenames resolve under `~/.config/omarchy/backgrounds/<theme>/`. |

The images are whatever your theme ships — the sets in the example are the
[apple-glass](https://github.com/macarchy/apple-glass) backgrounds. Point them
at your own and it works the same.

## How it decides

`solar` mode uses the NOAA sunrise equation, good to about a minute, so no
network and no location service. Dawn runs from civil dawn to sunrise plus the
margin, dusk from sunset minus the margin to civil dusk, and day and night take
the rest. Above the polar circles, where the sun never crosses, it settles on
`day` or `night` for the whole period instead of failing.

A solar day's sunset can land after midnight UTC, and its sunrise before it, so
the phase you are in may belong to yesterday's or tomorrow's solar day. It
checks all three. Skipping that is how a longitude of -122° never saw dusk and
+140° never saw dawn.

## What it will not do

- Touch the background while a theme it does not manage is active.
- Re-apply an image that is already on screen (pass `--force` to override).
- Run as a daemon. It exits after each pass; the timer brings it back.

After it sets a wallpaper it pokes `macarchy-bar-contrast.service`, so a
transparent bar re-picks its text colour against the ground that just changed
rather than waiting for its own next tick. Harmless if that unit is absent.

## Commands

    macos-dynamic-wallpaper            # apply the image for right now
    macos-dynamic-wallpaper apply      # the same thing, said out loud
    macos-dynamic-wallpaper --force    # apply even if the image is unchanged
    macos-dynamic-wallpaper status     # phase, times, chosen image; changes nothing

`status` is the one to reach for when the wallpaper is not what you expected:
it prints the active theme, the computed sunrise and sunset in local time, the
phase it landed on, and the exact file it would apply.

## Tests

    python3 -m pytest tests/ -q

Pure standard library, no desktop required — the suite runs against a temporary
XDG tree.

## License

MIT. Built and tuned on a MacBook Pro (13-inch, M2) running Omarchy on
[Asahi Linux](https://asahilinux.org), but there is nothing Apple-specific in
it: any Omarchy desktop will do.
