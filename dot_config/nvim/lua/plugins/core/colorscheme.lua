return {
  -- Catppuccin colorscheme
  {
    "catppuccin/nvim",
    name = "catppuccin",
    priority = 1000,
    opts = {
      flavour = "mocha", -- latte, frappe, macchiato, mocha
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

  -- Dracula colorscheme (alternative)
  {
    "Mofiqul/dracula.nvim",
    lazy = true,
  },

  -- Configure LazyVim to load catppuccin by default
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "catppuccin",
    },
  },
}
