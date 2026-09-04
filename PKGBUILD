# Maintainer: Philippe Matray <phmatray@gmail.com>
#
# Installs system-wide what ./install.sh installs into $HOME. tests/test_pkgbuild.py
# fails if either channel grows a file the other does not carry.
pkgname=macos-dynamic-wallpaper
# Rewritten from the tag by the packaging job before makepkg runs, so the package
# can never carry a version its release does not. This value is the fallback for
# a manual makepkg from a checkout.
pkgver=0.1.1
pkgrel=1
pkgdesc="The macOS dynamic desktop for Omarchy: time-of-day wallpapers that follow the real sun at your coordinates"
arch=('any')
url="https://github.com/macarchy/macos-dynamic-wallpaper"
license=('MIT')
install=macos-dynamic-wallpaper.install
depends=('python')
optdepends=('omarchy: the themes whose backgrounds this cycles through')
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
  cd "$srcdir/$pkgname-$pkgver"

  install -Dm755 bin/macos-dynamic-wallpaper "$pkgdir/usr/bin/macos-dynamic-wallpaper"

  # The shipped units say ExecStart=%h/.local/bin/… because install.sh symlinks
  # there. A package writes nothing into $HOME, so shipping them verbatim gives
  # 203/EXEC on a package that installed perfectly.
  sed 's|%h/\.local/bin/|/usr/bin/|' systemd/macos-dynamic-wallpaper.service \
    > "$srcdir/service.pkg"
  grep -q '^ExecStart=/usr/bin/' "$srcdir/service.pkg"   # or fail the build
  install -Dm644 "$srcdir/service.pkg" \
    "$pkgdir/usr/lib/systemd/user/macos-dynamic-wallpaper.service"
  install -Dm644 systemd/macos-dynamic-wallpaper.timer \
    "$pkgdir/usr/lib/systemd/user/macos-dynamic-wallpaper.timer"

  # install.sh seeds this into ~/.config; a package cannot write there, so it
  # ships as a template and the scriptlet says how to take it.
  install -Dm644 examples/dynamic-wallpaper.json \
    "$pkgdir/usr/share/$pkgname/dynamic-wallpaper.json"

  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
