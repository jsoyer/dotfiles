-- Performance optimization plugins
return {
  -- Faster filetype detection
  {
    "nathom/filetype.nvim",
    lazy = false,
    priority = 1000,
    opts = {
      overrides = {
        extensions = {
          tf = "terraform",
          tfvars = "terraform",
          tfstate = "json",
        },
        literal = {
          [".gitignore"] = "gitignore",
          [".dockerignore"] = "gitignore",
        },
        complex = {
          [".*%.env%..*"] = "sh",
        },
      },
    },
  },

  -- Improve startup time
  {
    "lewis6991/impatient.nvim",
    enabled = false, -- Disabled in Neovim 0.9+ as it's built-in
  },
}
