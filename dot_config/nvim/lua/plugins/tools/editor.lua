-- Editor enhancement plugins
return {
  -- Harpoon for quick file navigation
  {
    "ThePrimeagen/harpoon",
    branch = "harpoon2",
    dependencies = { "nvim-lua/plenary.nvim" },
    keys = function()
      local harpoon = require("harpoon")
      return {
        {
          "<leader>m",
          function()
            harpoon:list():add()
          end,
          desc = "Harpoon mark file",
        },
        {
          "<leader>ht",
          function()
            harpoon.ui:toggle_quick_menu(harpoon:list())
          end,
          desc = "Harpoon toggle menu",
        },
        {
          "<leader>sh",
          function()
            local conf = require("telescope.config").values
            local harpoon_files = harpoon:list()
            local file_paths = {}
            for _, item in ipairs(harpoon_files.items) do
              table.insert(file_paths, item.value)
            end

            require("telescope.pickers")
              .new({}, {
                prompt_title = "Harpoon",
                finder = require("telescope.finders").new_table({
                  results = file_paths,
                }),
                previewer = conf.file_previewer({}),
                sorter = conf.generic_sorter({}),
              })
              :find()
          end,
          desc = "Harpoon (Telescope)",
        },
      }
    end,
    config = function()
      require("harpoon"):setup()
    end,
  },

  -- File explorer: snacks_explorer (via lazyvim.json extra) handles <leader>e

  -- Goto preview for LSP
  {
    "rmagatti/goto-preview",
    keys = {
      { "gpd", "<cmd>lua require('goto-preview').goto_preview_definition()<CR>", desc = "Preview definition" },
      {
        "gpt",
        "<cmd>lua require('goto-preview').goto_preview_type_definition()<CR>",
        desc = "Preview type definition",
      },
      { "gpi", "<cmd>lua require('goto-preview').goto_preview_implementation()<CR>", desc = "Preview implementation" },
      { "gpr", "<cmd>lua require('goto-preview').goto_preview_references()<CR>", desc = "Preview references" },
      { "gP", "<cmd>lua require('goto-preview').close_all_win()<CR>", desc = "Close all preview windows" },
    },
    config = function()
      require("goto-preview").setup({
        width = 120,
        height = 15,
        border = { "↖", "─", "┐", "│", "┘", "─", "└", "│" },
        default_mappings = false,
        opacity = nil,
        post_open_hook = nil,
        references = {
          telescope = require("telescope.themes").get_dropdown({ hide_preview = false }),
        },
        focus_on_open = true,
        dismiss_on_move = false,
        force_close = true,
        bufhidden = "wipe",
        stack_floating_preview_windows = true,
        preview_window_title = { enable = true, position = "left" },
      })
    end,
  },

  -- Trouble for diagnostics (v3 API)
  {
    "folke/trouble.nvim",
    cmd = "Trouble",
    keys = {
      { "<leader>xx", "<cmd>Trouble diagnostics toggle<cr>", desc = "Toggle Trouble" },
      { "<leader>xw", "<cmd>Trouble diagnostics toggle filter.buf=0<cr>", desc = "Buffer diagnostics" },
      { "<leader>xd", "<cmd>Trouble diagnostics<cr>", desc = "Workspace diagnostics" },
      { "<leader>xl", "<cmd>Trouble loclist toggle<cr>", desc = "Location list" },
      { "<leader>xq", "<cmd>Trouble qflist toggle<cr>", desc = "Quickfix" },
      { "gR", "<cmd>Trouble lsp_references toggle<cr>", desc = "LSP references" },
    },
    opts = {
      use_diagnostic_signs = true,
    },
  },

  -- Todo comments
  {
    "folke/todo-comments.nvim",
    event = "LazyFile",
    dependencies = { "nvim-lua/plenary.nvim" },
    keys = {
      { "<leader>st", "<cmd>TodoTelescope<CR>", desc = "Todo (Telescope)" },
      {
        "]t",
        function()
          require("todo-comments").jump_next()
        end,
        desc = "Next todo",
      },
      {
        "[t",
        function()
          require("todo-comments").jump_prev()
        end,
        desc = "Previous todo",
      },
    },
    opts = {},
  },

  -- Note: vim-surround, vim-sleuth, vim-obsession disabled due to fetch issues
  -- Alternatives:
  -- - surround: use mini.surround (enabled in extras.lua)
  -- - sleuth: manual indentation settings in options.lua
  -- - obsession: use persistence.nvim (in extras.lua)

  -- Transparency toggle
  {
    "xiyaowong/nvim-transparent",
    cmd = "TransparentToggle",
    keys = {
      { "TT", "<cmd>TransparentToggle<CR>", desc = "Toggle transparency" },
    },
    opts = {
      enable = false,
    },
  },
}
