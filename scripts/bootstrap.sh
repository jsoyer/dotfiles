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
        # Check for Fedora Atomic (rpm-ostree) - must be checked BEFORE Toolbox
        if command -v rpm-ostree &>/dev/null || [[ -f "/run/ostree" ]]; then
            PLATFORM="fedora-atomic"
            EMOJI="🐧"
            log_success "Detected: $EMOJI Fedora Atomic"
        # Check for Toolbox container
        elif [[ -n "$TOOLBOX_PATH" ]] || [[ -f "/run/host/usr/lib/os-release" ]]; then
            PLATFORM="toolbox"
            EMOJI="📦"
            log_success "Detected: $EMOJI Fedora Toolbox"
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
        fedora)
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
        rpi|debian)
            if command -v apt &>/dev/null; then
                log_info "Checking for Debian/RPi updates..."
                sudo apt update -qq 2>/dev/null
                UPDATES=$(sudo apt-get -s dist-upgrade 2>&1 || true)
                if echo "$UPDATES" | grep -q "0 upgraded, 0 newly installed, 0 to remove"; then
                    log_success "🐍 Debian/RPi is up to date"
                else
                    log_warn "🐍 Debian/RPi has updates available!"
                    echo "$UPDATES" | head -20
                    read -p "Update now? (y/N) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        log_info "Updating Debian/RPi..."
                        sudo apt dist-upgrade -y
                        log_success "Debian/RPi updated. Reboot recommended."
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
# Ensure persistent packages survive Fedora Atomic upgrades
# =============================================================================

setup_fedora_atomic_base_layer() {
    if [[ "$PLATFORM" != "fedora-atomic" ]]; then
        return
    fi
    
    log_info "Setting up Fedora Atomic base layer..."
    
    # Create /etc/rpm-ostree.conf if not exists
    if [[ ! -f /etc/rpm-ostree.conf ]]; then
        # Check if we have the config file in dotfiles
        if [[ -f "$HOME/.config/fedora/rpm-ostree.conf" ]]; then
            log_info "Installing base layer config from dotfiles..."
            sudo cp "$HOME/.config/fedora/rpm-ostree.conf" /etc/rpm-ostree.conf
        else
            log_info "Creating /etc/rpm-ostree.conf with default packages..."
            sudo tee /etc/rpm-ostree.conf > /dev/null << 'EOF'
[Packages]
git
openssh-server
curl
wget
chezmoi
EOF
        fi
        log_success "Base layer config created at /etc/rpm-ostree.conf"
    else
        log_info "Base layer config already exists at /etc/rpm-ostree.conf"
    fi
    
    # Verify packages are installed (rpm-ostree will apply them on next boot)
    log_info "Verifying base layer packages..."
    BASE_PACKAGES="git openssh-server curl wget chezmoi"
    for pkg in $BASE_PACKAGES; do
        if ! rpm -q "$pkg" &>/dev/null; then
            log_warn "Package $pkg not installed, adding to base layer..."
            sudo rpm-ostree install --apply-live "$pkg" 2>/dev/null || true
        fi
    done
    
    log_success "Fedora Atomic base layer configured"
}

setup_fedora_atomic_base_layer

# =============================================================================
# Check and install SSH if needed (Linux only)
# =============================================================================

check_ssh() {
    if [[ "$OS" != "Linux" ]]; then
        return
    fi
    
    log_info "Checking SSH server..."
    
    # Check if sshd is installed (various possible packages)
    if command -v sshd &>/dev/null || [[ -f "/usr/sbin/sshd" ]] || dpkg -l | grep -q "openssh-server" || rpm -q openssh-server &>/dev/null 2>&1; then
        log_info "🔐 SSH server already installed"
        
        # Check if service is running
        if systemctl is-active --quiet sshd 2>/dev/null || systemctl is-active --quiet ssh 2>/dev/null; then
            log_success "🔐 SSH service is running"
        else
            log_warn "🔐 SSH is installed but not running"
            read -p "Start SSH service now? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo systemctl enable --now sshd 2>/dev/null || sudo systemctl enable --now ssh 2>/dev/null
                log_success "🔐 SSH service started"
            fi
        fi
    else
        log_warn "🔐 SSH server is not installed"
        read -p "Install and enable SSH server? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            case "$PLATFORM" in
                fedora)
                    sudo dnf install -y openssh-server
                    sudo systemctl enable --now sshd
                    ;;
                fedora-atomic)
                    sudo rpm-ostree install --apply-live openssh-server
                    sudo systemctl enable --now sshd
                    ;;
                rpi|debian)
                    sudo apt update
                    sudo apt install -y openssh-server
                    sudo systemctl enable --now ssh
                    ;;
                toolbox)
                    sudo dnf install -y openssh-server
                    sudo systemctl enable --now sshd
                    ;;
            esac
            log_success "🔐 SSH server installed and started"
        fi
    fi
}

check_ssh

# =============================================================================
# Apply dotfiles
# =============================================================================
log_info "Initializing chezmoi and applying dotfiles..."

if [[ -d "$HOME/.local/share/chezmoi" ]]; then
    log_info "chezmoi already initialized, updating..."
    # Handle case where branch has no tracking info
    cd "$HOME/.local/share/chezmoi"
    if ! git config --get "branch.main.remote" &>/dev/null && ! git config --get "branch.master.remote" &>/dev/null; then
        log_warn "No tracking info, setting up remote..."
        git branch --set-upstream-to=origin/main main 2>/dev/null || git branch --set-upstream-to=origin/master master 2>/dev/null || true
    fi
    chezmoi update || log_warn "chezmoi update failed, trying apply..."
    chezmoi apply || true
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
