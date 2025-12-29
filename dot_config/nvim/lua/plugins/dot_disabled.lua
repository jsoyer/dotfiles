-- Disabled plugins (fetch issues or not needed)
return {
  -- Disable vim-illuminate (fetch issues)
  { "RRethy/vim-illuminate", enabled = false },

  -- Disable vim-pencil (fetch issues) - not essential
  { "preservim/vim-pencil", enabled = false },

  -- Disable vim-repeat (fetch issues) - LazyVim handles this
  { "tpope/vim-repeat", enabled = false },

  -- Disable vim-sleuth (fetch issues) - we have manual settings
  { "tpope/vim-sleuth", enabled = false },

  -- Disable vim-startuptime (fetch issues) - can use :Lazy profile instead
  { "dstein64/vim-startuptime", enabled = false },

  -- Disable vimtex (fetch issues) - not needed unless you use LaTeX
  { "lervag/vimtex", enabled = false },

  -- Disable vim-surround (fetch issues) - use mini.surround instead
  { "tpope/vim-surround", enabled = false },

  -- Disable which-key (fetch issues) - LazyVim provides it
  { "folke/which-key.nvim", enabled = false },

  -- Disable yanky (fetch issues) - not essential
  { "gbprod/yanky.nvim", enabled = false },

  -- Disable zen-mode (fetch issues) - use Twilight instead or just :ZenMode won't work
  { "folke/zen-mode.nvim", enabled = false },

  -- Disable DAP temporarily (config issues)
  { "mfussenegger/nvim-dap", enabled = false },
  { "rcarriga/nvim-dap-ui", enabled = false },
  { "theHamsta/nvim-dap-virtual-text", enabled = false },
  { "leoluz/nvim-dap-go", enabled = false },
}
