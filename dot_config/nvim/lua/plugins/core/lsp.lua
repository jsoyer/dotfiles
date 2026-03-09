-- LSP Configuration for LazyVim
local is_arm = vim.uv.os_uname().machine:match("aarch64") ~= nil

-- Heavy LSP servers skipped on ARM/RPi (clangd, rust-analyzer are resource-intensive)
local ensure_installed = { "pyright", "lua-language-server", "bash-language-server" }
if not is_arm then
  vim.list_extend(ensure_installed, { "clangd", "rust-analyzer" })
end

return {
  -- Mason LSP installer configuration
  {
    "mason-org/mason.nvim",
    opts = {
      ensure_installed = ensure_installed,
    },
  },

  -- LSP Configuration
  {
    "neovim/nvim-lspconfig",
    opts = {
      -- Global diagnostics configuration
      diagnostics = {
        underline = true,
        update_in_insert = false,
        virtual_text = {
          spacing = 4,
          source = "if_many",
          prefix = "●",
        },
        severity_sort = true,
      },

      -- LSP servers configuration
      servers = {
        pyright = {},
        bashls = {},
        lua_ls = {
          settings = {
            Lua = {
              runtime = { version = "LuaJIT" },
              diagnostics = { globals = { "vim" } },
              workspace = { checkThirdParty = false },
              telemetry = { enable = false },
            },
          },
        },
      },
    },
  },

  -- Fidget for LSP progress
  {
    "j-hui/fidget.nvim",
    opts = {},
  },
}
