echo "🧹 Starting maintenance..."

# Update package managers
echo "📦 Updating Homebrew..."
brew update && brew upgrade
brew upgrade --cask --greedy
brew cleanup -s
brew bundle dump --force --file=~/.private/Brewfile

# Update App Store apps
echo "🏪 Updating App Store apps..."
mas upgrade

# Clean up Docker
echo "🐳 Cleaning Docker..."
docker system prune -f --volumes

# Clean up downloads folder
echo "🗑️ Cleaning Downloads..."
#find ~/Downloads -mtime +30 -exec mv {} ~/.Trash \;

echo "✨ Maintenance complete!"
