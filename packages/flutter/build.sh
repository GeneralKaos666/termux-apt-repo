TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/flutter-for-termux
TERMUX_PKG_DESCRIPTION="Flutter SDK (stable)"
TERMUX_PKG_LICENSE="BSD-3-Clause"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="3.47.8-6"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/flutter-for-termux/archive/refs/heads/main.tar.gz"
TERMUX_PKG_SHA256=SKIP_CHECKSUM
TERMUX_PKG_DEPENDS="git, which, gtk3, xorgproto, ninja, cmake, clang, pkg-config, openjdk-21, wget, curl, unzip, 7zip, binutils, tar, xz-utils"

# This is an architecture-any stub: its postinst downloads the real
# architecture-specific payload (`flutter_${TERMUX_PKG_VERSION}_aarch64.deb`)
# from the flutter-for-termux releases on first install.
termux_step_make_install() {
	: # no payload installed at build time; everything happens in postinst
}

termux_step_create_debscripts() {
	install -Dm755 "${TERMUX_PKG_BUILDER_DIR}/postinst" "${TERMUX_PKG_TMPDIR}/DEBIAN/postinst"
}
