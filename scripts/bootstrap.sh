#!/usr/bin/env bash
# =============================================================================
# Multiplatform Bootstrap Script
# =============================================================================
# Installs git and chezmoi, then lets package layers select the remaining tools.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.sh | bash
#
# Supported platforms:
#   - macOS (Homebrew)
#   - Arch Linux / OmArchy (pacman + yay)
#   - Fedora Standard (dnf)
#   - Fedora Atomic (rpm-ostree)
#   - Fedora Toolbox (container)
#   - Raspberry Pi / Debian / Ubuntu (apt)
#
# For Windows, use bootstrap.ps1 instead:
#   irm https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/bootstrap.ps1 | iex
#
# =============================================================================
# SECURITY MODEL
# =============================================================================
# This script downloads and executes code from external sources:
#
# Trusted sources (all HTTPS, maintained by reputable orgs):
#   - get.chezmoi.io          — chezmoi official installer (Go binary)
#   - Homebrew/install         — Homebrew official installer (GitHub)
#   - astral.sh/uv            — uv Python package manager (Astral)
#   - downloads.1password.com — 1Password CLI (AgileBits, GPG-signed repo)
#   - cli.github.com          — GitHub CLI (GitHub, GPG-signed repo)
#
# All curl calls use -fsSL (fail on HTTP errors, silent, follow redirects, HTTPS).
# GPG keys are verified for apt/dnf repos (1Password, GitHub CLI).
# No checksums on installer scripts (standard industry practice for these tools).
#
# To audit: grep -n 'curl' scripts/bootstrap.sh
# =============================================================================

set -euo pipefail

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
        # Read /etc/os-release as the primary source of truth
        _DISTRO_ID=""
        if [[ -f /etc/os-release ]]; then
            _DISTRO_ID="$(. /etc/os-release && echo "${ID:-}")"
        fi

        # Helper: true if running on Raspberry Pi hardware
        _is_rpi_hw() {
            [[ -f /proc/device-tree/model ]] && grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null
        }

        # Check for Fedora Atomic (rpm-ostree) - must be checked BEFORE Toolbox
        if command -v rpm-ostree &>/dev/null || [[ -f "/run/ostree" ]]; then
            PLATFORM="fedora-atomic"
            EMOJI="🐧"
            log_success "Detected: $EMOJI Fedora Atomic"
        # Check for Toolbox container
        elif [[ -n "${TOOLBOX_PATH:-}" ]] || [[ -f "/run/host/usr/lib/os-release" ]]; then
            PLATFORM="toolbox"
            EMOJI="📦"
            log_success "Detected: $EMOJI Fedora Toolbox"
        elif command -v dnf &>/dev/null; then
            _BHOST="${HOSTNAME%%.*}"
            if [[ "${_BHOST}" == fedora-server* ]]; then
                PLATFORM="fedora-server"
                EMOJI="🐧"
                log_success "Detected: $EMOJI Fedora Server"
            else
                PLATFORM="fedora-desktop"
                EMOJI="🐧"
                log_success "Detected: $EMOJI Fedora Desktop"
            fi
            unset _BHOST
        elif [[ "${_DISTRO_ID}" == "arch" ]]; then
            _BHOST="${HOSTNAME%%.*}"
            if [[ "${_BHOST}" == arch-server* ]]; then
                PLATFORM="arch-server"
                EMOJI="🐧"
                log_success "Detected: $EMOJI Arch Linux Server"
            else
                PLATFORM="arch-desktop"
                EMOJI="🐧"
                log_success "Detected: $EMOJI Arch Linux Desktop"
            fi
            unset _BHOST
        elif command -v apt &>/dev/null; then
            # Use hardware detection for RPi (works regardless of OS: raspbian or ubuntu)
            if _is_rpi_hw || [[ "${_DISTRO_ID}" == "raspbian" ]]; then
                PLATFORM="rpi"
                EMOJI="🍓"
                log_success "Detected: $EMOJI Raspberry Pi (${_DISTRO_ID:-unknown})"
            elif [[ "${_DISTRO_ID}" == "ubuntu" ]]; then
                # Distinguish desktop vs server by hostname prefix
                _BHOST="${HOSTNAME%%.*}"
                if [[ "${_BHOST}" == ubuntu-server* ]]; then
                    PLATFORM="ubuntu-server"
                    EMOJI="🐧"
                    log_success "Detected: $EMOJI Ubuntu Server"
                else
                    PLATFORM="ubuntu-desktop"
                    EMOJI="🐧"
                    log_success "Detected: $EMOJI Ubuntu Desktop"
                fi
                unset _BHOST
            else
                PLATFORM="debian"
                EMOJI="🐍"
                log_success "Detected: $EMOJI Debian"
            fi
        else
            log_error "Unsupported Linux distribution (ID=${_DISTRO_ID:-unknown})"
        fi
        unset _DISTRO_ID
        ;;
    *)
        log_error "Unsupported OS: $OS. For Windows, use bootstrap.ps1"
        ;;
esac

# =============================================================================
# Check if OS is up to date
# =============================================================================

check_os_updates() {
    log_info "Checking for OS updates..."
    
    case "$PLATFORM" in
        macos)
            if command -v softwareupdate &>/dev/null; then
                UPDATES=$(softwareupdate -l 2>&1 || true)
                if echo "$UPDATES" | grep -q "No new software available"; then
                    log_success "🍎 macOS is up to date"
                else
                    log_warn "🍎 macOS has updates available!"
                    echo "$UPDATES"
                    read -p "Update now? (y/N) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        log_info "Updating macOS..."
                        sudo softwareupdate -i -a
                        log_success "macOS updated. Reboot required for changes to take effect."
                        read -p "Reboot now? (y/N) " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            sudo reboot
                        fi
                    else
                        log_warn "Skipping update. You can run 'softwareupdate -i -a' later."
                    fi
                fi
            fi
            ;;
        fedora-desktop|fedora-server)
            if command -v dnf &>/dev/null; then
                log_info "Checking for Fedora updates..."
                UPDATES=$(sudo dnf check-update 2>&1 || true)
                if echo "$UPDATES" | grep -qE "^(Fedora|.*No packages|Last metadata)"; then
                    # Check if there are actually updates
                    if echo "$UPDATES" | grep -qE "^[a-z].*\.[a-z].*"; then
                        log_warn "🐧 Fedora has updates available!"
                        echo "$UPDATES"
                        read -p "Update now? (y/N) " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            log_info "Updating Fedora..."
                            sudo dnf upgrade -y
                            log_success "Fedora updated. Reboot recommended."
                            read -p "Reboot now? (y/N) " -n 1 -r
                            echo
                            if [[ $REPLY =~ ^[Yy]$ ]]; then
                                sudo reboot
                            fi
                        else
                            log_warn "Skipping update. You can run 'sudo dnf upgrade' later."
                        fi
                    else
                        log_success "🐧 Fedora is up to date"
                    fi
                fi
            fi
            ;;
        fedora-atomic)
            log_info "Checking for Fedora Atomic updates..."
            CHECK_OUTPUT=$(sudo rpm-ostree upgrade --check 2>&1 || true)
            if echo "$CHECK_OUTPUT" | grep -q "No upgrade available"; then
                log_success "🐧 Fedora Atomic is up to date"
            else
                log_warn "🐧 Fedora Atomic has updates available!"
                echo "$CHECK_OUTPUT"
                read -p "Update now? (y/N) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    log_info "Updating Fedora Atomic..."
                    sudo rpm-ostree upgrade
                    log_success "Fedora Atomic updated. Reboot required for changes to take effect."
                    read -p "Reboot now? (y/N) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        sudo reboot
                    fi
                else
                    log_warn "Skipping update. You can run 'sudo rpm-ostree upgrade' later."
                fi
            fi
            ;;
        rpi|debian|ubuntu-server|ubuntu-desktop)
            if command -v apt &>/dev/null; then
                log_info "Checking for apt updates..."
                sudo apt update -qq 2>/dev/null
                UPDATES=$(sudo apt-get -s dist-upgrade 2>&1 || true)
                if echo "$UPDATES" | grep -q "0 upgraded, 0 newly installed, 0 to remove"; then
                    log_success "System is up to date"
                else
                    log_warn "Updates available!"
                    echo "$UPDATES" | head -20
                    read -p "Update now? (y/N) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        log_info "Updating system..."
                        sudo apt dist-upgrade -y
                        log_success "System updated. Reboot recommended."
                        read -p "Reboot now? (y/N) " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            sudo reboot
                        fi
                    else
                        log_warn "Skipping update. You can run 'sudo apt update && sudo apt dist-upgrade' later."
                    fi
                fi
            fi
            ;;
        arch-desktop|arch-server)
            if command -v pacman &>/dev/null; then
                log_info "Checking for Arch Linux updates..."
                UPDATES=$(pacman -Qu 2>/dev/null || true)
                if [[ -z "$UPDATES" ]]; then
                    log_success "Arch Linux is up to date"
                else
                    log_warn "Arch Linux has updates available!"
                    echo "$UPDATES" | head -20
                    read -p "Update now? (y/N) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        log_info "Updating Arch Linux..."
                        sudo pacman -Syu --noconfirm
                        log_success "Arch Linux updated."
                    else
                        log_warn "Skipping update. You can run 'sudo pacman -Syu' later."
                    fi
                fi
            fi
            ;;
        toolbox)
            if command -v dnf &>/dev/null; then
                log_info "Checking for Toolbox updates..."
                UPDATES=$(sudo dnf check-update 2>&1 || true)
                if echo "$UPDATES" | grep -qE "^(Fedora|.*No packages|Last metadata)"; then
                    if echo "$UPDATES" | grep -qE "^[a-z].*\.[a-z].*"; then
                        log_warn "📦 Toolbox has updates available!"
                        echo "$UPDATES"
                        read -p "Update now? (y/N) " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            log_info "Updating Toolbox..."
                            sudo dnf upgrade -y
                            log_success "📦 Toolbox updated."
                        else
                            log_warn "Skipping update. You can run 'sudo dnf upgrade' later."
                        fi
                    else
                        log_success "📦 Toolbox is up to date"
                    fi
                fi
            fi
            ;;
    esac
}

# Check for updates before installing
check_os_updates

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
        for _brew in /opt/homebrew/bin/brew /usr/local/bin/brew; do
            if [ -x "$_brew" ]; then
                eval "$("$_brew" shellenv)"
                break
            fi
        done
        unset _brew
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

    # Add ~/.local/bin to PATH for potential official installs
    export PATH="$HOME/.local/bin:$PATH"

    # Install git - use --apply-live to apply immediately
    if command -v git &>/dev/null; then
        log_warn "🐧 Git already installed"
    elif rpm -q git &>/dev/null; then
        log_info "git already in system"
    else
        log_info "Installing git via rpm-ostree..."
        sudo rpm-ostree install --apply-live --idempotent git
    fi

    # Install chezmoi via rpm-ostree OR fallback to official script
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    else
        log_info "Installing chezmoi via rpm-ostree..."
        if sudo rpm-ostree install --apply-live chezmoi 2>/dev/null; then
            log_success "chezmoi installed via rpm-ostree"
        else
            log_warn "rpm-ostree install failed (package may need a reboot to apply); using fallback"
            log_info "Installing chezmoi via official script to ~/.local/bin..."
            sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        fi
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

install_apt() {
    log_info "Installing git, chezmoi, and gh via apt..."

    # Check if git is available first
    if command -v git &>/dev/null; then
        log_warn "$EMOJI Git already installed"
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

    log_success "$EMOJI git and chezmoi installed"
}

install_debian()         { install_apt; }
install_rpi()            { install_apt; }
install_ubuntu_server()  { install_apt; }
install_ubuntu_desktop() { install_apt; }

install_arch() {
    log_info "Installing Arch Linux prerequisites..."

    # git
    if command -v git &>/dev/null; then
        log_warn "git already installed"
    else
        sudo pacman -S --noconfirm git
    fi

    # chezmoi
    if command -v chezmoi &>/dev/null; then
        log_warn "chezmoi already installed"
    else
        log_info "Installing chezmoi..."
        sudo pacman -S --noconfirm chezmoi || \
            sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        log_success "chezmoi installed"
    fi

    log_success "Arch Linux prerequisites installed"
}

case "$PLATFORM" in
    macos)           install_macos ;;
    fedora-desktop|fedora-server) install_fedora ;;
    fedora-atomic)   install_fedora_atomic ;;
    toolbox)         install_toolbox ;;
    arch-desktop|arch-server) install_arch ;;
    rpi)             install_rpi ;;
    debian)          install_debian ;;
    ubuntu-server)   install_ubuntu_server ;;
    ubuntu-desktop)  install_ubuntu_desktop ;;
esac

# =============================================================================
# Ensure persistent packages survive Fedora Atomic upgrades
# =============================================================================

# Package layers own Atomic extras; bootstrap only needs git and chezmoi.

# =============================================================================
# Check and install SSH if needed (Linux only)
# =============================================================================

# SSH installation/activation is an explicit server or machine choice.

# =============================================================================
# Apply dotfiles
# =============================================================================
log_info "Initializing chezmoi and applying dotfiles..."

if [[ -d "$HOME/.local/share/chezmoi" ]]; then
    log_info "chezmoi already initialized, updating..."
    CHEZMOI_DIR="$HOME/.local/share/chezmoi"
    cd "$CHEZMOI_DIR"
    
    # Configure git remote if needed
    if ! git remote get-url origin &>/dev/null 2>&1; then
        git remote add origin https://github.com/jsoyer/dotfiles.git
    fi
    
    # Fetch and merge latest changes
    log_info "Fetching latest dotfiles..."
    git fetch origin

    # Keep local changes and stop on divergence instead of discarding them
    current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    if git rev-parse --verify "origin/${current_branch}" &>/dev/null 2>&1; then
        git branch --set-upstream-to="origin/${current_branch}" "${current_branch}" 2>/dev/null || true
        git merge --ff-only "origin/${current_branch}"
    fi

    # Apply dotfiles (we already have latest source)
    export PATH="$HOME/.local/bin:$PATH"
    chezmoi apply
else
    log_info "Initializing chezmoi from GitHub..."
    chezmoi init https://github.com/jsoyer/dotfiles.git --apply
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
