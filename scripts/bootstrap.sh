#!/bin/bash
# =============================================================================
# Multiplatform Bootstrap Script
# =============================================================================
# Installs git + chezmoi on any platform, then applies dotfiles.
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.sh | bash
#
# Supported platforms:
#   - macOS (Homebrew)
#   - Fedora Standard (dnf)
#   - Fedora Atomic (rpm-ostree)
#   - Fedora Toolbox (container)
#   - Raspberry Pi / Debian / Ubuntu (apt)
#
# For Windows, use bootstrap.ps1 instead:
#   irm https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.ps1 | iex
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# =============================================================================
# Platform Detection
# =============================================================================
OS="$(uname -s)"
ARCH="$(uname -m)"
log_info "Detecting platform..."

case "$OS" in
    Darwin)
        PLATFORM="macos"
        EMOJI="🍎"
        log_success "Detected: $EMOJI macOS $(sw_vers -productVersion)"
        ;;
    Linux)
        # Check for Toolbox container
        if [[ -n "$TOOLBOX_PATH" ]] || [[ -f "/run/host/usr/lib/os-release" ]]; then
            PLATFORM="toolbox"
            EMOJI="📦"
            log_success "Detected: $EMOJI Fedora Toolbox"
        elif command -v rpm-ostree &>/dev/null; then
            PLATFORM="fedora-atomic"
            EMOJI="🐧"
            log_success "Detected: $EMOJI Fedora Atomic"
        elif command -v dnf &>/dev/null; then
            PLATFORM="fedora"
            EMOJI="🐧"
            log_success "Detected: $EMOJI Fedora Standard"
        elif command -v apt &>/dev/null; then
            # Check for Raspberry Pi
            if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]] || grep -qi "rpi\|raspberry" /proc/device-tree/model 2>/dev/null || [[ -f "/sys/firmware/devicetree/base/model" ]] && grep -qi "rpi" /sys/firmware/devicetree/base/model 2>/dev/null; then
                PLATFORM="rpi"
                EMOJI="🍓"
                log_success "Detected: $EMOJI Raspberry Pi"
            else
                PLATFORM="debian"
                EMOJI="🐍"
                log_success "Detected: $EMOJI Debian/Ubuntu"
            fi
        else
            log_error "Unsupported Linux distribution"
        fi
        ;;
    *)
        log_error "Unsupported OS: $OS. For Windows, use bootstrap.ps1"
        ;;
esac

# =============================================================================
# Install git + chezmoi
# =============================================================================

install_macos() {
    # Check if git is available
    if command -v git &>/dev/null; then
        log_warn "🍎 Git already installed"
    else
        # Xcode CLI tools
        if ! xcode-select -p &>/dev/null; then
            log_info "Installing Xcode Command Line Tools..."
            xcode-select --install
            # Wait for installation
            until xcode-select -p &>/dev/null; do
                sleep 5
            done
            log_success "Xcode CLI tools installed"
        else
            log_warn "Xcode CLI tools already installed"
        fi
    fi

    # Homebrew
    if command -v brew &>/dev/null; then
        log_warn "🍺 Homebrew already installed"
    else
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv)"
        log_success "🍺 Homebrew installed"
    fi

    # chezmoi via Homebrew
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    else
        log_info "Installing chezmoi via Homebrew..."
        brew install chezmoi
        log_success "chezmoi installed"
    fi
}

install_fedora() {
    log_info "Installing git and chezmoi via dnf..."

    # Install git
    if command -v git &>/dev/null; then
        log_warn "🐧 Git already installed"
    else
        sudo dnf install -y git
    fi

    # Install chezmoi - prefer dnf package, fallback to official script
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    elif dnf info chezmoi &>/dev/null; then
        log_info "Installing chezmoi via dnf..."
        sudo dnf install -y chezmoi
    else
        log_info "chezmoi not in dnf repos, installing via official script..."
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        export PATH="$HOME/.local/bin:$PATH"
    fi

    log_success "🐧 git and chezmoi installed"
}

install_fedora_atomic() {
    log_info "Installing git and chezmoi via rpm-ostree..."

    # Install git - prefer rpm-ostree package, fallback to official
    if command -v git &>/dev/null; then
        log_warn "🐧 Git already installed"
    elif rpm -q git &>/dev/null; then
        log_info "git already in system"
    else
        log_info "Installing git via rpm-ostree..."
        sudo rpm-ostree install --apply-live --idempotent git
    fi

    # Install chezmoi - prefer rpm-ostree, fallback to official script
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    elif rpm -q chezmoi &>/dev/null; then
        log_info "chezmoi already in system"
    else
        log_info "Installing chezmoi via official script..."
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        export PATH="$HOME/.local/bin:$PATH"
    fi

    log_success "🐧 git and chezmoi installed"
}

install_toolbox() {
    log_info "Installing git and chezmoi in Toolbox..."

    # Install git via dnf
    if command -v git &>/dev/null; then
        log_warn "🐧 Git already installed"
    else
        sudo dnf install -y git
    fi

    # Install chezmoi via official script
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    else
        log_info "Installing chezmoi via official script..."
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        export PATH="$HOME/.local/bin:$PATH"
    fi

    log_success "📦 git and chezmoi installed"
}

install_debian() {
    log_info "Installing git and chezmoi via apt..."

    # Check if git is available first
    if command -v git &>/dev/null; then
        log_warn "🐍 Git already installed"
    else
        sudo apt update
        sudo apt install -y git curl
    fi

    # Install chezmoi - prefer apt package, fallback to official script
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    elif apt-cache show chezmoi &>/dev/null 2>&1; then
        log_info "Installing chezmoi via apt..."
        sudo apt install -y chezmoi
    else
        log_info "chezmoi not in apt repos, installing via official script..."
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        export PATH="$HOME/.local/bin:$PATH"
    fi

    log_success "🐍 git and chezmoi installed"
}

install_rpi() {
    log_info "Installing git and chezmoi via apt..."

    # Check if git is available first
    if command -v git &>/dev/null; then
        log_warn "🍓 Git already installed"
    else
        sudo apt update
        sudo apt install -y git curl
    fi

    # Install chezmoi - prefer apt package, fallback to official script
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    elif apt-cache show chezmoi &>/dev/null 2>&1; then
        log_info "Installing chezmoi via apt..."
        sudo apt install -y chezmoi
    else
        log_info "chezmoi not in apt repos, installing via official script..."
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        export PATH="$HOME/.local/bin:$PATH"
    fi

    log_success "🍓 git and chezmoi installed"
}

case "$PLATFORM" in
    macos)          install_macos ;;
    fedora)         install_fedora ;;
    fedora-atomic)  install_fedora_atomic ;;
    toolbox)        install_toolbox ;;
    rpi)            install_rpi ;;
    debian)         install_debian ;;
esac

# =============================================================================
# Apply dotfiles
# =============================================================================
log_info "Initializing chezmoi and applying dotfiles..."

if [[ -d "$HOME/.local/share/chezmoi" ]]; then
    log_info "chezmoi already initialized, updating..."
    chezmoi update
else
    chezmoi init --apply jsoyer
fi

log_success "✨ Dotfiles applied!"

# =============================================================================
# Done
# =============================================================================
echo ""
echo -e "${GREEN}=============================================="
echo -e "  $EMOJI Bootstrap Complete!"
echo -e "==============================================${NC}"
echo ""
log_info "chezmoi has installed and configured everything."
log_info "Log out and log back in to apply all shell changes."
echo ""
