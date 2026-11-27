TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/termux-sync-rust
TERMUX_PKG_DESCRIPTION="Back up and restore a Termux environment across devices"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="2.0.0"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/termux-sync-rust/archive/refs/tags/v2.0.0.tar.gz"
TERMUX_PKG_SHA256=8cba98b20b960a555c3ebf28b5e333b660c632be504aa2125f1ec5e0b50e8151
TERMUX_PKG_DEPENDS="dpkg"
TERMUX_PKG_BUILD_IN_SRC=true

termux_step_make() {
	termux_setup_rust
	cargo build --release --locked --target "${CARGO_TARGET_NAME}"
}

termux_step_make_install() {
	install -Dm755 "target/${CARGO_TARGET_NAME}/release/termux-sync" \
		"${TERMUX_PREFIX}/bin/termux-sync"
	install -Dm755 "target/${CARGO_TARGET_NAME}/release/termux-sync-tui" \
		"${TERMUX_PREFIX}/bin/termux-sync-tui"
	install -Dm644 README.md \
		"${TERMUX_PREFIX}/share/doc/termux-sync/README.md"
	install -Dm644 LICENSE \
		"${TERMUX_PREFIX}/share/doc/termux-sync/LICENSE"
}
