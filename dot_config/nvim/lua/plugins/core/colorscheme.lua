-- Platform detection (vim.uv.os_uname() is in-memory, no subprocess)
local machine = vim.uv.os_uname().machine
local is_rpi = machine:match("aarch64") ~= nil
local is_linux = vim.fn.has("unix") == 1 and vim.fn.has("mac") == 0

return {
  -- Catppuccin colorscheme (macOS default)
  {
    "catppuccin/nvim",
    name = "catppuccin",
    priority = 1000,
    lazy = is_rpi or is_linux,
    opts = {
      flavour = "mocha",
      transparent_background = false,
      integrations = {
        cmp = true,
        gitsigns = true,
        nvimtree = true,
        treesitter = true,
        notify = true,
        mini = true,
        telescope = true,
        which_key = true,
        mason = true,
        neogit = true,
      },
    },
  },

  -- Snazzy colorscheme (RPi/Linux)
  {
    "connorholyday/vim-snazzy",
    name = "snazzy",
    priority = 1000,
    lazy = not (is_rpi or is_linux),
  },

  -- Dracula colorscheme (alternative)
  {
    "Mofiqul/dracula.nvim",
    lazy = true,
  },

  -- Configure LazyVim to load colorscheme based on platform
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = (is_rpi or is_linux) and "snazzy" or "catppuccin",
    },
  },
}
