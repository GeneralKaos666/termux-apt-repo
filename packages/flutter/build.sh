TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/flutter-for-termux
TERMUX_PKG_DESCRIPTION="Flutter SDK (stable)"
TERMUX_PKG_LICENSE="BSD 3-Clause"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="3.47.8-7"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/flutter-for-termux/archive/refs/heads/main.tar.gz"
TERMUX_PKG_SHA256=SKIP_CHECKSUM
TERMUX_PKG_DEPENDS="git, which, gtk3, xorgproto, ninja, cmake, clang, pkg-config, openjdk-21, wget, curl, unzip, 7zip, binutils, tar, xz-utils"

# This is an architecture-any stub: its postinst downloads the real
# architecture-specific payload from the flutter-for-termux releases on first
# install, so the package itself has no data files.
TERMUX_PKG_METAPACKAGE=true

termux_step_make_install() {
	: # nothing is installed at build time
}

# The harness only runs the debscripts this hook puts into DEBIAN; files named
# postinst/preinst/postrm in the recipe directory are not copied implicitly.
termux_step_create_debscripts() {
	termux_step_create_debscripts__copy_from_dir "$TERMUX_PKG_BUILDER_DIR" .
}
