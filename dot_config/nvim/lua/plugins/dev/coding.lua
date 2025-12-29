-- Coding enhancement plugins
return {
  -- Auto pairs
  {
    "windwp/nvim-autopairs",
    event = "InsertEnter",
    opts = {
      check_ts = true,
      ts_config = {
        lua = { "string" },
        javascript = { "template_string" },
        java = false,
      },
    },
  },

  -- Comment plugin
  {
    "numToStr/Comment.nvim",
    event = "LazyFile",
    opts = {},
  },

  -- LSP kind icons
  {
    "onsails/lspkind.nvim",
    lazy = true,
  },

  -- DAP (Debug Adapter Protocol)
  {
    "mfussenegger/nvim-dap",
    dependencies = {
      {
        "rcarriga/nvim-dap-ui",
        dependencies = { "nvim-neotest/nvim-nio" },
        opts = {},
      },
      {
        "theHamsta/nvim-dap-virtual-text",
        opts = {},
      },
    },
    keys = {
      {
        "<leader>dt",
        function()
          require("dapui").toggle()
        end,
        desc = "Toggle DAP UI",
      },
      {
        "<leader>db",
        function()
          require("dap").toggle_breakpoint()
        end,
        desc = "Toggle breakpoint",
      },
      {
        "<leader>dc",
        function()
          require("dap").continue()
        end,
        desc = "Continue debugging",
      },
      {
        "<leader>dr",
        function()
          require("dapui").open({ reset = true })
        end,
        desc = "Reset DAP UI",
      },
      {
        "<leader>dso",
        function()
          require("dap").step_over()
        end,
        desc = "Step over",
      },
      {
        "<leader>dsi",
        function()
          require("dap").step_into()
        end,
        desc = "Step into",
      },
      {
        "<leader>dsx",
        function()
          require("dap").step_out()
        end,
        desc = "Step out",
      },
    },
    config = function()
      local dap = require("dap")
      local dapui = require("dapui")

      -- Setup dapui
      dapui.setup()

      -- Setup virtual text
      require("nvim-dap-virtual-text").setup()

      -- Breakpoint icons
      vim.fn.sign_define("DapBreakpoint", {
        text = "🔴",
        texthl = "DapBreakpoint",
        linehl = "DapBreakpoint",
        numhl = "DapBreakpoint",
      })

      -- Auto open/close dapui
      dap.listeners.after.event_initialized["dapui_config"] = function()
        dapui.open()
      end
      dap.listeners.before.event_terminated["dapui_config"] = function()
        dapui.close()
      end
      dap.listeners.before.event_exited["dapui_config"] = function()
        dapui.close()
      end
    end,
  },

  -- Code snapshot
  {
    "mistricky/codesnap.nvim",
    build = "make",
    cmd = { "CodeSnap", "CodeSnapSave" },
    keys = {
      { "<leader>cs", "<cmd>CodeSnap<cr>", mode = "v", desc = "Code snapshot to clipboard" },
      { "<leader>cS", "<cmd>CodeSnapSave<cr>", mode = "v", desc = "Code snapshot to file" },
    },
    opts = {
      save_path = "~/Pictures/CodeSnaps",
      has_breadcrumbs = true,
      bg_theme = "bamboo",
      watermark = "",
    },
  },
}
