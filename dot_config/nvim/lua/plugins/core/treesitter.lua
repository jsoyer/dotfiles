-- Treesitter configuration
return {
  {
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    event = { "LazyFile", "VeryLazy" },
    dependencies = {
      "nvim-treesitter/nvim-treesitter-textobjects",
    },
    opts = {
      ensure_installed = {
        "bash",
        "c",
        "css",
        "diff",
        "go",
        "html",
        "javascript",
        "jsdoc",
        "json",
        "jsonc",
        "kdl",
        "lua",
        "luadoc",
        "luap",
        "markdown",
        "markdown_inline",
        "org",
        "python",
        "query",
        "regex",
        "rust",
        "sql",
        "terraform",
        "toml",
        "tsx",
        "typescript",
        "vim",
        "vimdoc",
        "xml",
        "yaml",
      },
      auto_install = true,
      highlight = {
        enable = true,
        additional_vim_regex_highlighting = false,
      },
      indent = { enable = true },
      incremental_selection = {
        enable = true,
        keymaps = {
          init_selection = "<c-space>",
          node_incremental = "<c-space>",
          scope_incremental = false,
          node_decremental = "<c-backspace>",
        },
      },
      textobjects = {
        select = {
          enable = true,
          lookahead = true,
          keymaps = {
            ["aa"] = "@parameter.outer",
            ["ia"] = "@parameter.inner",
            ["af"] = "@function.outer",
            ["if"] = "@function.inner",
            ["ac"] = "@class.outer",
            ["ic"] = "@class.inner",
            ["ii"] = "@conditional.inner",
            ["ai"] = "@conditional.outer",
            ["il"] = "@loop.inner",
            ["al"] = "@loop.outer",
            ["at"] = "@comment.outer",
          },
        },
        move = {
          enable = true,
          set_jumps = true,
          goto_next_start = {
            ["]f"] = "@function.outer",
            ["]]"] = "@class.outer",
          },
          goto_next_end = {
            ["]F"] = "@function.outer",
            ["]["] = "@class.outer",
          },
          goto_previous_start = {
            ["[f"] = "@function.outer",
            ["[["] = "@class.outer",
          },
          goto_previous_end = {
            ["[F"] = "@function.outer",
            ["[]"] = "@class.outer",
          },
        },
        swap = {
          enable = true,
          swap_next = {
            ["<leader>a"] = "@parameter.inner",
          },
          swap_previous = {
            ["<leader>A"] = "@parameter.inner",
          },
        },
      },
    },
    -- Note: LazyVim will automatically call setup, no need for config function
  },
}
