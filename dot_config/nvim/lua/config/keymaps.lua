-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- Better escape from insert mode
vim.keymap.set("i", "jj", "<Esc>", { desc = "Exit insert mode" })
vim.keymap.set("i", "jk", "<Esc>", { desc = "Exit insert mode" })

-- Resize windows
vim.keymap.set("n", "<C-Up>", ":resize +2<CR>", { desc = "Increase window height" })
vim.keymap.set("n", "<C-Down>", ":resize -2<CR>", { desc = "Decrease window height" })
vim.keymap.set("n", "<C-Left>", ":vertical resize -2<CR>", { desc = "Decrease window width" })
vim.keymap.set("n", "<C-Right>", ":vertical resize +2<CR>", { desc = "Increase window width" })
vim.keymap.set("n", "<C-W>,", ":vertical resize -10<CR>", { desc = "Decrease width by 10" })
vim.keymap.set("n", "<C-W>.", ":vertical resize +10<CR>", { desc = "Increase width by 10" })

-- Buffer navigation (using <leader>b prefix to avoid conflicts)
vim.keymap.set("n", "<leader>bh", ":bprev<CR>", { desc = "Previous buffer" })
vim.keymap.set("n", "<leader>bl", ":bnext<CR>", { desc = "Next buffer" })
vim.keymap.set("n", "<leader>bj", ":bfirst<CR>", { desc = "First buffer" })
vim.keymap.set("n", "<leader>bk", ":blast<CR>", { desc = "Last buffer" })
vim.keymap.set("n", "<leader>bd", ":bdelete<CR>", { desc = "Delete buffer" })
vim.keymap.set("n", "<leader>bD", ":bdelete!<CR>", { desc = "Force delete buffer" })
vim.keymap.set("n", "<leader>ba", ":%bd|e#<CR>", { desc = "Delete all buffers except current" })

-- Alternative buffer navigation with H/L
vim.keymap.set("n", "H", ":bprev<CR>", { desc = "Previous buffer" })
vim.keymap.set("n", "L", ":bnext<CR>", { desc = "Next buffer" })

-- Navigation shortcuts
vim.keymap.set("n", "E", "$", { desc = "End of line" })
vim.keymap.set("n", "B", "^", { desc = "Beginning of line" })
vim.keymap.set("v", "E", "$", { desc = "End of line" })
vim.keymap.set("v", "B", "^", { desc = "Beginning of line" })

-- Better indenting
vim.keymap.set("v", "<", "<gv", { desc = "Indent left" })
vim.keymap.set("v", ">", ">gv", { desc = "Indent right" })

-- Better paste
vim.keymap.set("v", "p", '"_dP', { desc = "Paste without yanking" })

-- Clear search highlight
vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<cr>", { desc = "Clear search highlight" })

-- Better search (keep cursor centered)
vim.keymap.set("n", "n", "nzzzv", { desc = "Next search result" })
vim.keymap.set("n", "N", "Nzzzv", { desc = "Previous search result" })

-- Join lines keeping cursor position
vim.keymap.set("n", "J", "mzJ`z", { desc = "Join lines" })

-- Better undo break points
vim.keymap.set("i", ",", ",<c-g>u")
vim.keymap.set("i", ".", ".<c-g>u")
vim.keymap.set("i", "!", "!<c-g>u")
vim.keymap.set("i", "?", "?<c-g>u")

-- Word wrap navigation
vim.keymap.set("n", "k", "v:count == 0 ? 'gk' : 'k'", { expr = true, silent = true, desc = "Move up (wrap-aware)" })
vim.keymap.set("n", "j", "v:count == 0 ? 'gj' : 'j'", { expr = true, silent = true, desc = "Move down (wrap-aware)" })

-- Select all
vim.keymap.set("n", "<C-a>", "gg<S-v>G", { desc = "Select all" })

-- Better command mode navigation
vim.keymap.set("c", "<C-a>", "<Home>", { desc = "Start of line" })
vim.keymap.set("c", "<C-e>", "<End>", { desc = "End of line" })

-- Quick fix/location list navigation
vim.keymap.set("n", "[q", ":cprev<CR>", { desc = "Previous quickfix" })
vim.keymap.set("n", "]q", ":cnext<CR>", { desc = "Next quickfix" })
vim.keymap.set("n", "[l", ":lprev<CR>", { desc = "Previous location" })
vim.keymap.set("n", "]l", ":lnext<CR>", { desc = "Next location" })

-- Diagnostic navigation
vim.keymap.set("n", "[d", vim.diagnostic.goto_prev, { desc = "Previous diagnostic" })
vim.keymap.set("n", "]d", vim.diagnostic.goto_next, { desc = "Next diagnostic" })
vim.keymap.set("n", "[e", function()
  vim.diagnostic.goto_prev({ severity = vim.diagnostic.severity.ERROR })
end, { desc = "Previous error" })
vim.keymap.set("n", "]e", function()
  vim.diagnostic.goto_next({ severity = vim.diagnostic.severity.ERROR })
end, { desc = "Next error" })

-- Toggle options
vim.keymap.set("n", "<leader>ts", function()
  vim.opt.spell = not vim.opt.spell:get()
end, { desc = "Toggle spell check" })
vim.keymap.set("n", "<leader>tw", function()
  vim.opt.wrap = not vim.opt.wrap:get()
end, { desc = "Toggle line wrap" })
vim.keymap.set("n", "<leader>tr", function()
  vim.opt.relativenumber = not vim.opt.relativenumber:get()
end, { desc = "Toggle relative number" })
vim.keymap.set("n", "<leader>tt", ":TransparentToggle<CR>", { desc = "Toggle transparency" })
vim.keymap.set("n", "<leader>tW", ":Twilight<CR>", { desc = "Toggle Twilight" })

-- Split windows (see Enhanced Split Management section below)

-- Terminal mappings
vim.keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })
vim.keymap.set("t", "<C-h>", "<C-\\><C-n><C-w>h", { desc = "Go to left window" })
vim.keymap.set("t", "<C-j>", "<C-\\><C-n><C-w>j", { desc = "Go to lower window" })
vim.keymap.set("t", "<C-k>", "<C-\\><C-n><C-w>k", { desc = "Go to upper window" })
vim.keymap.set("t", "<C-l>", "<C-\\><C-n><C-w>l", { desc = "Go to right window" })

-- File operations
vim.keymap.set("n", "<leader>fn", ":enew<CR>", { desc = "New file" })
vim.keymap.set("n", "<leader>fs", ":w<CR>", { desc = "Save file" })
vim.keymap.set("n", "<leader>fS", ":wa<CR>", { desc = "Save all files" })

-- Go specific (scoped to Go buffers)
vim.api.nvim_create_autocmd("FileType", {
  pattern = "go",
  callback = function(ev)
    vim.keymap.set("n", "<leader>ge", "<cmd>GoIfErr<cr>", { silent = true, desc = "Add if err (Go)", buffer = ev.buf })
  end,
})

-- Disable default space behavior
vim.keymap.set({ "n", "v" }, "<Space>", "<Nop>", { silent = true })

-- ============================================================================
-- Enhanced Split Management
-- ============================================================================

-- Better split creation (opens in same directory, more intuitive)
vim.keymap.set("n", "<leader>sv", ":vsplit<CR>", { desc = "Split vertical" })
vim.keymap.set("n", "<leader>sh", ":split<CR>", { desc = "Split horizontal" })
vim.keymap.set("n", "<leader>sx", ":close<CR>", { desc = "Close current split" })
vim.keymap.set("n", "<leader>so", ":only<CR>", { desc = "Close other splits" })

-- Quick splits without prefix (alternative to <leader>)
vim.keymap.set("n", "<C-w>v", ":vsplit<CR>", { desc = "Split vertical" })
vim.keymap.set("n", "<C-w>s", ":split<CR>", { desc = "Split horizontal" })
vim.keymap.set("n", "<C-w>x", ":close<CR>", { desc = "Close split" })

-- Equalize split sizes
vim.keymap.set("n", "<leader>s=", "<C-w>=", { desc = "Equalize split sizes" })

-- ============================================================================
-- Enhanced Buffer Navigation
-- ============================================================================

-- Tab-like buffer navigation (super intuitive)
vim.keymap.set("n", "<Tab>", ":bnext<CR>", { desc = "Next buffer" })
vim.keymap.set("n", "<S-Tab>", ":bprev<CR>", { desc = "Previous buffer" })

-- Alternative: use Ctrl+Tab (like browser tabs)
vim.keymap.set("n", "<C-Tab>", ":bnext<CR>", { desc = "Next buffer" })
vim.keymap.set("n", "<C-S-Tab>", ":bprev<CR>", { desc = "Previous buffer" })

vim.keymap.set("n", "<leader>bn", ":enew<CR>", { desc = "New buffer" })

-- Close all buffers except current
vim.keymap.set("n", "<leader>bo", ":%bd|e#|bd#<CR>", { desc = "Close other buffers" })

