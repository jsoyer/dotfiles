#!/bin/bash
# =============================================================================
# 🔐 1Password Installation Script for Linux ARM64
# =============================================================================
#
# This script installs 1Password on Linux ARM64/aarch64 systems
# (Raspberry Pi 4/5, ARM servers, etc.)
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/jsoyer/dotfiles/main/scripts/install-1password-linux.sh | bash
#
# Supported architectures:
#   ✅ aarch64 (ARM 64-bit)
#   ✅ arm64 (ARM 64-bit)
#   ❌ armv7l (ARM 32-bit) - Not supported by 1Password
#   ❌ x86_64 (Intel/AMD) - Use official apt repository instead
#
# =============================================================================

set -e

# 🎨 Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 📝 Logging functions
log_info()    { echo -e "${BLUE}ℹ️  [INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}✅ [OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠️  [WARN]${NC} $1"; }
log_error()   { echo -e "${RED}❌ [ERROR]${NC} $1"; }

# 🎬 Header
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}     🔐 ${BLUE}1Password Installation Script for Linux ARM64${NC}     ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# 🔍 Architecture Check
# =============================================================================
log_info "Checking system architecture..."

ARCH=$(uname -m)

if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
    log_error "Unsupported architecture: $ARCH"
    echo ""
    echo -e "  ${YELLOW}This script only supports ARM64 (aarch64/arm64) systems.${NC}"
    echo ""
    if [[ "$ARCH" == "x86_64" ]]; then
        echo -e "  ${BLUE}For x86_64, use the official apt repository:${NC}"
        echo "    curl -sS https://downloads.1password.com/linux/keys/1password.asc | sudo gpg --dearmor -o /usr/share/keyrings/1password-archive-keyring.gpg"
        echo "    echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/amd64 stable main' | sudo tee /etc/apt/sources.list.d/1password.list"
        echo "    sudo apt update && sudo apt install 1password"
    elif [[ "$ARCH" == "armv7l" ]]; then
        echo -e "  ${RED}ARM 32-bit (armv7l) is not supported by 1Password.${NC}"
    fi
    echo ""
    exit 1
fi

log_success "Architecture: $ARCH ✓"

# =============================================================================
# 🔍 Check if already installed
# =============================================================================
if command -v 1password &> /dev/null || [[ -d "/opt/1Password" ]]; then
    log_warn "1Password appears to be already installed"
    read -p "Do you want to reinstall? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled"
        exit 0
    fi
fi

# =============================================================================
# 📦 Download 1Password
# =============================================================================
log_info "Downloading 1Password for ARM64..."

DOWNLOAD_URL="https://downloads.1password.com/linux/tar/stable/aarch64/1password-latest.tar.gz"
DOWNLOAD_FILE="/tmp/1password-latest.tar.gz"

if ! curl -sSL -o "$DOWNLOAD_FILE" "$DOWNLOAD_URL"; then
    log_error "Failed to download 1Password"
    exit 1
fi

log_success "Download complete"

# =============================================================================
# 📂 Extract archive
# =============================================================================
log_info "Extracting archive..."

cd /tmp
if ! tar -xf "$DOWNLOAD_FILE"; then
    log_error "Failed to extract archive"
    rm -f "$DOWNLOAD_FILE"
    exit 1
fi

log_success "Extraction complete"

# =============================================================================
# 🚀 Install 1Password
# =============================================================================
log_info "Installing 1Password to /opt/1Password..."

# Create installation directory
sudo mkdir -p /opt/1Password

# Move files to installation directory
sudo rm -rf /opt/1Password/*
sudo mv 1password-*/* /opt/1Password/

log_success "Files installed"

# =============================================================================
# ⚙️ Run post-installation script
# =============================================================================
log_info "Running post-installation setup..."

if [[ -f "/opt/1Password/after-install.sh" ]]; then
    sudo /opt/1Password/after-install.sh
    log_success "Post-installation complete"
else
    log_warn "Post-installation script not found, skipping"
fi

# =============================================================================
# 🧹 Cleanup
# =============================================================================
log_info "Cleaning up temporary files..."

rm -f "$DOWNLOAD_FILE"
rm -rf /tmp/1password-*/

log_success "Cleanup complete"

# =============================================================================
# ✅ Installation Complete
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}          🎉 ${GREEN}1Password installed successfully!${NC}              ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "To launch 1Password:"
echo -e "  ${CYAN}•${NC} From terminal: ${BLUE}1password${NC}"
echo -e "  ${CYAN}•${NC} Or find it in your application menu"
echo ""
log_info "To enable CLI integration:"
echo -e "  ${CYAN}•${NC} Open 1Password → Settings → Developer"
echo -e "  ${CYAN}•${NC} Enable 'Integrate with 1Password CLI'"
echo ""
