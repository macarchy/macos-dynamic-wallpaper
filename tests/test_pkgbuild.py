"""The PKGBUILD must land everything install.sh lands.

Two install channels that drift apart are worse than one: the package installs
cleanly and is missing a file nobody notices until it is needed. This reads both
and asserts they agree on WHAT ships — the destinations differ by design, since
install.sh works in $HOME and the package works in /usr. macarchy-install#17.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKGBUILD = (ROOT / "PKGBUILD").read_text()
# Comments name every artefact, so a substring match over the whole file passes
# even when the install line is gone. Match the code.
PKG_CODE = "\n".join(l for l in PKGBUILD.splitlines() if not l.lstrip().startswith("#"))
INSTALL = (ROOT / "install.sh").read_text()

INSTALLED = [
    "bin/macos-dynamic-wallpaper",
    "systemd/macos-dynamic-wallpaper.service",
    "systemd/macos-dynamic-wallpaper.timer",
    "examples/dynamic-wallpaper.json",
]


def test_the_package_carries_everything_install_sh_does():
    missing = [a for a in INSTALLED if a.split("/")[-1].split(".")[0] not in PKG_CODE
               and a not in PKG_CODE]
    assert not missing, f"install.sh installs {missing}; the PKGBUILD does not"


def test_install_sh_still_installs_what_this_test_claims():
    for a in INSTALLED:
        stem = a.split("/")[-1].split(".")[0]
        assert stem in INSTALL, f"{a} is in INSTALLED but install.sh no longer mentions it"


def test_the_units_are_repointed_away_from_HOME():
    # They say %h/.local/bin/… for install.sh's benefit; a package writes nothing
    # into $HOME, so shipping them verbatim gives 203/EXEC.
    assert "%h/" in (ROOT / "systemd" / "macos-dynamic-wallpaper.service").read_text()
    assert "sed 's|%h/" in PKG_CODE
    assert "grep -q '^ExecStart=/usr/bin/'" in PKG_CODE, "the rewrite must be checked, not hoped"


def test_there_is_a_scriptlet_for_what_pacman_cannot_do():
    # install.sh seeds the config into ~/.config; pacman cannot write there.
    assert "install=macos-dynamic-wallpaper.install" in PKG_CODE
    s = (ROOT / "macos-dynamic-wallpaper.install").read_text()
    assert "dynamic-wallpaper.json" in s and "timer" in s


def test_the_package_job_lives_where_it_will_actually_fire():
    # A `release: [published]` trigger never fires: release-please creates the
    # Release with GITHUB_TOKEN, and GitHub raises no run from a GITHUB_TOKEN
    # event. macarchy-install#16 paid for that lesson.
    assert not (ROOT / ".github" / "workflows" / "package.yml").exists()
    wf = (ROOT / ".github" / "workflows" / "release-please.yml").read_text()
    assert "release_created" in wf
    assert "types: [published]" not in wf


def test_pkgver_comes_from_the_tag_at_build_time():
    wf = (ROOT / ".github" / "workflows" / "release-please.yml").read_text()
    assert 's/^pkgver=.*/pkgver=${TAG#v}/' in wf
    assert 'grep -q "^pkgver=${TAG#v}$" PKGBUILD' in wf
    cfg = json.loads((ROOT / "release-please-config.json").read_text())
    assert "extra-files" not in cfg["packages"]["."], "it cannot parse a PKGBUILD"


def test_the_upload_globs_and_clobbers():
    wf = (ROOT / ".github" / "workflows" / "release-please.yml").read_text()
    assert "*.pkg.tar.*" in wf, "hardcoding an extension uploads nothing when PKGEXT differs"
    assert "--clobber" in wf
    assert "github-cli" in wf, "gh lives on the runner, not inside the container"
    assert "pacman -Syu" in wf, "a partial upgrade reads as a build bug"
