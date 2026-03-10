-- AI coding assistants
return {
  -- codecompanion.nvim: multi-provider AI chat + inline editing
  -- Providers: Claude, ChatGPT, Gemini, Mistral, Ollama + ACP agents (Claude Code, Gemini CLI, OpenCode, Mistral Vibe, Codex)
  {
    "olimorris/codecompanion.nvim",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "nvim-treesitter/nvim-treesitter",
      "hrsh7th/nvim-cmp",
    },
    cmd = {
      "CodeCompanion",
      "CodeCompanionChat",
      "CodeCompanionActions",
    },
    keys = {
      { "<leader>aa", "<cmd>CodeCompanionActions<cr>",     mode = { "n", "v" }, desc = "AI Actions" },
      { "<leader>ac", "<cmd>CodeCompanionChat Toggle<cr>", mode = { "n", "v" }, desc = "AI Chat toggle" },
      { "<leader>an", "<cmd>CodeCompanionChat<cr>",        mode = { "n", "v" }, desc = "AI New chat" },
      { "<leader>ai", "<cmd>CodeCompanion<cr>",            mode = { "n", "v" }, desc = "AI Inline" },
      { "<leader>aq", "<cmd>CodeCompanionChat Toggle<cr>", mode = "n",          desc = "AI Quick chat" },
      { "<leader>ae", "<cmd>CodeCompanionActions<cr>",     mode = "v",          desc = "AI Actions (visual)" },
    },
    config = function(_, opts)
      -- Pick default adapter: first one whose API key is set, fallback to ollama
      local api_adapters = {
        { name = "anthropic", env = "ANTHROPIC_API_KEY" },
        { name = "openai",    env = "OPENAI_API_KEY" },
        { name = "gemini",    env = "GEMINI_API_KEY" },
        { name = "mistral",   env = "MISTRAL_API_KEY" },
      }
      local default = "ollama"
      for _, a in ipairs(api_adapters) do
        if vim.env[a.env] and vim.env[a.env] ~= "" then
          default = a.name
          break
        end
      end
      opts.strategies = {
        chat   = { adapter = default },
        inline = { adapter = default },
        agent  = { adapter = default },
      }
      require("codecompanion").setup(opts)
    end,
    opts = {
      -- strategies are set dynamically in config() above

      adapters = {
        -- ----------------------------------------------------------------
        -- HTTP API adapters
        -- ----------------------------------------------------------------

        -- Anthropic Claude (API key via 1Password → secrets.zsh ANTHROPIC_API_KEY)
        anthropic = function()
          return require("codecompanion.adapters").extend("anthropic", {
            env = { api_key = "ANTHROPIC_API_KEY" },
            schema = {
              model = {
                default = "claude-opus-4-6",
                choices = {
                  "claude-opus-4-6",
                  "claude-sonnet-4-6",
                  "claude-haiku-4-5-20251001",
                },
              },
            },
          })
        end,

        -- OpenAI ChatGPT / Codex (API key via 1Password → secrets.zsh OPENAI_API_KEY)
        openai = function()
          return require("codecompanion.adapters").extend("openai", {
            env = { api_key = "OPENAI_API_KEY" },
            schema = {
              model = {
                default = "gpt-4o",
                choices = {
                  "gpt-4o",
                  "gpt-4o-mini",
                  "o3",
                  "o4-mini",
                  "codex-mini-latest",
                },
              },
            },
          })
        end,

        -- Google Gemini (API key via 1Password → secrets.zsh GEMINI_API_KEY)
        gemini = function()
          return require("codecompanion.adapters").extend("gemini", {
            env = { api_key = "GEMINI_API_KEY" },
            schema = {
              model = {
                default = "gemini-2.5-pro",
                choices = {
                  "gemini-2.5-pro",
                  "gemini-2.5-flash",
                  "gemini-2.0-flash",
                },
              },
            },
          })
        end,

        -- Mistral (API key via 1Password → secrets.zsh MISTRAL_API_KEY)
        mistral = function()
          return require("codecompanion.adapters").extend("mistral", {
            env = { api_key = "MISTRAL_API_KEY" },
            schema = {
              model = {
                default = "mistral-large-latest",
                choices = {
                  "mistral-large-latest",
                  "mistral-small-latest",
                  "codestral-latest",
                },
              },
            },
          })
        end,

        -- Ollama (local, no auth required)
        ollama = function()
          return require("codecompanion.adapters").extend("ollama", {
            schema = {
              model = {
                default = "llama3",
                choices = {
                  "llama3",
                  "mistral",
                  "codestral",
                  "deepseek-coder-v2",
                  "qwen2.5-coder",
                },
              },
            },
          })
        end,

        -- ----------------------------------------------------------------
        -- ACP agent adapters (use CLI tools' existing auth, no extra keys)
        -- ----------------------------------------------------------------

        -- Claude Code CLI
        claude_code = function()
          return require("codecompanion.adapters").extend("claude_code", {})
        end,

        -- Gemini CLI
        gemini_cli = function()
          return require("codecompanion.adapters").extend("gemini_cli", {})
        end,

        -- OpenCode
        opencode = function()
          return require("codecompanion.adapters").extend("opencode", {})
        end,

        -- Mistral Vibe (le Vibe Coding de Mistral)
        mistral_vibe = function()
          return require("codecompanion.adapters").extend("mistral_vibe", {})
        end,

        -- Codex CLI (OpenAI)
        codex = function()
          return require("codecompanion.adapters").extend("codex", {})
        end,
      },

      -- Prompt library: actions disponibles via <leader>aa
      prompt_library = {
        ["DevOps"] = {
          strategy = "chat",
          description = "Senior DevOps (Terraform, AWS, Kubernetes, Python)",
          opts = { auto_submit = false },
          prompts = {
            {
              role = "system",
              content = "You are a senior DevOps engineer. You offer help with cloud technologies: Terraform, AWS, Kubernetes, Python. You answer with code examples when possible.",
            },
          },
        },
      },

      display = {
        chat = {
          window = {
            layout = "vertical",
            width = 0.35,
          },
        },
        inline = {
          diff = {
            enabled = true,
            priority = 130,
          },
        },
      },
    },
  },
}
