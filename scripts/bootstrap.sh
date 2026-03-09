#!/usr/bin/env bash
# =============================================================================
# Multiplatform Bootstrap Script
# =============================================================================
# Installs git, chezmoi, and gh (GitHub CLI) on any platform, then applies dotfiles.
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
            if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]] || \
               grep -qi "rpi\|raspberry" /proc/device-tree/model 2>/dev/null || \
               { [[ -f "/sys/firmware/devicetree/base/model" ]] && grep -qi "rpi\|raspberry" /sys/firmware/devicetree/base/model 2>/dev/null; }; then
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

install_linuxbrew() {
    if command -v brew &>/dev/null; then
        log_warn "🍺 Homebrew (Linuxbrew) already installed"
        return
    fi

    log_info "Installing Homebrew (Linuxbrew)..."

    # Prerequisites
    case "$PLATFORM" in
        fedora|toolbox)
            sudo dnf groupinstall -y "Development Tools"
            sudo dnf install -y procps-ng curl file gcc
            ;;
        rpi|debian)
            sudo apt install -y build-essential procps curl file gcc
            ;;
    esac

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Set up PATH for current session
    if [[ -d "/home/linuxbrew/.linuxbrew" ]]; then
        eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
    elif [[ -d "$HOME/.linuxbrew" ]]; then
        eval "$("$HOME/.linuxbrew/bin/brew" shellenv)"
    fi

    log_success "🍺 Homebrew (Linuxbrew) installed"
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

    # Install gh CLI via official dnf repo
    install_gh_dnf

    # Install 1Password CLI
    install_op_dnf

    # Install uv (for uvx / MCP servers using Python)
    install_uv

    # Install Linuxbrew
    install_linuxbrew

    log_success "🐧 git, chezmoi, gh, op, uv, and Homebrew installed"
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
        if ! sudo rpm-ostree install --apply-live --idempotent chezmoi 2>/dev/null; then
            log_warn "chezmoi already in base layer (will be available after reboot)"
            # Fallback: install via official script to ~/.local/bin
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

    # Install gh CLI via official dnf repo
    install_gh_dnf

    # Install 1Password CLI
    install_op_dnf

    # Install uv (for uvx / MCP servers using Python)
    install_uv

    # Install Linuxbrew
    install_linuxbrew

    log_success "📦 git, chezmoi, gh, op, uv, and Homebrew installed"
}

install_op_apt() {
    if command -v op &>/dev/null; then
        log_warn "op (1Password CLI) already installed"
        return
    fi

    log_info "Installing op (1Password CLI) via official apt repo..."

    local keyring_dir="/usr/share/keyrings"
    local sources_dir="/etc/apt/sources.list.d"
    local tmp_key
    tmp_key="$(mktemp)"

    sudo mkdir -p -m 755 "$keyring_dir" "$sources_dir"
    curl -sS https://downloads.1password.com/linux/keys/1password.asc -o "$tmp_key"
    sudo gpg --dearmor < "$tmp_key" | sudo tee "$keyring_dir/1password-archive-keyring.gpg" > /dev/null
    rm -f "$tmp_key"

    echo "deb [arch=$(dpkg --print-architecture) signed-by=${keyring_dir}/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/$(dpkg --print-architecture) stable main" \
        | sudo tee "$sources_dir/1password.list" > /dev/null

    sudo apt update
    sudo apt install -y 1password-cli

    log_success "op installed ($(op --version))"
}

install_op_dnf() {
    if command -v op &>/dev/null; then
        log_warn "op (1Password CLI) already installed"
        return
    fi

    log_info "Installing op (1Password CLI) via official rpm repo..."
    sudo rpm --import https://downloads.1password.com/linux/keys/1password.asc
    sudo sh -c 'echo -e "[1password]\nname=1Password Stable Channel\nbaseurl=https://downloads.1password.com/linux/rpm/stable/\$basearch\nenabled=1\ngpgcheck=1\nrepo_gpgcheck=1\ngpgkey=https://downloads.1password.com/linux/keys/1password.asc" > /etc/yum.repos.d/1password.repo'
    sudo dnf install -y 1password-cli

    log_success "op installed ($(op --version))"
}

install_uv() {
    if command -v uv &>/dev/null; then
        log_warn "uv already installed"
        return
    fi

    log_info "Installing uv (Python package runner / uvx)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"

    log_success "uv installed ($(uv --version))"
}

install_gh_dnf() {
    if command -v gh &>/dev/null; then
        log_warn "gh already installed"
        return
    fi

    log_info "Installing gh (GitHub CLI) via official dnf repo..."
    sudo dnf install -y dnf5-plugins
    sudo dnf config-manager addrepo --from-repofile=https://cli.github.com/packages/rpm/gh-cli.repo
    sudo dnf install -y gh --repo gh-cli

    log_success "gh installed"
}

install_gh_apt() {
    if command -v gh &>/dev/null; then
        log_warn "gh already installed"
        return
    fi

    log_info "Installing gh (GitHub CLI) via official apt repo..."

    # Ensure wget is available
    if ! type -p wget &>/dev/null; then
        sudo apt update
        sudo apt install -y wget
    fi

    local keyring_dir="/etc/apt/keyrings"
    local sources_dir="/etc/apt/sources.list.d"
    local tmp_key
    tmp_key="$(mktemp)"

    sudo mkdir -p -m 755 "$keyring_dir" "$sources_dir"
    wget -nv -O "$tmp_key" https://cli.github.com/packages/githubcli-archive-keyring.gpg
    sudo install -m 644 "$tmp_key" "$keyring_dir/githubcli-archive-keyring.gpg"
    rm -f "$tmp_key"

    echo "deb [arch=$(dpkg --print-architecture) signed-by=${keyring_dir}/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | sudo tee "$sources_dir/github-cli.list" > /dev/null

    sudo apt update
    sudo apt install -y gh

    log_success "gh installed"
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

    # Install gh CLI via official apt repo
    install_gh_apt

    # Install 1Password CLI
    install_op_apt

    # Install uv (for uvx / MCP servers using Python)
    install_uv

    # Install Linuxbrew
    install_linuxbrew

    log_success "$EMOJI git, chezmoi, gh, op, uv, and Homebrew installed"
}

install_debian() { install_apt; }
install_rpi()    { install_apt; }

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
    
    # Verify packages are in base layer (rpm-ostree.conf), add if missing
    log_info "Verifying base layer packages..."
    local -a BASE_PACKAGES=( git openssh-server curl wget chezmoi )
    for pkg in "${BASE_PACKAGES[@]}"; do
        if ! grep -qx "${pkg}" /etc/rpm-ostree.conf 2>/dev/null; then
            log_info "Adding $pkg to base layer..."
            echo "$pkg" | sudo tee -a /etc/rpm-ostree.conf > /dev/null
        fi
    done

    # Install packages that aren't installed yet (will apply on next boot)
    # Skip wget — provided by wget2 on Fedora
    local -a BASE_PACKAGES_CLEAN=( git openssh-server curl chezmoi )
    for pkg in "${BASE_PACKAGES_CLEAN[@]}"; do
        if ! rpm -q "$pkg" &>/dev/null; then
            log_info "Installing $pkg to base layer..."
            sudo rpm-ostree install "$pkg" 2>/dev/null || log_warn "Could not install $pkg"
        fi
    done
    
    log_success "Fedora Atomic base layer configured"
    log_warn "⚠️  Reboot required for base layer packages to be available!"
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
    
    # Check if sshd is installed (various methods, sshd might not be in PATH)
    if [[ -f "/usr/sbin/sshd" ]] || [[ -f "/usr/bin/sshd" ]] || dpkg -l 2>/dev/null | grep -q "openssh-server" || rpm -q openssh-server &>/dev/null 2>&1; then
        log_info "🔐 SSH server already installed"
        
        # Check if service is enabled/running
        if systemctl is-active --quiet sshd 2>/dev/null || systemctl is-active --quiet ssh 2>/dev/null; then
            log_success "🔐 SSH service is running"
        elif systemctl is-enabled --quiet sshd 2>/dev/null || systemctl is-enabled --quiet ssh 2>/dev/null; then
            log_success "🔐 SSH service is enabled (not running, starting now...)"
            sudo systemctl start sshd 2>/dev/null || sudo systemctl start ssh 2>/dev/null
        else
            log_warn "🔐 SSH is installed but not enabled"
            read -p "Enable and start SSH service now? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo systemctl enable --now sshd 2>/dev/null || sudo systemctl enable --now ssh 2>/dev/null
                log_success "🔐 SSH service enabled and started"
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
                    log_success "🔐 SSH server installed and enabled"
                    ;;
                fedora-atomic)
                    # Add to base layer config for persistence
                    if ! grep -q "openssh-server" /etc/rpm-ostree.conf 2>/dev/null; then
                        log_info "Adding openssh-server to base layer..."
                        echo "openssh-server" | sudo tee -a /etc/rpm-ostree.conf > /dev/null
                    fi
                    sudo rpm-ostree install openssh-server
                    log_warn "SSH will be active after reboot. Run 'sudo systemctl enable --now sshd' after reboot."
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
            if [[ "$PLATFORM" == "fedora-atomic" ]]; then
                log_warn "🔐 SSH will be active after reboot"
            else
                log_success "🔐 SSH server installed and enabled"
            fi
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
    CHEZMOI_DIR="$HOME/.local/share/chezmoi"
    cd "$CHEZMOI_DIR"
    
    # Configure git remote if needed
    if ! git remote get-url origin &>/dev/null 2>&1; then
        git remote add origin https://github.com/jsoyer/dotfiles.git
    fi
    
    # Fetch and merge latest changes
    log_info "Fetching latest dotfiles..."
    git fetch origin

    # Merge or reset to remote HEAD
    current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    if git rev-parse --verify "origin/${current_branch}" &>/dev/null 2>&1; then
        git branch --set-upstream-to="origin/${current_branch}" "${current_branch}" 2>/dev/null || true
        git merge --ff-only "origin/${current_branch}" 2>/dev/null || \
            git reset --hard "origin/${current_branch}"
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
