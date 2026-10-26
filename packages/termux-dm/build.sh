TERMUX_PKG_HOMEPAGE=https://github.com/GeneralKaos666/termux-display-manager-repo
TERMUX_PKG_DESCRIPTION="Termux display manager"
TERMUX_PKG_LICENSE="GPL-3.0"
TERMUX_PKG_MAINTAINER="Ronald Sloan (for termux) <xkiller1177@gmail.com>"
TERMUX_PKG_VERSION="6-morano"
TERMUX_PKG_SRCURL="https://github.com/GeneralKaos666/termux-display-manager-repo/archive/refs/heads/master.tar.gz"
TERMUX_PKG_SHA256=SKIP_CHECKSUM
TERMUX_PKG_DEPENDS="python, python-tkinter, python-pillow, tigervnc, tigervnc-viewer"

# `tdm` and `tdmpasswd` are vendored from the 6-morano package (the upstream
# repo ships prebuilt .debs rather than a source tree).
termux_step_make_install() {
	install -Dm755 "${TERMUX_PKG_BUILDER_DIR}/tdm" "${TERMUX_PREFIX}/bin/tdm"
	install -Dm755 "${TERMUX_PKG_BUILDER_DIR}/tdmpasswd" "${TERMUX_PREFIX}/bin/tdmpasswd"
}
