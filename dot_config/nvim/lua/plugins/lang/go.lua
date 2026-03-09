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
        -- Auto format and import on save
        lsp_cfg = true,
        lsp_gofumpt = true,
        lsp_on_attach = true,
        dap_debug = true,
      })

      -- Note: goimport on save is handled by go.nvim via lsp_on_attach = true
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
