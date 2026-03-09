-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")

-- Codeium platform override (Apple Silicon only)
if vim.fn.has("mac") == 1 and vim.uv.os_uname().machine == "arm64" then
  vim.g.codeium_platform_override = "mac-arm64"
end
