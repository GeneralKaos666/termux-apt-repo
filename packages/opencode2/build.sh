TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/opencode-android
TERMUX_PKG_DESCRIPTION="OpenCode AI coding assistant for Android/Termux"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="2.1.4-1"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/opencode-android/archive/refs/tags/v2.1.4-android.tar.gz"
TERMUX_PKG_SHA256=SKIP_CHECKSUM
TERMUX_PKG_DEPENDS="ripgrep, libc++"

# opencode2 ships a prebuilt Bun binary (opencode2.bin) plus a launcher
# wrapper and a LICENSE. The binary is produced by the opencode-android
# release workflow rather than built here from source.
# TODO: wire the exact release-asset URL + sha256 for opencode2.bin.
termux_step_make_install() {
	install -Dm755 opencode2 "${TERMUX_PREFIX}/bin/opencode2"
	install -Dm755 opencode2.bin "${TERMUX_PREFIX}/libexec/opencode2/opencode2.bin"
	ln -sf opencode2 "${TERMUX_PREFIX}/bin/opencode"
	install -Dm644 LICENSE "${TERMUX_PREFIX}/share/doc/opencode2/LICENSE"
}
