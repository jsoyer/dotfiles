-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here
-- NOTE: YankHighlight, ResizeSplits, RestoreCursor, Checktime, AutoCursorLine
--       are intentionally omitted — LazyVim ships them already.

local augroup = vim.api.nvim_create_augroup
local autocmd = vim.api.nvim_create_autocmd

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

-- Remove trailing whitespace on save (skip markdown/text where trailing spaces are semantic)
autocmd("BufWritePre", {
  group = augroup("TrimWhitespace", { clear = true }),
  pattern = "*",
  callback = function()
    local ft = vim.bo.filetype
    if ft == "markdown" or ft == "text" or vim.b.autoformat == false then
      return
    end
    local curpos = vim.api.nvim_win_get_cursor(0)
    vim.cmd([[keeppatterns %s/\s\+$//e]])
    vim.api.nvim_win_set_cursor(0, curpos)
  end,
})

-- Disable diagnostics in insert mode (single augroup for paired events)
local diag_group = augroup("DiagnosticsInsertMode", { clear = true })
autocmd("InsertEnter", {
  group = diag_group,
  callback = function()
    vim.diagnostic.enable(false, { bufnr = 0 })
  end,
})
autocmd("InsertLeave", {
  group = diag_group,
  callback = function()
    vim.diagnostic.enable(true, { bufnr = 0 })
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
