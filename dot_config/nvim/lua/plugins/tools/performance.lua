-- Filetype detection overrides (native Neovim)
vim.filetype.add({
  extension = {
    tf = "terraform",
    tfvars = "terraform",
    tfstate = "json",
  },
  filename = {
    [".gitignore"] = "gitignore",
    [".dockerignore"] = "gitignore",
  },
  pattern = {
    [".*%.env%..*"] = "sh",
  },
})

return {}
