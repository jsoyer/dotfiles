-- AI coding assistants
return {
  -- opencode.nvim: OpenCode CLI integration
  {
    "nickjvandyke/opencode.nvim",
    version = "*",
    config = function()
      vim.g.opencode_opts = {}
      vim.o.autoread = true
    end,
    keys = {
      {
        "<leader>ao",
        function() require("opencode").toggle() end,
        mode = { "n", "v" },
        desc = "OpenCode toggle",
      },
      {
        "<C-a>",
        function() require("opencode").ask("@this: ", { submit = true }) end,
        mode = "v",
        desc = "OpenCode ask (selection)",
      },
    },
  },

  -- copilot.lua: GitHub Copilot ghost-text completions
  {
    "zbirenbaum/copilot.lua",
    cmd = "Copilot",
    event = "InsertEnter",
    opts = {
      suggestion = {
        enabled = true,
        auto_trigger = true,
        keymap = {
          accept = "<M-l>",
          accept_word = "<M-k>",
          accept_line = "<M-j>",
          next = "<M-]>",
          prev = "<M-[>",
          dismiss = "<C-]>",
        },
      },
      panel = { enabled = false },
      filetypes = {
        markdown = true,
        yaml = true,
        ["."] = false,
      },
    },
  },

  -- avante.nvim: Cursor-style AI diff panel
  {
    "yetone/avante.nvim",
    event = "VeryLazy",
    build = "make",
    dependencies = {
      "nvim-treesitter/nvim-treesitter",
      "nvim-lua/plenary.nvim",
      "MunifTanjim/nui.nvim",
      "nvim-telescope/telescope.nvim",
    },
    opts = {
      provider = "claude",
      auto_suggestions_provider = "copilot",
      providers = {
        claude = {
          model = "claude-sonnet-4-6",
          extra_request_body = { max_tokens = 4096 },
        },
        openai = {
          model = "gpt-4o",
        },
        gemini = {
          model = "gemini-2.5-pro",
        },
      },
      selector = {
        provider = "telescope",
      },
      behaviour = {
        auto_suggestions = false,
        auto_set_keymaps = true,
      },
    },
  },

  -- minuet-ai.nvim: multi-provider as-you-type completions
  {
    "milanglacier/minuet-ai.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    event = "InsertEnter",
    opts = {
      provider = "openai_fim_compatible",
      notify = "warn",
      throttle = 1500,
      provider_options = {
        openai_fim_compatible = {
          api_key = "OLLAMA_API_KEY",
          name = "Ollama",
          end_point = "http://localhost:11434/v1/completions",
          model = "qwen2.5-coder:7b",
          optional = {
            max_tokens = 128,
            stop = { "\n\n" },
          },
        },
      },
      virtualtext = {
        auto_trigger_ft = {},
        keymap = {
          accept = "<A-a>",
          accept_line = "<A-e>",
          next = "<A-n>",
          prev = "<A-p>",
          dismiss = "<A-d>",
        },
      },
    },
  },

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
      -- Pick default adapter: API key first, then corresponding CLI, then ollama
      local function has_key(env) return vim.env[env] and vim.env[env] ~= "" end
      local function has_cli(cmd) return vim.fn.executable(cmd) == 1 end

      local default = "ollama"
      if     has_key("ANTHROPIC_API_KEY") then default = "anthropic"
      elseif has_cli("claude")            then default = "claude_code"
      elseif has_key("OPENAI_API_KEY")    then default = "openai"
      elseif has_cli("codex")             then default = "codex"
      elseif has_key("GEMINI_API_KEY")    then default = "gemini"
      elseif has_cli("gemini")            then default = "gemini_cli"
      elseif has_key("MISTRAL_API_KEY")   then default = "mistral"
      elseif has_cli("mistral-vibe")      then default = "mistral_vibe"
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
