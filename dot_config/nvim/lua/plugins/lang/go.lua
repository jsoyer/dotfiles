-- Go development plugins
return {
  {
    "ray-x/go.nvim",
    dependencies = {
      "ray-x/guihua.lua",
      "neovim/nvim-lspconfig",
      "nvim-treesitter/nvim-treesitter",
    },
    ft = { "go", "gomod" },
    build = ':lua require("go.install").update_all_sync()',
    config = function()
      require("go").setup({
        -- LazyVim lang.go extra owns gopls, on_attach and DAP — disable here to avoid double clients
        lsp_cfg = false,
        lsp_on_attach = false,
        dap_debug = false,
        lsp_gofumpt = true, -- still tell gofumpt to run via go.nvim
      })
    end,
  },

  -- Go DAP integration
  {
    "leoluz/nvim-dap-go",
    ft = "go",
    dependencies = { "mfussenegger/nvim-dap" },
    opts = {},
  },
}
