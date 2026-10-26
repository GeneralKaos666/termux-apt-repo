TERMUX_PKG_HOMEPAGE=https://github.com/Superchavo/termux-display-manager-repo
TERMUX_PKG_DESCRIPTION="Termux display manager"
TERMUX_PKG_LICENSE="GPL-3.0"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="6-morano"
TERMUX_PKG_SRCURL="https://github.com/Superchavo/termux-display-manager-repo/archive/refs/heads/main.tar.gz"
TERMUX_PKG_SHA256=SKIP_CHECKSUM
TERMUX_PKG_DEPENDS="python, python-tkinter, python-pillow, tigervnc, tigervnc-viewer"

# TODO: confirm the exact source paths for `tdm` and `tdmpasswd` in the
# upstream tree. The 6-morano .deb installs `bin/tdm` and `bin/tdmpasswd`.
termux_step_make_install() {
	install -Dm755 bin/tdm "${TERMUX_PREFIX}/bin/tdm"
	install -Dm755 bin/tdmpasswd "${TERMUX_PREFIX}/bin/tdmpasswd"
}
