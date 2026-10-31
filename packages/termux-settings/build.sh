TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/termux-settings
TERMUX_PKG_DESCRIPTION="Keyboard-driven TUI to change Termux colors, app theme, and fonts"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="1.3.1"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/termux-settings/archive/refs/tags/v1.3.1.tar.gz"
TERMUX_PKG_SHA256=10cbd17058b6a963e90992dbf337505e15e1cec35445e83293dc368bd92889a7
TERMUX_PKG_DEPENDS="termux-tools"
TERMUX_PKG_BUILD_IN_SRC=true

termux_step_make() {
	termux_setup_rust
	cargo build --release --target "${CARGO_TARGET_NAME}"
}

termux_step_make_install() {
	install -Dm755 "target/${CARGO_TARGET_NAME}/release/termux-settings" "${TERMUX_PREFIX}/bin/termux-settings"
}
