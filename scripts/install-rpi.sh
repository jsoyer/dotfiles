#!/bin/bash
# =============================================================================
# Raspberry Pi / Linux Dotfiles Installation Script
# =============================================================================
# 
# This script installs all necessary tools and applies dotfiles configuration
# for Raspberry Pi and Linux systems.
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/install-rpi.sh | bash
#
# What this script does:
#   1. Configures system locale (en_US.UTF-8)
#   2. Installs all packages via apt
#   3. Installs Oh-My-Zsh with plugins
#   4. Installs Tmux Plugin Manager (TPM)
#   5. Installs Nerd Fonts for icons
#   6. Applies dotfiles via chezmoi
#
# Platform differences:
#   - macOS: Catppuccin Mocha theme, tmux bar at top, Ctrl+A prefix
#   - RPi/Linux: Snazzy theme, tmux bar at bottom, Ctrl+B prefix
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# Platform Detection
# =============================================================================
log_info "Detecting platform..."

if [[ "$(uname -s)" == "Darwin" ]]; then
    log_error "This script is intended for Raspberry Pi / Linux only"
    log_info "For macOS, use: sh -c \"\$(curl -fsLS get.chezmoi.io)\" -- init --apply jsoyer"
    exit 1
fi

if [[ -f /proc/device-tree/model ]]; then
    RPI_MODEL=$(cat /proc/device-tree/model | tr -d '\0')
    log_success "Detected: $RPI_MODEL"
else
    log_info "Running on Linux (non-RPi)"
fi

# =============================================================================
# Locale Configuration
# =============================================================================
log_info "Configuring system locale..."

# Check if en_US.UTF-8 locale is available
if ! locale -a 2>/dev/null | grep -q "en_US.utf8"; then
    log_info "Generating en_US.UTF-8 locale..."
    sudo locale-gen en_US.UTF-8
    sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
    log_success "Locale configured"
else
    log_warn "Locale en_US.UTF-8 already available"
fi

# Set locale for current session
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# =============================================================================
# All Packages Installation (via apt)
# =============================================================================
log_info "Installing all packages via apt..."

sudo apt update && sudo apt install -y \
    zsh \
    git \
    curl \
    wget \
    tmux \
    fzf \
    neovim \
    fd-find \
    ripgrep \
    jq \
    unzip \
    bat \
    fontconfig \
    starship \
    zoxide \
    eza \
    vivid \
    locales

# Create symlinks for renamed packages on Debian/Ubuntu
sudo ln -sf /usr/bin/batcat /usr/local/bin/bat 2>/dev/null || true
sudo ln -sf /usr/bin/fdfind /usr/local/bin/fd 2>/dev/null || true

log_success "All packages installed via apt"

# =============================================================================
# Oh-My-Zsh Installation
# =============================================================================
log_info "Installing Oh-My-Zsh..."

if [[ ! -d "$HOME/.oh-my-zsh" ]]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
    log_success "Oh-My-Zsh installed"
else
    log_warn "Oh-My-Zsh already installed, skipping"
fi

# =============================================================================
# Zsh Plugins Installation
# =============================================================================
log_info "Installing Zsh plugins..."

ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"

if [[ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]]; then
    git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
    log_success "zsh-autosuggestions installed"
else
    log_warn "zsh-autosuggestions already installed, skipping"
fi

if [[ ! -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]]; then
    git clone https://github.com/zsh-users/zsh-syntax-highlighting "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
    log_success "zsh-syntax-highlighting installed"
else
    log_warn "zsh-syntax-highlighting already installed, skipping"
fi

# =============================================================================
# Tmux Plugin Manager Installation
# =============================================================================
log_info "Installing Tmux Plugin Manager (TPM)..."

if [[ ! -d "$HOME/.tmux/plugins/tpm" ]]; then
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
    log_success "TPM installed"
else
    log_warn "TPM already installed, skipping"
fi

# =============================================================================
# Nerd Font Installation (for icons in terminal)
# =============================================================================
log_info "Installing JetBrains Mono Nerd Font..."

FONT_DIR="$HOME/.local/share/fonts"
if [[ ! -f "$FONT_DIR/JetBrainsMonoNerdFont-Regular.ttf" ]]; then
    mkdir -p "$FONT_DIR"
    FONT_VERSION=$(curl -s https://api.github.com/repos/ryanoasis/nerd-fonts/releases/latest | jq -r '.tag_name')
    wget -qO /tmp/JetBrainsMono.zip "https://github.com/ryanoasis/nerd-fonts/releases/download/${FONT_VERSION}/JetBrainsMono.zip"
    unzip -qo /tmp/JetBrainsMono.zip -d "$FONT_DIR"
    rm /tmp/JetBrainsMono.zip
    fc-cache -fv > /dev/null 2>&1
    log_success "JetBrains Mono Nerd Font installed"
else
    log_warn "Nerd Font already installed, skipping"
fi

# =============================================================================
# Chezmoi Installation & Dotfiles Application
# =============================================================================
log_info "Installing Chezmoi and applying dotfiles..."

if ! command -v chezmoi &> /dev/null; then
    sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply jsoyer
    log_success "Chezmoi installed and dotfiles applied"
else
    log_info "Chezmoi already installed, updating dotfiles..."
    chezmoi update
    log_success "Dotfiles updated"
fi

# =============================================================================
# Change Default Shell to Zsh
# =============================================================================
log_info "Setting Zsh as default shell..."

if [[ "$SHELL" != *"zsh"* ]]; then
    chsh -s "$(which zsh)"
    log_success "Default shell changed to Zsh"
else
    log_warn "Zsh is already the default shell"
fi

# =============================================================================
# Installation Complete
# =============================================================================
echo ""
echo -e "${GREEN}=============================================="
echo -e "  Installation Complete!"
echo -e "==============================================${NC}"
echo ""
log_info "Next steps:"
echo "  1. Log out and log back in (or run 'zsh' to start a new session)"
echo "  2. In tmux, press Ctrl+B then I to install tmux plugins"
echo ""
log_info "Configuration differences from macOS:"
echo "  - Theme: Snazzy (instead of Catppuccin Mocha)"
echo "  - Tmux: Status bar at bottom (instead of top)"
echo "  - Tmux: Prefix is Ctrl+B (instead of Ctrl+A)"
echo ""
if [[ -f /proc/device-tree/model ]]; then
    HOSTNAME=$(hostname)
    echo -e "${GREEN}Your prompt will look like:${NC} 🍓 ${HOSTNAME}:~/path ❯"
fi
echo ""
