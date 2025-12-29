-- Telescope fuzzy finder
return {
  {
    "nvim-telescope/telescope.nvim",
    branch = "0.1.x",
    cmd = "Telescope",
    dependencies = {
      "nvim-lua/plenary.nvim",
      { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
      "nvim-telescope/telescope-symbols.nvim",
    },
    keys = {
      -- Files
      { "<leader>sf", "<cmd>Telescope find_files<cr>", desc = "[S]earch [F]iles" },
      { "<leader>?", "<cmd>Telescope oldfiles<cr>", desc = "Recent files" },

      -- Search
      { "<leader>sg", "<cmd>Telescope live_grep<cr>", desc = "[S]earch by [G]rep" },
      { "<leader>sw", "<cmd>Telescope grep_string<cr>", desc = "[S]earch current [W]ord" },
      {
        "<leader>/",
        function()
          require("telescope.builtin").current_buffer_fuzzy_find(require("telescope.themes").get_dropdown({
            winblend = 10,
            previewer = true,
          }))
        end,
        desc = "[/] Fuzzily search in current buffer",
      },

      -- LSP
      { "<leader>sd", "<cmd>Telescope diagnostics<cr>", desc = "[S]earch [D]iagnostics" },
      { "<leader>sb", "<cmd>Telescope buffers<cr>", desc = "[ ] Find existing buffers" },

      -- Git
      { "<leader>sS", "<cmd>Telescope git_status<cr>", desc = "Git status" },
      {
        "<leader>sr",
        "<CMD>lua require('telescope').extensions.git_worktree.git_worktrees()<CR>",
        desc = "Git worktrees",
      },
      {
        "<leader>sR",
        "<CMD>lua require('telescope').extensions.git_worktree.create_git_worktree()<CR>",
        desc = "Create git worktree",
      },

      -- Commands
      { "<Leader><tab>", "<cmd>Telescope commands<cr>", desc = "Commands" },
    },
    opts = {
      defaults = {
        layout_strategy = "horizontal",
        layout_config = {
          preview_width = 0.65,
          horizontal = {
            size = {
              width = "95%",
              height = "95%",
            },
          },
        },
        mappings = {
          i = {
            ["<C-u>"] = false,
            ["<C-d>"] = false,
            ["<C-j>"] = require("telescope.actions").move_selection_next,
            ["<C-k>"] = require("telescope.actions").move_selection_previous,
          },
        },
      },
      pickers = {
        find_files = {
          theme = "dropdown",
        },
      },
    },
    config = function(_, opts)
      local telescope = require("telescope")
      telescope.setup(opts)

      -- Load extensions
      pcall(telescope.load_extension, "fzf")
      pcall(telescope.load_extension, "notify")
    end,
  },
}
