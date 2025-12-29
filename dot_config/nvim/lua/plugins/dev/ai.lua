-- AI coding assistants
return {
  -- Ollama/Gen.nvim for local LLM
  {
    "David-Kunz/gen.nvim",
    cmd = { "Gen" },
    keys = {
      { "<leader>ai", ":Gen<CR>", mode = { "n", "v" }, desc = "AI Generate" },
    },
    opts = {
      model = "llama3",
      host = "localhost",
      port = "11434",
      quit_map = "q",
      retry_map = "<c-r>",
      display_mode = "float",
      show_prompt = false,
      show_model = false,
      no_auto_close = false,
    },
    config = function(_, opts)
      require("gen").setup(opts)

      -- Custom prompts
      require("gen").prompts["DevOps me!"] = {
        prompt = "You are a senior devops engineer, acting as an assistant. You offer help with cloud technologies like: Terraform, AWS, kubernetes, python. You answer with code examples when possible. $input:\n$text",
        replace = true,
      }
    end,
  },

  -- Codeium for AI completions
  {
    "Exafunction/codeium.vim",
    event = "InsertEnter",
    config = function()
      vim.g.codeium_platform_override = "mac-arm64"

      -- Keymaps
      vim.keymap.set("i", "<C-e>", function()
        return vim.fn["codeium#Accept"]()
      end, { expr = true, silent = true, desc = "Accept Codeium suggestion" })

      vim.keymap.set("i", "<C-n>", function()
        return vim.fn["codeium#CycleCompletions"](1)
      end, { expr = true, silent = true, desc = "Next Codeium suggestion" })

      vim.keymap.set("i", "<C-p>", function()
        return vim.fn["codeium#CycleCompletions"](-1)
      end, { expr = true, silent = true, desc = "Previous Codeium suggestion" })

      vim.keymap.set("i", "<C-x>", function()
        return vim.fn["codeium#Clear"]()
      end, { expr = true, silent = true, desc = "Clear Codeium" })
    end,
  },
}
