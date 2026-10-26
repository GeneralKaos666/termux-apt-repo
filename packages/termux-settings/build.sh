TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/termux-settings
TERMUX_PKG_DESCRIPTION="Keyboard-driven TUI to change Termux colors, app theme, and fonts"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="1.1.0"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/termux-settings/archive/refs/tags/v${TERMUX_PKG_VERSION}.tar.gz"
TERMUX_PKG_SHA256=4d9e0faab45c52a40701ed3ecb1aeeb83fba1b2dc32331394557d92731521cd5
TERMUX_PKG_DEPENDS="termux-tools"
TERMUX_PKG_BUILD_IN_SRC=true

termux_step_make() {
	termux_setup_rust
	cargo build --release
}

termux_step_make_install() {
	install -Dm755 target/release/termux-settings "${TERMUX_PREFIX}/bin/termux-settings"
}
