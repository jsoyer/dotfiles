-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here

local augroup = vim.api.nvim_create_augroup
local autocmd = vim.api.nvim_create_autocmd

-- Highlight on yank
local highlight_group = augroup("YankHighlight", { clear = true })
autocmd("TextYankPost", {
  callback = function()
    vim.highlight.on_yank({ higroup = "IncSearch", timeout = 200 })
  end,
  group = highlight_group,
  pattern = "*",
})

-- Resize splits if window got resized
autocmd("VimResized", {
  group = augroup("ResizeSplits", { clear = true }),
  callback = function()
    local current_tab = vim.fn.tabpagenr()
    vim.cmd("tabdo wincmd =")
    vim.cmd("tabnext " .. current_tab)
  end,
})

-- Close some filetypes with <q>
autocmd("FileType", {
  group = augroup("CloseWithQ", { clear = true }),
  pattern = {
    "qf",
    "help",
    "man",
    "notify",
    "lspinfo",
    "spectre_panel",
    "startuptime",
    "tsplayground",
    "PlenaryTestPopup",
    "checkhealth",
  },
  callback = function(event)
    vim.bo[event.buf].buflisted = false
    vim.keymap.set("n", "q", "<cmd>close<cr>", { buffer = event.buf, silent = true })
  end,
})

-- Disable autoformat for certain filetypes
autocmd("FileType", {
  group = augroup("NoAutoFormat", { clear = true }),
  pattern = { "text", "markdown" },
  callback = function()
    vim.b.autoformat = false
  end,
})

-- Auto create directory when saving a file
autocmd("BufWritePre", {
  group = augroup("AutoCreateDir", { clear = true }),
  callback = function(event)
    if event.match:match("^%w%w+://") then
      return
    end
    local file = vim.uv.fs_realpath(event.match) or event.match
    vim.fn.mkdir(vim.fn.fnamemodify(file, ":p:h"), "p")
  end,
})

-- Restore cursor position
autocmd("BufReadPost", {
  group = augroup("RestoreCursor", { clear = true }),
  callback = function()
    local mark = vim.api.nvim_buf_get_mark(0, '"')
    local lcount = vim.api.nvim_buf_line_count(0)
    if mark[1] > 0 and mark[1] <= lcount then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})

-- Check if file changed outside of Neovim (also covers FocusGained)
autocmd({ "FocusGained", "TermClose", "TermLeave" }, {
  group = augroup("Checktime", { clear = true }),
  command = "checktime",
})

-- Remove trailing whitespace on save
autocmd("BufWritePre", {
  group = augroup("TrimWhitespace", { clear = true }),
  pattern = "*",
  callback = function()
    local curpos = vim.api.nvim_win_get_cursor(0)
    vim.cmd([[keeppatterns %s/\s\+$//e]])
    vim.api.nvim_win_set_cursor(0, curpos)
  end,
})

-- Disable diagnostics in insert mode
autocmd("InsertEnter", {
  group = augroup("DisableDiagnosticsInInsert", { clear = true }),
  callback = function()
    vim.diagnostic.enable(false, { bufnr = 0 })
  end,
})

autocmd("InsertLeave", {
  group = augroup("EnableDiagnosticsOnLeave", { clear = true }),
  callback = function()
    vim.diagnostic.enable(true, { bufnr = 0 })
  end,
})

-- Auto-format on save for specific filetypes
autocmd("BufWritePre", {
  group = augroup("AutoFormat", { clear = true }),
  pattern = { "*.lua", "*.go", "*.rs", "*.ts", "*.tsx", "*.js", "*.jsx", "*.json", "*.yaml", "*.yml" },
  callback = function()
    if vim.b.autoformat ~= false then
      vim.lsp.buf.format({ async = false })
    end
  end,
})

-- Enable wrap mode for certain filetypes
autocmd("FileType", {
  group = augroup("WrapMode", { clear = true }),
  pattern = { "gitcommit", "markdown", "text" },
  callback = function()
    vim.opt_local.wrap = true
    vim.opt_local.spell = true
  end,
})

-- Set conceallevel for certain filetypes
autocmd("FileType", {
  group = augroup("ConcealLevel", { clear = true }),
  pattern = { "json", "jsonc", "markdown" },
  callback = function()
    vim.opt_local.conceallevel = 0
  end,
})

-- Terminal settings
autocmd("TermOpen", {
  group = augroup("TerminalSettings", { clear = true }),
  callback = function()
    vim.opt_local.number = false
    vim.opt_local.relativenumber = false
    vim.opt_local.signcolumn = "no"
  end,
})

-- Show cursor line only in active window
autocmd({ "InsertLeave", "WinEnter" }, {
  group = augroup("AutoCursorLine", { clear = true }),
  callback = function()
    if vim.bo.filetype ~= "alpha" then
      vim.wo.cursorline = true
    end
  end,
})

autocmd({ "InsertEnter", "WinLeave" }, {
  group = augroup("AutoNoCursorLine", { clear = true }),
  callback = function()
    vim.wo.cursorline = false
  end,
})
