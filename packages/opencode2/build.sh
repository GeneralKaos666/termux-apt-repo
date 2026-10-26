TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/opencode-android
TERMUX_PKG_DESCRIPTION="OpenCode AI coding assistant for Android/Termux"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="2.1.4-1"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/opencode-android/archive/refs/tags/v2.1.4-android-r2.tar.gz"
TERMUX_PKG_SHA256=SKIP_CHECKSUM
TERMUX_PKG_DEPENDS="ripgrep, libc++"

# `opencode2.bin` is a prebuilt Bun binary from the opencode-android release
# workflow (not built from source here); the launcher and LICENSE are vendored
# in this directory. The release also ships a ready-made
# `opencode2_2.1.4-2_aarch64.deb` if you prefer to mirror that directly.
termux_step_make_install() {
	termux_download "https://github.com/GeneralKaos666/opencode-android/releases/download/v2.1.4-android-r2/opencode2-2.1.4-android-aarch64.zip" opencode2.zip SKIP_CHECKSUM
	unzip -o opencode2.zip opencode2.bin

	install -Dm755 "${TERMUX_PKG_BUILDER_DIR}/opencode2" "${TERMUX_PREFIX}/bin/opencode2"
	install -Dm755 opencode2.bin "${TERMUX_PREFIX}/libexec/opencode2/opencode2.bin"
	ln -sf opencode2 "${TERMUX_PREFIX}/bin/opencode"
	install -Dm644 "${TERMUX_PKG_BUILDER_DIR}/LICENSE" "${TERMUX_PREFIX}/share/doc/opencode2/LICENSE"
}
