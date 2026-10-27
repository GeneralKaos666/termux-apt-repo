TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/termux-settings
TERMUX_PKG_DESCRIPTION="Keyboard-driven TUI to change Termux colors, app theme, and fonts"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="1.1.1"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/termux-settings/archive/refs/tags/v1.1.1.tar.gz"
TERMUX_PKG_SHA256=2f77a0db3c38696ac10aa152a52731aafe5c582dcda40b3b6eaca16f768cb768
TERMUX_PKG_DEPENDS="termux-tools"
TERMUX_PKG_BUILD_IN_SRC=true

termux_step_make() {
	termux_setup_rust
	cargo build --release
}

termux_step_make_install() {
	install -Dm755 target/release/termux-settings "${TERMUX_PREFIX}/bin/termux-settings"
}
