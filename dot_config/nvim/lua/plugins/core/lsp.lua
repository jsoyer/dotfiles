-- LSP Configuration for LazyVim
return {
  -- Mason LSP installer configuration
  {
    "mason-org/mason.nvim",
    opts = {
      ensure_installed = {
        "clangd",
        "rust-analyzer",
        "pyright",
        "lua-language-server",
        "bash-language-server",
      },
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
        clangd = {},
        rust_analyzer = {},
        pyright = {},
        bashls = {},
        lua_ls = {
          settings = {
            Lua = {
              runtime = {
                version = "LuaJIT",
              },
              diagnostics = {
                globals = { "vim" },
              },
              workspace = {
                checkThirdParty = false,
                library = {
                  vim.fn.expand("$VIMRUNTIME/lua"),
                  vim.fn.stdpath("config") .. "/lua",
                },
              },
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
