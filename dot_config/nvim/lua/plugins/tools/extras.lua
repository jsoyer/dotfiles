-- Extra modern plugins
return {
  -- Note: Better escape is handled in config/keymaps.lua with simple vim.keymap.set
  -- No need for a plugin for jj/jk -> Esc

  -- Flash for better navigation
  {
    "folke/flash.nvim",
    event = "VeryLazy",
    opts = {},
    keys = {
      {
        "s",
        mode = { "n", "x", "o" },
        function()
          require("flash").jump()
        end,
        desc = "Flash",
      },
      {
        "S",
        mode = { "n", "x", "o" },
        function()
          require("flash").treesitter()
        end,
        desc = "Flash Treesitter",
      },
      {
        "r",
        mode = "o",
        function()
          require("flash").remote()
        end,
        desc = "Remote Flash",
      },
      {
        "R",
        mode = { "o", "x" },
        function()
          require("flash").treesitter_search()
        end,
        desc = "Treesitter Search",
      },
      {
        "<c-s>",
        mode = { "c" },
        function()
          require("flash").toggle()
        end,
        desc = "Toggle Flash Search",
      },
    },
  },

  -- Better quickfix/location list
  {
    "kevinhwang91/nvim-bqf",
    ft = "qf",
    opts = {},
  },

  -- Note: which-key disabled due to fetch issues
  -- LazyVim provides which-key by default anyway

  -- Persistence for session management
  {
    "folke/persistence.nvim",
    event = "BufReadPre",
    opts = { options = vim.opt.sessionoptions:get() },
    keys = {
      {
        "<leader>qs",
        function()
          require("persistence").load()
        end,
        desc = "Restore Session",
      },
      {
        "<leader>ql",
        function()
          require("persistence").load({ last = true })
        end,
        desc = "Restore Last Session",
      },
      {
        "<leader>qd",
        function()
          require("persistence").stop()
        end,
        desc = "Don't Save Current Session",
      },
    },
  },

  -- Smooth scrolling (disabled on ARM/RPi — too slow)
  {
    "karb94/neoscroll.nvim",
    enabled = not vim.uv.os_uname().machine:match("aarch64"),
    event = "VeryLazy",
    opts = {
      mappings = { "<C-u>", "<C-d>", "<C-b>", "<C-f>", "<C-y>", "<C-e>", "zt", "zz", "zb" },
      hide_cursor = true,
      stop_eof = true,
      respect_scrolloff = false,
      cursor_scrolls_alone = true,
    },
  },

  -- Git blame inline
  {
    "f-person/git-blame.nvim",
    event = "LazyFile",
    keys = {
      { "<leader>gb", "<cmd>GitBlameToggle<cr>", desc = "Toggle Git Blame" },
    },
    opts = {
      enabled = false, -- Start disabled, toggle with keymap
      message_template = " <summary> • <date> • <author>",
      date_format = "%r",
    },
  },

  -- Better incremental rename
  {
    "smjonas/inc-rename.nvim",
    cmd = "IncRename",
    keys = {
      {
        "<leader>rn",
        function()
          return ":IncRename " .. vim.fn.expand("<cword>")
        end,
        expr = true,
        desc = "Incremental rename",
      },
    },
    opts = {},
  },

  -- Colorizer for hex colors
  {
    "NvChad/nvim-colorizer.lua",
    event = "LazyFile",
    cmd = { "ColorizerToggle", "ColorizerAttachToBuffer" },
    keys = {
      { "<leader>tc", "<cmd>ColorizerToggle<cr>", desc = "Toggle Colorizer" },
    },
    config = function()
      require("colorizer").setup({
        "*",
        css = { css = true },
        html = { mode = "foreground" },
      })
    end,
  },

  -- Better marks
  {
    "chentoast/marks.nvim",
    event = "LazyFile",
    opts = {},
  },

  -- Refactoring
  {
    "ThePrimeagen/refactoring.nvim",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "nvim-treesitter/nvim-treesitter",
    },
    keys = {
      {
        "<leader>re",
        function()
          require("refactoring").refactor("Extract Function")
        end,
        mode = "v",
        desc = "Extract Function",
      },
      {
        "<leader>rf",
        function()
          require("refactoring").refactor("Extract Function To File")
        end,
        mode = "v",
        desc = "Extract Function To File",
      },
      {
        "<leader>rv",
        function()
          require("refactoring").refactor("Extract Variable")
        end,
        mode = "v",
        desc = "Extract Variable",
      },
      {
        "<leader>ri",
        function()
          require("refactoring").refactor("Inline Variable")
        end,
        mode = { "n", "v" },
        desc = "Inline Variable",
      },
    },
    opts = {},
  },

  -- Mini.surround — override LazyVim default gz* mappings to gs* prefix
  {
    "nvim-mini/mini.surround",
    opts = {
      mappings = {
        add = "gsa",
        delete = "gsd",
        find = "gsf",
        find_left = "gsF",
        highlight = "gsh",
        replace = "gsr",
        update_n_lines = "gsn",
      },
    },
  },
}
