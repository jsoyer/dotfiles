return {
  "hrsh7th/nvim-cmp",
  opts = function(_, opts)
    local cmp = require("cmp")

    -- Override default options
    opts.view = {
      entries = "native",
    }

    -- Add custom mappings while preserving defaults
    opts.mapping = vim.tbl_extend("force", opts.mapping or {}, {
      ["<C-d>"] = cmp.mapping.scroll_docs(-4),
      ["<C-f>"] = cmp.mapping.scroll_docs(4),
      ["<C-Space>"] = cmp.mapping.complete(),
      ["<CR>"] = cmp.mapping.confirm({
        behavior = cmp.ConfirmBehavior.Replace,
        select = true,
      }),
    })

    -- Add custom sources
    opts.sources = cmp.config.sources({
      { name = "nvim_lsp" },
      { name = "luasnip" },
      { name = "neorg" },
      { name = "buffer" },
      { name = "path" },
    })

    return opts
  end,
}
