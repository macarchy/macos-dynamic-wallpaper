"""Checks for the parts that decide which image lands on the screen.

The module reads XDG variables at import time, so every test that touches the
filesystem imports it fresh against a temp tree -- same loader trick as
macarchy-core's test_macarchy_sun.py, since the tool has no .py extension.
"""
import importlib.machinery
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "macos-dynamic-wallpaper"

# Liege: a longitude where sunrise and sunset both sit inside one UTC day, so
# the simple cases stay simple. The awkward longitudes get their own test.
LAT, LON = 50.6337, 5.5675


def load_script():
    loader = importlib.machinery.SourceFileLoader("mdw", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mdw", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def mdw():
    return load_script()


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A throwaway XDG tree, imported into a fresh copy of the module."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / ".local" / "state"))
    (tmp_path / ".config" / "omarchy" / "backgrounds" / "apple-glass").mkdir(parents=True)
    (tmp_path / ".local" / "state" / "omarchy" / "current").mkdir(parents=True)
    return tmp_path, load_script()


# --- solar phases -----------------------------------------------------------

def test_solar_phase_names_the_four_parts_of_the_day(mdw):
    def at(hour_utc):
        return mdw.solar_phase(LAT, LON, datetime(2026, 6, 21, hour_utc, tzinfo=timezone.utc), 45)

    # June 21 at Liege: sunrise 03:25 UTC, sunset 19:53 UTC.
    assert at(1) == "night"
    assert at(4) == "dawn"
    assert at(12) == "day"
    assert at(20) == "dusk"


@pytest.mark.parametrize("place,lat,lon,hour,expected", [
    # Sunset lands after midnight UTC, so dusk belongs to the previous solar
    # day. Before the three-day window it read as night and never fired.
    ("Cupertino", 37.3230, -122.0322, 3, "dusk"),
    ("Cupertino", 37.3230, -122.0322, 13, "dawn"),
    # Mirror image: sunrise lands before midnight UTC, so dawn belongs to the
    # next solar day.
    ("Tokyo", 35.68, 139.69, 19, "dawn"),
    ("Tokyo", 35.68, 139.69, 2, "day"),
])
def test_every_phase_is_reachable_across_the_utc_day_boundary(mdw, place, lat, lon, hour, expected):
    when = datetime(2026, 6, 21, hour, tzinfo=timezone.utc)
    assert mdw.solar_phase(lat, lon, when, 45) == expected, place


def test_polar_day_and_night_do_not_raise(mdw):
    """Above the circle the sun never crosses, and solar_pair returns a string."""
    midsummer = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
    midwinter = datetime(2026, 12, 21, 12, tzinfo=timezone.utc)
    assert mdw.solar_phase(78.2, 15.6, midsummer, 45) == "day"     # Svalbard
    assert mdw.solar_phase(78.2, 15.6, midwinter, 45) == "night"


def test_margin_widens_dawn_at_the_expense_of_day(mdw):
    when = datetime(2026, 6, 21, 4, 30, tzinfo=timezone.utc)
    assert mdw.solar_phase(LAT, LON, when, 5) == "day"
    assert mdw.solar_phase(LAT, LON, when, 120) == "dawn"


# --- fixed schedule ---------------------------------------------------------

SCHEDULE = {"dawn": "06:00", "day": "09:00", "dusk": "19:00", "night": "21:30"}


@pytest.mark.parametrize("hh,mm,expected", [
    (7, 0, "dawn"),
    (12, 0, "day"),
    (20, 0, "dusk"),
    (23, 0, "night"),
    (9, 0, "day"),      # a boundary belongs to the phase it opens
    (21, 30, "night"),
])
def test_fixed_phase(mdw, hh, mm, expected):
    assert mdw.fixed_phase(SCHEDULE, datetime(2026, 6, 21, hh, mm)) == expected


def test_before_the_first_entry_is_still_yesterdays_last_phase(mdw):
    """03:00 is earlier than every entry, so the day has not turned over yet."""
    assert mdw.fixed_phase(SCHEDULE, datetime(2026, 6, 21, 3, 0)) == "night"


def test_fixed_mode_without_a_schedule_exits_rather_than_guessing(mdw):
    with pytest.raises(SystemExit):
        mdw.fixed_phase({}, datetime(2026, 6, 21, 12, 0))


# --- picking the image ------------------------------------------------------

def config(**over):
    cfg = {
        "theme": "apple-glass", "mode": "fixed", "schedule": SCHEDULE,
        "set": "tahoe", "sets": {"tahoe": {"dawn": "d.jpg", "day": "n.jpg",
                                           "dusk": "k.jpg", "night": "t.jpg"}},
    }
    cfg.update(over)
    return cfg


def test_resolve_image_returns_the_file_for_the_phase(tree):
    root, mdw = tree
    (root / ".config/omarchy/backgrounds/apple-glass/n.jpg").write_bytes(b"")
    assert mdw.resolve_image(config(), "day").name == "n.jpg"


def test_missing_image_exits_instead_of_setting_a_broken_path(tree):
    _, mdw = tree
    with pytest.raises(SystemExit):
        mdw.resolve_image(config(), "day")


def test_unknown_set_or_phase_exits(tree):
    root, mdw = tree
    (root / ".config/omarchy/backgrounds/apple-glass/n.jpg").write_bytes(b"")
    with pytest.raises(SystemExit):
        mdw.resolve_image(config(set="nope"), "day")
    with pytest.raises(SystemExit):
        mdw.resolve_image(config(), "noon")


# --- what apply actually does -----------------------------------------------

def run_apply(root, mdw, monkeypatch, cfg, theme_name, argv=("x", "apply"), at_hour=12):
    """main() reads the wall clock, so pin it -- otherwise the phase, and with
    it the expected image, changes depending on when the suite runs."""
    real = mdw.datetime

    class Pinned(real):
        @classmethod
        def now(cls, tz=None):
            return real(2026, 6, 21, at_hour, tzinfo=tz) if tz else real(2026, 6, 21, at_hour)

    monkeypatch.setattr(mdw, "datetime", Pinned)
    (root / ".config/omarchy/dynamic-wallpaper.json").write_text(json.dumps(cfg))
    (root / ".local/state/omarchy/current/theme.name").write_text(theme_name)
    calls = []
    monkeypatch.setattr(mdw.subprocess, "run", lambda a, **k: calls.append(a))
    assert mdw.main(list(argv)) == 0
    return calls


def test_apply_sets_the_background_and_pokes_the_bar(tree, monkeypatch):
    root, mdw = tree
    (root / ".config/omarchy/backgrounds/apple-glass/n.jpg").write_bytes(b"")
    calls = run_apply(root, mdw, monkeypatch, config(), "apple-glass",
                      ("x", "apply", "--force"))
    assert calls[0][0] == "omarchy-theme-bg-set"
    assert calls[0][1].endswith("/n.jpg")
    # The bar samples the screen this just repainted; the unit was renamed to
    # macarchy-* on 2026-09-04 and nothing else in the tree would catch a slip.
    assert calls[1] == ["systemctl", "--user", "start", "--no-block",
                        "macarchy-bar-contrast.service"]


def test_a_foreign_theme_is_left_alone(tree, monkeypatch):
    root, mdw = tree
    (root / ".config/omarchy/backgrounds/apple-glass/n.jpg").write_bytes(b"")
    assert run_apply(root, mdw, monkeypatch, config(), "tokyo-night") == []


def test_an_unchanged_background_is_not_reapplied(tree, monkeypatch):
    root, mdw = tree
    image = root / ".config/omarchy/backgrounds/apple-glass/n.jpg"
    image.write_bytes(b"")
    (root / ".local/state/omarchy/current/background").symlink_to(image)
    assert run_apply(root, mdw, monkeypatch, config(), "apple-glass") == []


def test_force_reapplies_the_same_background(tree, monkeypatch):
    root, mdw = tree
    image = root / ".config/omarchy/backgrounds/apple-glass/n.jpg"
    image.write_bytes(b"")
    (root / ".local/state/omarchy/current/background").symlink_to(image)
    calls = run_apply(root, mdw, monkeypatch, config(), "apple-glass",
                      ("x", "apply", "--force"))
    assert calls[0][0] == "omarchy-theme-bg-set"


def test_no_theme_key_means_manage_every_theme(tree, monkeypatch):
    root, mdw = tree
    (root / ".config/omarchy/backgrounds/n.jpg").write_bytes(b"")
    cfg = config(theme="")
    calls = run_apply(root, mdw, monkeypatch, cfg, "whatever", ("x", "apply", "--force"))
    assert calls and calls[0][0] == "omarchy-theme-bg-set"


def test_status_reports_without_touching_the_screen(tree, monkeypatch, capsys):
    root, mdw = tree
    (root / ".config/omarchy/backgrounds/apple-glass/n.jpg").write_bytes(b"")
    calls = run_apply(root, mdw, monkeypatch, config(), "apple-glass", ("x", "status"))
    assert calls == []
    assert "phase:   day" in capsys.readouterr().out


def test_a_missing_config_exits_rather_than_assuming_defaults(tree):
    _, mdw = tree
    with pytest.raises(SystemExit):
        mdw.main(["x", "apply"])


def test_invalid_json_exits(tree):
    root, mdw = tree
    (root / ".config/omarchy/dynamic-wallpaper.json").write_text("{ not json")
    with pytest.raises(SystemExit):
        mdw.main(["x", "apply"])


def test_solar_mode_without_a_location_exits(tree):
    root, mdw = tree
    (root / ".config/omarchy/dynamic-wallpaper.json").write_text(
        json.dumps(config(mode="solar")))
    with pytest.raises(SystemExit):
        mdw.main(["x", "apply"])


def test_the_shipped_example_config_is_valid_and_complete(mdw):
    cfg = json.loads((ROOT / "examples" / "dynamic-wallpaper.json").read_text())
    assert cfg["set"] in cfg["sets"]
    for name, mapping in cfg["sets"].items():
        assert set(mapping) == {"dawn", "day", "dusk", "night"}, name
