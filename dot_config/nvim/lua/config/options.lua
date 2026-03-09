-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- Leader keys (must be set before lazy)
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Line numbers
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.signcolumn = "yes"

-- Search
vim.opt.hlsearch = true
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.incsearch = true

-- Indentation
vim.opt.breakindent = true
vim.opt.expandtab = true
vim.opt.shiftwidth = 2
vim.opt.tabstop = 2
vim.opt.softtabstop = 2
vim.opt.smartindent = true

-- Persistence
vim.opt.undofile = true
vim.opt.undolevels = 10000
vim.opt.backup = false
vim.opt.swapfile = false

-- Clipboard
vim.opt.clipboard = "unnamedplus"

-- Completion
vim.opt.completeopt = "menuone,noselect,noinsert"
vim.opt.pumheight = 10

-- UI improvements
vim.opt.termguicolors = true
vim.opt.cursorline = true
vim.opt.scrolloff = 8
vim.opt.sidescrolloff = 8
vim.opt.wrap = false
vim.opt.colorcolumn = "120"
vim.opt.list = true
vim.opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }

-- Split windows
vim.opt.splitright = true
vim.opt.splitbelow = true

-- Performance
vim.opt.updatetime = 250
vim.opt.timeoutlen = 300
vim.opt.lazyredraw = false

-- Mouse
vim.opt.mouse = ""

-- Concealer (for markdown, etc.)
vim.opt.conceallevel = 2

-- Fold settings — treesitter foldexpr is expensive on ARM/RPi
if vim.uv.os_uname().machine:match("aarch64") then
  vim.opt.foldmethod = "indent"
else
  vim.opt.foldmethod = "expr"
  vim.opt.foldexpr = "nvim_treesitter#foldexpr()"
end
vim.opt.foldenable = false
vim.opt.foldlevel = 99

-- Spell checking
vim.opt.spelllang = { "en", "fr" }
vim.opt.spell = false

-- Format options
vim.opt.formatoptions = "jcroqlnt"

-- Grep program
if vim.fn.executable("rg") == 1 then
  vim.opt.grepprg = "rg --vimgrep"
  vim.opt.grepformat = "%f:%l:%c:%m"
end

-- Disable some builtin plugins
vim.g.loaded_node_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_ruby_provider = 0

-- Fix markdown indentation settings
vim.g.markdown_recommended_style = 0
