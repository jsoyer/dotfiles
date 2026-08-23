# Nushell Config File
#
# version = "0.109.1"

# For more information on defining custom themes, see
# https://www.nushell.sh/book/coloring_and_theming.html
# And here is the theme collection
# https://github.com/nushell/nu_scripts/tree/main/themes
let dark_theme = {
    # color for nushell primitives
    separator: white
    leading_trailing_space_bg: { attr: n } # no fg, no bg, attr none effectively turns this off
    header: green_bold
    empty: blue
    # Closures can be used to choose colors for specific values.
    # The value (in this case, a bool) is piped into the closure.
    # eg) {|| if $in { 'light_cyan' } else { 'light_gray' } }
    bool: light_cyan
    int: white
    filesize: cyan
    duration: white
    date: purple
    range: white
    float: white
    string: white
    nothing: white
    binary: white
    cell-path: white
    row_index: green_bold
    record: white
    list: white
    block: white
    hints: dark_gray
    search_result: { bg: red fg: white }
    shape_and: purple_bold
    shape_binary: purple_bold
    shape_block: blue_bold
    shape_bool: light_cyan
    shape_closure: green_bold
    shape_custom: green
    shape_datetime: cyan_bold
    shape_directory: cyan
    shape_external: cyan
    shape_externalarg: green_bold
    shape_external_resolved: light_yellow_bold
    shape_filepath: cyan
    shape_flag: blue_bold
    shape_float: purple_bold
    # shapes are used to change the cli syntax highlighting
    shape_garbage: { fg: white bg: red attr: b}
    shape_glob_interpolation: cyan_bold
    shape_globpattern: cyan_bold
    shape_int: purple_bold
    shape_internalcall: cyan_bold
    shape_keyword: cyan_bold
    shape_list: cyan_bold
    shape_literal: blue
    shape_match_pattern: green
    shape_matching_brackets: { attr: u }
    shape_nothing: light_cyan
    shape_operator: yellow
    shape_or: purple_bold
    shape_pipe: purple_bold
    shape_range: yellow_bold
    shape_record: cyan_bold
    shape_redirection: purple_bold
    shape_signature: green_bold
    shape_string: green
    shape_string_interpolation: cyan_bold
    shape_table: blue_bold
    shape_variable: purple
    shape_vardecl: purple
    shape_raw_string: light_purple
}

let light_theme = {
    # color for nushell primitives
    separator: dark_gray
    leading_trailing_space_bg: { attr: n } # no fg, no bg, attr none effectively turns this off
    header: green_bold
    empty: blue
    # Closures can be used to choose colors for specific values.
    # The value (in this case, a bool) is piped into the closure.
    # eg) {|| if $in { 'dark_cyan' } else { 'dark_gray' } }
    bool: dark_cyan
    int: dark_gray
    filesize: cyan_bold
    duration: dark_gray
    date: purple
    range: dark_gray
    float: dark_gray
    string: dark_gray
    nothing: dark_gray
    binary: dark_gray
    cell-path: dark_gray
    row_index: green_bold
    record: dark_gray
    list: dark_gray
    block: dark_gray
    hints: dark_gray
    search_result: { fg: white bg: red }
    shape_and: purple_bold
    shape_binary: purple_bold
    shape_block: blue_bold
    shape_bool: light_cyan
    shape_closure: green_bold
    shape_custom: green
    shape_datetime: cyan_bold
    shape_directory: cyan
    shape_external: cyan
    shape_externalarg: green_bold
    shape_external_resolved: light_purple_bold
    shape_filepath: cyan
    shape_flag: blue_bold
    shape_float: purple_bold
    # shapes are used to change the cli syntax highlighting
    shape_garbage: { fg: white bg: red attr: b}
    shape_globpattern: cyan_bold
    shape_int: purple_bold
    shape_internalcall: cyan_bold
    shape_keyword: cyan_bold
    shape_list: cyan_bold
    shape_literal: blue
    shape_match_pattern: green
    shape_matching_brackets: { attr: u }
    shape_nothing: light_cyan
    shape_operator: yellow
    shape_or: purple_bold
    shape_pipe: purple_bold
    shape_range: yellow_bold
    shape_record: cyan_bold
    shape_redirection: purple_bold
    shape_signature: green_bold
    shape_string: green
    shape_string_interpolation: cyan_bold
    shape_table: blue_bold
    shape_variable: purple
    shape_vardecl: purple
    shape_raw_string: light_purple
}

$env.config = {
    show_banner: false

    ls: {
        use_ls_colors: true # use the LS_COLORS environment variable to colorize output
        clickable_links: true # enable or disable clickable links. Your terminal has to support links.
    }

    rm: {
        always_trash: false # always act as if -t was given. Can be overridden with -p
    }

    table: {
        mode: rounded # basic, compact, compact_double, light, thin, with_love, rounded, reinforced, heavy, none, other
        index_mode: always # "always" show indexes, "never" show indexes, "auto" = show indexes when a table has "index" column
        show_empty: true # show 'empty list' and 'empty record' placeholders for command output
        padding: { left: 1, right: 1 } # a left right padding of each column in a table
        trim: {
            methodology: wrapping # wrapping or truncating
            wrapping_try_keep_words: true # A strategy used by the 'wrapping' methodology
            truncating_suffix: "..." # A suffix used by the 'truncating' methodology
        }
        header_on_separator: false # show header text on separator/border line
        # abbreviated_row_count: 10 # limit data rows from top and bottom after reaching a set point
    }

    error_style: "fancy" # "fancy" or "plain" for screen reader-friendly error messages

    # datetime_format determines what a datetime rendered in the shell would look like.
    # Behavior without this configuration point will be to "humanize" the datetime display,
    # showing something like "a day ago."
    datetime_format: {
        # normal: '%a, %d %b %Y %H:%M:%S %z'    # shows up in displays of variables or other datetime's outside of tables
        # table: '%m/%d/%y %I:%M:%S%p'          # generally shows up in tabular outputs such as ls. commenting this out will change it to the default human readable datetime format
    }

    explore: {
        status_bar_background: { fg: "#1D1F21", bg: "#C4C9C6" },
        command_bar_text: { fg: "#C4C9C6" },
        highlight: { fg: "black", bg: "yellow" },
        status: {
            error: { fg: "white", bg: "red" },
            warn: {}
            info: {}
        },
        selected_cell: { bg: light_blue },
    }

    history: {
        max_size: 100_000 # Session has to be reloaded for this to take effect
        sync_on_enter: true # Enable to share history between multiple sessions, else you have to close the session to write history to file
        file_format: "plaintext" # "sqlite" or "plaintext"
        isolation: false # only available with sqlite file_format. true enables history isolation, false disables it. true will allow the history to be isolated to the current session using up/down arrows. false will allow the history to be shared across all sessions.
    }

    completions: {
        case_sensitive: false # set to true to enable case-sensitive completions
        quick: true    # set this to false to prevent auto-selecting completions when only one remains
        partial: true    # set this to false to prevent partial filling of the prompt
        algorithm: "prefix"    # prefix or fuzzy
        external: {
            enable: true # set to false to prevent nushell looking into $env.PATH to find more suggestions, `false` recommended for WSL users as this look up may be very slow
            max_results: 100 # setting it lower can improve completion performance at the cost of omitting some options
            completer: null # check 'carapace_completer' above as an example
        }
        use_ls_colors: true # set this to true to enable file/path/directory completions using LS_COLORS
    }

    # filesize configuration removed - not available in this Nushell version

    cursor_shape: {
        emacs: block # block, underscore, line, blink_block, blink_underscore, blink_line, inherit to skip setting cursor shape (line is the default)
        vi_insert: block # block, underscore, line, blink_block, blink_underscore, blink_line, inherit to skip setting cursor shape (block is the default)
        vi_normal: underscore # block, underscore, line, blink_block, blink_underscore, blink_line, inherit to skip setting cursor shape (underscore is the default)
    }

    color_config: $dark_theme # if you want a more interesting theme, you can replace the empty record with `$dark_theme`, `$light_theme` or another custom record
    footer_mode: 25 # always, never, number_of_rows, auto
    float_precision: 2 # the precision for displaying floats in tables
    buffer_editor: "" # command that will be used to edit the current line buffer with ctrl+o, if unset fallback to $env.EDITOR and $env.VISUAL
    use_ansi_coloring: true
    bracketed_paste: true # enable bracketed paste, currently useless on windows
    edit_mode: vi # emacs, vi
    shell_integration: {
        # osc2 abbreviates the path if in the home_dir, sets the tab/window title, shows the running command in the tab/window title
        osc2: true
        # osc7 is a way to communicate the path to the terminal, this is helpful for spawning new tabs in the same directory
        osc7: true
        # osc8 is also implemented as the deprecated setting ls.show_clickable_links, it shows clickable links in ls output if your terminal supports it. show_clickable_links is deprecated in favor of osc8
        osc8: true
        # osc9_9 is from ConEmu and is starting to get wider support. It's similar to osc7 in that it communicates the path to the terminal
        osc9_9: false
        # osc133 is several escapes invented by Final Term which include the supported ones below.
        # 133;A - Mark prompt start
        # 133;B - Mark prompt end
        # 133;C - Mark pre-execution
        # 133;D;exit - Mark execution finished with exit code
        # This is used to enable terminals to know where the prompt is, the command is, where the command finishes, and where the output of the command is
        osc133: true
        # osc633 is closely related to osc133 but only exists in visual studio code (vscode) and supports their shell integration features
        # 633;A - Mark prompt start
        # 633;B - Mark prompt end
        # 633;C - Mark pre-execution
        # 633;D;exit - Mark execution finished with exit code
        # 633;E - NOT IMPLEMENTED - Explicitly set the command line with an optional nonce
        # 633;P;Cwd=<path> - Mark the current working directory and communicate it to the terminal
        # and also helps with the run recent menu in vscode
        osc633: true
        # reset_application_mode is escape \x1b[?1l and was added to help ssh work better
        reset_application_mode: true
    }
    render_right_prompt_on_last_line: false # true or false to enable or disable right prompt to be rendered on last line of the prompt.
    use_kitty_protocol: false # enables keyboard enhancement protocol implemented by kitty console, only if your terminal support this.
    highlight_resolved_externals: false # true enables highlighting of external commands in the repl resolved by which.
    recursion_limit: 50 # the maximum number of times nushell allows recursion before stopping it

    plugins: {} # Per-plugin configuration. See https://www.nushell.sh/contributor-book/plugins.html#configuration.

    plugin_gc: {
        # Configuration for plugin garbage collection
        default: {
            enabled: true # true to enable stopping of inactive plugins
            stop_after: 10sec # how long to wait after a plugin is inactive to stop it
        }
        plugins: {
            # alternate configuration for specific plugins, by name, for example:
            #
            # gstat: {
            #     enabled: false
            # }
        }
    }

    hooks: {
        pre_prompt: [{ null }]
        pre_execution: [{ null }] # run before the repl input is run
        env_change: {
            PWD: [{|before, after| null }] # run if the PWD environment is different since the last repl input
        }
        display_output: "if (term size).columns >= 100 { table -e } else { table }" # run to display the output of a pipeline
        command_not_found: { null } # return an error message when a command is not found
    }

    menus: [
        # Configuration for default nushell menus
        # Note the lack of source parameter
        {
            name: completion_menu
            only_buffer_difference: false
            marker: "| "
            type: {
                layout: columnar
                columns: 4
                col_width: 20     # Optional value. If missing all the screen width is used to calculate column width
                col_padding: 2
            }
            style: {
                text: green
                selected_text: { attr: r }
                description_text: yellow
                match_text: { attr: u }
                selected_match_text: { attr: ur }
            }
        }
        {
            name: ide_completion_menu
            only_buffer_difference: false
            marker: "| "
            type: {
                layout: ide
                min_completion_width: 0,
                max_completion_width: 50,
                max_completion_height: 10, # will be limited by the available lines in the terminal
                padding: 0,
                border: true,
                cursor_offset: 0,
                description_mode: "prefer_right"
                min_description_width: 0
                max_description_width: 50
                max_description_height: 10
                description_offset: 1
                # If true, the cursor pos will be corrected, so the suggestions match up with the typed text
                #
                # C:\> str
                #      str join
                #      str trim
                #      str split
                correct_cursor_pos: false
            }
            style: {
                text: green
                selected_text: { attr: r }
                description_text: yellow
                match_text: { attr: u }
                selected_match_text: { attr: ur }
            }
        }
        {
            name: history_menu
            only_buffer_difference: true
            marker: "? "
            type: {
                layout: list
                page_size: 10
            }
            style: {
                text: green
                selected_text: green_reverse
                description_text: yellow
            }
        }
        {
            name: help_menu
            only_buffer_difference: true
            marker: "? "
            type: {
                layout: description
                columns: 4
                col_width: 20     # Optional value. If missing all the screen width is used to calculate column width
                col_padding: 2
                selection_rows: 4
                description_rows: 10
            }
            style: {
                text: green
                selected_text: green_reverse
                description_text: yellow
            }
        }
    ]

    keybindings: [
        {
            name: delete_one_word_backward
            modifier: alt
            keycode: backspace
            mode: [emacs, vi_normal, vi_insert]
            event: {edit: backspaceword}
        }
        {
            name: completion_menu
            modifier: none
            keycode: tab
            mode: [emacs vi_normal vi_insert]
            event: {
                until: [
                    { send: menu name: completion_menu }
                    { send: menunext }
                    { edit: complete }
                ]
            }
        }
        {
            name: ide_completion_menu
            modifier: control
            keycode: char_n
            mode: [emacs vi_normal vi_insert]
            event: {
                until: [
                    { send: menu name: ide_completion_menu }
                    { send: menunext }
                    { edit: complete }
                ]
            }
        }
        {
            name: history_menu
            modifier: control
            keycode: char_r
            mode: [emacs, vi_insert, vi_normal]
            event: { send: menu name: history_menu }
        }
        {
            name: help_menu
            modifier: none
            keycode: f1
            mode: [emacs, vi_insert, vi_normal]
            event: { send: menu name: help_menu }
        }
        {
            name: completion_previous_menu
            modifier: shift
            keycode: backtab
            mode: [emacs, vi_normal, vi_insert]
            event: { send: menuprevious }
        }
        {
            name: next_page_menu
            modifier: control
            keycode: char_x
            mode: emacs
            event: { send: menupagenext }
        }
        {
            name: undo_or_previous_page_menu
            modifier: control
            keycode: char_z
            mode: emacs
            event: {
                until: [
                    { send: menupageprevious }
                    { edit: undo }
                ]
            }
        }
        {
            name: escape
            modifier: none
            keycode: escape
            mode: [emacs, vi_normal, vi_insert]
            event: { send: esc }    # NOTE: does not appear to work
        }
        {
            name: cancel_command
            modifier: control
            keycode: char_c
            mode: [emacs, vi_normal, vi_insert]
            event: { send: ctrlc }
        }
        {
            name: quit_shell
            modifier: control
            keycode: char_d
            mode: [emacs, vi_normal, vi_insert]
            event: { send: ctrld }
        }
        {
            name: clear_screen
            modifier: control
            keycode: char_l
            mode: [emacs, vi_normal, vi_insert]
            event: { send: clearscreen }
        }
        {
            name: search_history
            modifier: control
            keycode: char_q
            mode: [emacs, vi_normal, vi_insert]
            event: { send: searchhistory }
        }
        {
            name: open_command_editor
            modifier: control
            keycode: char_o
            mode: [emacs, vi_normal, vi_insert]
            event: { send: openeditor }
        }
        {
            name: move_up
            modifier: none
            keycode: up
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: menuup }
                    { send: up }
                ]
            }
        }
        {
            name: move_down
            modifier: none
            keycode: down
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: menudown }
                    { send: down }
                ]
            }
        }
        {
            name: move_left
            modifier: none
            keycode: left
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: menuleft }
                    { send: left }
                ]
            }
        }
        {
            name: move_right_or_take_history_hint
            modifier: none
            keycode: right
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: historyhintcomplete }
                    { send: menuright }
                    { send: right }
                ]
            }
        }
        {
            name: move_one_word_left
            modifier: control
            keycode: left
            mode: [emacs, vi_normal, vi_insert]
            event: { edit: movewordleft }
        }
        {
            name: move_one_word_right_or_take_history_hint
            modifier: control
            keycode: right
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: historyhintwordcomplete }
                    { edit: movewordright }
                ]
            }
        }
        {
            name: move_to_line_start
            modifier: none
            keycode: home
            mode: [emacs, vi_normal, vi_insert]
            event: { edit: movetolinestart }
        }
        {
            name: move_to_line_start
            modifier: control
            keycode: char_a
            mode: [emacs, vi_normal, vi_insert]
            event: { edit: movetolinestart }
        }
        {
            name: move_to_line_end_or_take_history_hint
            modifier: none
            keycode: end
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: historyhintcomplete }
                    { edit: movetolineend }
                ]
            }
        }
        {
            name: move_to_line_end_or_take_history_hint
            modifier: control
            keycode: char_e
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: historyhintcomplete }
                    { edit: movetolineend }
                ]
            }
        }
        {
            name: move_to_line_start
            modifier: control
            keycode: home
            mode: [emacs, vi_normal, vi_insert]
            event: { edit: movetolinestart }
        }
        {
            name: move_to_line_end
            modifier: control
            keycode: end
            mode: [emacs, vi_normal, vi_insert]
            event: { edit: movetolineend }
        }
        {
            name: move_up
            modifier: control
            keycode: char_p
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: menuup }
                    { send: up }
                ]
            }
        }
        {
            name: move_down
            modifier: control
            keycode: char_t
            mode: [emacs, vi_normal, vi_insert]
            event: {
                until: [
                    { send: menudown }
                    { send: down }
                ]
            }
        }
        {
            name: delete_one_character_backward
            modifier: none
            keycode: backspace
            mode: [emacs, vi_insert]
            event: { edit: backspace }
        }
        {
            name: delete_one_word_backward
            modifier: control
            keycode: backspace
            mode: [emacs, vi_insert]
            event: { edit: backspaceword }
        }
        {
            name: delete_one_character_forward
            modifier: none
            keycode: delete
            mode: [emacs, vi_insert]
            event: { edit: delete }
        }
        {
            name: delete_one_character_forward
            modifier: control
            keycode: delete
            mode: [emacs, vi_insert]
            event: { edit: delete }
        }
        {
            name: delete_one_character_backward
            modifier: control
            keycode: char_h
            mode: [emacs, vi_insert]
            event: { edit: backspace }
        }
        {
            name: delete_one_word_backward
            modifier: control
            keycode: char_w
            mode: [emacs, vi_insert]
            event: { edit: backspaceword }
        }
        {
            name: move_left
            modifier: none
            keycode: backspace
            mode: vi_normal
            event: { edit: moveleft }
        }
        {
            name: newline_or_run_command
            modifier: none
            keycode: enter
            mode: emacs
            event: { send: enter }
        }
        {
            name: move_left
            modifier: control
            keycode: char_b
            mode: emacs
            event: {
                until: [
                    { send: menuleft }
                    { send: left }
                ]
            }
        }
        {
            name: move_right_or_take_history_hint
            modifier: control
            keycode: char_f
            mode: emacs
            event: {
                until: [
                    { send: historyhintcomplete }
                    { send: menuright }
                    { send: right }
                ]
            }
        }
        {
            name: redo_change
            modifier: control
            keycode: char_g
            mode: emacs
            event: { edit: redo }
        }
        {
            name: undo_change
            modifier: control
            keycode: char_z
            mode: emacs
            event: { edit: undo }
        }
        {
            name: paste_before
            modifier: control
            keycode: char_y
            mode: emacs
            event: { edit: pastecutbufferbefore }
        }
        {
            name: cut_word_left
            modifier: control
            keycode: char_w
            mode: emacs
            event: { edit: cutwordleft }
        }
        {
            name: cut_line_to_end
            modifier: control
            keycode: char_k
            mode: emacs
            event: { edit: cuttoend }
        }
        {
            name: cut_line_from_start
            modifier: control
            keycode: char_u
            mode: emacs
            event: { edit: cutfromstart }
        }
        {
            name: swap_graphemes
            modifier: control
            keycode: char_t
            mode: emacs
            event: { edit: swapgraphemes }
        }
        {
            name: move_one_word_left
            modifier: alt
            keycode: left
            mode: emacs
            event: { edit: movewordleft }
        }
        {
            name: move_one_word_right_or_take_history_hint
            modifier: alt
            keycode: right
            mode: emacs
            event: {
                until: [
                    { send: historyhintwordcomplete }
                    { edit: movewordright }
                ]
            }
        }
        {
            name: move_one_word_left
            modifier: alt
            keycode: char_b
            mode: emacs
            event: { edit: movewordleft }
        }
        {
            name: move_one_word_right_or_take_history_hint
            modifier: alt
            keycode: char_f
            mode: emacs
            event: {
                until: [
                    { send: historyhintwordcomplete }
                    { edit: movewordright }
                ]
            }
        }
        {
            name: delete_one_word_forward
            modifier: alt
            keycode: delete
            mode: emacs
            event: { edit: deleteword }
        }
        {
            name: delete_one_word_backward
            modifier: alt
            keycode: backspace
            mode: emacs
            event: { edit: backspaceword }
        }
        {
            name: delete_one_word_backward
            modifier: alt
            keycode: char_m
            mode: emacs
            event: { edit: backspaceword }
        }
        {
            name: cut_word_to_right
            modifier: alt
            keycode: char_d
            mode: emacs
            event: { edit: cutwordright }
        }
        {
            name: upper_case_word
            modifier: alt
            keycode: char_u
            mode: emacs
            event: { edit: uppercaseword }
        }
        {
            name: lower_case_word
            modifier: alt
            keycode: char_l
            mode: emacs
            event: { edit: lowercaseword }
        }
        {
            name: capitalize_char
            modifier: alt
            keycode: char_c
            mode: emacs
            event: { edit: capitalizechar }
        }
        # The following bindings with `*system` events require that Nushell has
        # been compiled with the `system-clipboard` feature.
        # This should be the case for Windows, macOS, and most Linux distributions
        # Not available for example on Android (termux)
        # If you want to use the system clipboard for visual selection or to
        # paste directly, uncomment the respective lines and replace the version
        # using the internal clipboard.
        {
            name: copy_selection
            modifier: control_shift
            keycode: char_c
            mode: emacs
            event: { edit: copyselection }
            # event: { edit: copyselectionsystem }
        }
        {
            name: cut_selection
            modifier: control_shift
            keycode: char_x
            mode: emacs
            event: { edit: cutselection }
            # event: { edit: cutselectionsystem }
        }
        # {
        #     name: paste_system
        #     modifier: control_shift
        #     keycode: char_v
        #     mode: emacs
        #     event: { edit: pastesystem }
        # }
        {
            name: select_all
            modifier: control_shift
            keycode: char_a
            mode: emacs
            event: { edit: selectall }
        }
    ]
}

# ============================================================================
# Custom functions
# ============================================================================
def --env cx [arg] {
    cd $arg
    ls -l
}

def --env fcd [] {
    let dir = (fd --type d --hidden --exclude .git | fzf)
    if ($dir | is-not-empty) {
        cd $dir
        ls -l
    }
}

def f [] {
    let file = (fd --type f --hidden --exclude .git | fzf)
    if ($file | is-not-empty) {
        if (which pbcopy | is-not-empty) {
            $file | pbcopy
        } else if (which wl-copy | is-not-empty) {
            $file | wl-copy
        } else if (which xclip | is-not-empty) {
            $file | xclip -selection clipboard
        }
        print $"Copied to clipboard: ($file)"
    }
}

def fv [] {
    let file = (fd --type f --hidden --exclude .git | fzf)
    if ($file | is-not-empty) {
        ^nvim $file
    }
}

def ff [] {
    aerospace list-windows --all | fzf --bind 'enter:execute(bash -c "aerospace focus --window-id {1}")+abort'
}

# ============================================================================
# Modern CLI tool replacements
# ============================================================================
alias vim = nvim
alias v = nvim
alias la = tree
alias cat = bat
alias catp = bat --plain
alias http = xh
alias as = aerospace
alias asr = atuin scripts run

# Eza (modern ls replacement)
# Note: shadowing nushell's built-in ls with eza requires --wrapped
def --wrapped ls [...args: string] { ^eza --color=always --icons ...$args }
alias l = eza -l --icons --git -a
alias ll = eza -l --color=always --icons --git -a
alias lt = eza --tree --level=2 --long --icons --git
alias ltree = eza --tree --level=2 --icons --git
alias zl = eza -lagX --icons --color=always

# ============================================================================
# System
# ============================================================================
alias cl = clear
alias bcask = brew cask
alias tbx = /usr/bin/toolbox run zsh

# ============================================================================
# Navigation
# ============================================================================
alias .. = cd ..
alias ... = cd ../..
alias .... = cd ../../..
alias ..... = cd ../../../..
alias ...... = cd ../../../../..

# ============================================================================
# Git
# ============================================================================
alias gc = git commit -m
alias gca = git commit -a -m
alias gp = git push origin HEAD
alias gpu = git pull origin
alias gst = git status
alias glog = git log --graph --topo-order --pretty='%w(100,0,6)%C(yellow)%h%C(bold)%C(black)%d %C(cyan)%ar %C(green)%an%n%C(bold)%C(white)%s %N' --abbrev-commit
alias gdiff = git diff
alias gco = git checkout
alias gb = git branch
alias gba = git branch -a
alias gadd = git add
alias ga = git add -p
alias gcoall = git checkout -- .
alias gr = git remote
alias gre = git reset

# ============================================================================
# Git (Additions)
# ============================================================================
alias gs = git status -s
alias gsw = git switch
alias gswc = git switch -c
alias grs = git restore
alias grbi = git rebase -i
alias gcl = git clone

# ============================================================================
# Docker / Podman
# ============================================================================
alias dco = docker compose
alias dl = docker ps -l -q

# docker-compose -> docker compose (alias for compatibility)
alias docker-compose = ^docker compose

# Podman Compose
alias podman-compose = ^podman compose

# ============================================================================
# Docker / Podman Compose
# ============================================================================
# Cached container runtime detection (avoids forking docker info on every call)
def _container_runtime [] {
    if ($env._CONTAINER_RUNTIME? | default "" | is-not-empty) {
        return ($env._CONTAINER_RUNTIME? | default "")
    }
    let rt = if (which docker | is-not-empty) and (^docker info | complete).exit_code == 0 {
        "docker"
    } else if (which podman | is-not-empty) and (^podman info | complete).exit_code == 0 {
        "podman"
    } else {
        ""
    }
    $env._CONTAINER_RUNTIME = $rt
    $rt
}

# Docker/Podman aliases — top-level (def/alias inside if not visible in Nushell)
def dps [] { ^(_container_runtime) ps --format 'table {{.Names}}\t{{.ID}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}' }
def dpsa [] { ^(_container_runtime) container ls -a --format 'table {{.Names}}\t{{.ID}}\t{{.State}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}' }
def dcpl [] { ^(_container_runtime) compose pull }
def dcup [] { ^(_container_runtime) compose up -d }
def dcl [...args: string] { ^(_container_runtime) compose logs -f ...$args }
def dcd [] { ^(_container_runtime) compose down }
def dcr [] { ^(_container_runtime) compose restart }
def dcp [] { ^(_container_runtime) compose ps }
def dce [...args: string] { ^(_container_runtime) compose exec ...$args }
def dcb [] { ^(_container_runtime) compose build }

def dcua [base?: string] {
    let base_dir = ($base | default ".")
    let runtime = (_container_runtime)

    if ($runtime | is-empty) {
        print "⚠️ No container runtime found."
        return
    }

    mut updated = 0

    for dir in (ls $base_dir | where type == dir | get name) {
        let compose_file = if ($dir | path join "docker-compose.yml" | path exists) {
            $dir | path join "docker-compose.yml"
        } else if ($dir | path join "compose.yml" | path exists) {
            $dir | path join "compose.yml"
        } else {
            continue
        }

        let name = ($dir | path basename)
        print $"📥 ($name)"

        let before = (^$runtime compose -f $compose_file images -q | complete | get stdout | str trim)
        ^$runtime compose -f $compose_file pull --quiet out+err>| complete
        let after = (^$runtime compose -f $compose_file images -q | complete | get stdout | str trim)

        if $before != $after {
            print "  🔄 Updated, restarting..."
            ^$runtime compose -f $compose_file up -d --quiet-pull
            $updated = $updated + 1
        } else {
            print "  ✅ Up to date"
        }
    }

    print "🧹 Pruning dangling images..."
    ^$runtime image prune -f --filter "dangling=true" out+err>| complete
    print $"✨ Done. ($updated) project\(s\) updated."
}

# ============================================================================
# Kubernetes
# ============================================================================
alias k = kubectl
alias ka = kubectl apply -f
alias kg = kubectl get
alias kd = kubectl describe
alias kdel = kubectl delete
alias kl = kubectl logs -f
alias kgpo = kubectl get pod
alias kgd = kubectl get deployments
alias kc = kubectx
alias kns = kubens
alias ke = kubectl exec -it
alias kcns = kubectl config set-context --current --namespace

# ============================================================================
# Security & Pentesting tools — top-level (fail gracefully if not installed)
# ============================================================================
alias gobust = gobuster dir --wordlist ~/security/wordlists/diccnoext.txt --wildcard --url
alias server = python -m http.server 4445
alias tunnel = ngrok http 4445
alias fuzz = ffuf -w ~/hacking/SecLists/content_discovery_all.txt -mc all -u
alias nm = nmap -sC -sV -oN nmap

# ============================================================================
# Homebrew (via breww wrapper) + Mac App Store (via masw)
# ============================================================================
alias b = breww
def mas [...args: string] { ^masw ...$args }
alias bi = breww install
alias bu = breww update
alias bup = breww upgrade
alias bcu = breww cu -a
alias bs = breww search
alias bl = breww list
alias brm = breww uninstall
alias bci = breww cleanup
# Aggressive reclaim: every cached download + the download cache itself.
# `bci` keeps Homebrew's 120-day retention; this one does not.
alias bcp = brew cleanup --prune=all -s
alias bcpn = brew cleanup --prune=all -s --dry-run
alias binfo = breww info
alias bdo = breww doctor
alias bdep = brew-deprecated

# ============================================================================
# Chezmoi
# ============================================================================
alias c = chezmoi
alias cdiff = chezmoi diff
alias cedit = chezmoi edit
alias cadd = chezmoi add
alias creadd = chezmoi re-add
alias cs = chezmoi status
alias ccd = chezmoi cd

# Auto-update monitoring
def cmstatus [] {
    let path = ($env.HOME | path join ".cache" "chezmoi-autoupdate" "status.json")
    if ($path | path exists) {
        open $path
    } else {
        print "No status yet"
    }
}

def cmlog [] {
    let path = ($env.HOME | path join ".cache" "chezmoi-autoupdate" "last-run.log")
    if ($path | path exists) {
        open $path
    } else {
        print "No logs yet"
    }
}

def cmdiff [] {
    if (which delta | is-not-empty) {
        ^chezmoi diff | ^delta
    } else {
        ^chezmoi diff
    }
}

def cmchangelog [] {
    ^git -C ($env.HOME | path join ".local" "share" "chezmoi") log --oneline -20
}

# Chezmoi apply/update with verbose mode
def ca [...args: string] {
    ^chezmoi apply -v ...$args
}

def cu [...args: string] {
    ^chezmoi update -v ...$args
}

# Chezmoi purge (remove chezmoi source + config, keep deployed files)
def cpurge [] {
    print "WARNING: This will remove chezmoi source directory and config."
    print "  - Deletes: ~/.local/share/chezmoi (source repo)"
    print "  - Deletes: ~/.config/chezmoi/chezmoi.toml (config)"
    print "  - Keeps:   All deployed dotfiles in your home directory"
    print ""
    let reply = (input "Are you sure? (y/N) ")
    if $reply == "y" or $reply == "Y" {
        ^chezmoi purge --force
        print "chezmoi purged."
    } else {
        print "Aborted."
    }
}

# Monitoring & diagnostics (scripts in ~/.local/bin/)
def cmhealth [...args: string] { ^cmhealth ...$args }
def cmbench [...args: string] { ^cmbench ...$args }
def cmaudit [...args: string] { ^cmaudit ...$args }
def cmaudit-packages [...args: string] { ^cmaudit-packages ...$args }
def cmrollback [...args: string] { ^cmrollback ...$args }
def cmreload [...args: string] { ^cmreload ...$args }
def cmwho [] { ^cmwho }
def cminventory [] { ^cminventory }

# Security & tools
def mcp-health [] { ^mcp-health }
def secret-age [...args: string] { ^secret-age ...$args }
def config-search [...args: string] { ^config-search ...$args }
def zsh-profiler [] { ^zsh-profiler }
def chezmoi-state-backup [...args: string] { ^chezmoi-state-backup ...$args }

# Chezmoi destroy (purge + remove ALL managed files)
def cdestroy [] {
    print "DANGER: This will remove chezmoi AND all managed dotfiles!"
    print "  - Deletes: ~/.local/share/chezmoi (source repo)"
    print "  - Deletes: ~/.config/chezmoi/chezmoi.toml (config)"
    print "  - Deletes: ALL files managed by chezmoi in your home"
    print ""
    let reply = (input "Type 'destroy' to confirm: ")
    if $reply == "destroy" {
        ^chezmoi destroy --force
        print "chezmoi destroyed. All managed files removed."
    } else {
        print "Aborted."
    }
}

def sysup [] {
    let os = (^uname | str trim)

    match $os {
        "Darwin" => {
            bup
            bcu
            if (which mas | is-not-empty) {
                print "📱 Updating App Store apps..."
                ^mas upgrade
            }
            # bup/bcu upgrade but never reclaim: do it explicitly.
            if (which brew | is-not-empty) {
                print "🍺 Cleaning up Homebrew cache..."
                ^brew cleanup --prune=all -s
            }
        }
        "Linux" => {
            let mp = ($env.MACHINE_PROFILE? | default "")
            match $mp {
                "rpi" | "ubuntu-desktop" | "ubuntu-server" | "debian" => {
                    print "📦 Updating apt packages..."
                    ^sudo apt-get update
                    ^sudo apt-get dist-upgrade -y
                    ^sudo apt-get autoremove -y
                }
                "arch-desktop" | "arch-server" | "omarchy" => {
                    print "📦 Updating pacman packages..."
                    ^sudo pacman -Syu --noconfirm
                    if (which yay | is-not-empty) {
                        print "📦 Updating AUR packages..."
                        ^yay -Sua --noconfirm
                    }
                }
                "fedora-desktop" | "fedora-server" | "toolbox" => {
                    print "📦 Updating dnf packages..."
                    ^sudo dnf upgrade --refresh -y
                }
                "fedora-atomic" => {
                    print "🔒 Updating Fedora Atomic..."
                    ^rpm-ostree upgrade
                }
                _ => { }
            }

            if (which flatpak | is-not-empty) {
                print "📦 Updating Flatpak apps..."
                # Split by scope: a bare `flatpak update` also targets
                # system-scope installs, and polkit refuses a non-interactive
                # deploy for a normal user ("Deploy not allowed for user"),
                # which makes the whole command exit non-zero.
                (^flatpak update --user -y) | complete | ignore
                let _sys = (^flatpak list --system --columns=application | complete)
                if ($_sys.exit_code == 0 and ($_sys.stdout | str trim | is-not-empty)) {
                    (^sudo flatpak update --system -y) | complete | ignore
                }
            }

            if (which brew | is-not-empty) {
                print "🍺 Updating Linuxbrew packages..."
                ^brew update
                ^brew upgrade
                # --prune=all removes ALL cached downloads (not just >120 days),
                # -s clears the download cache itself.
                ^brew cleanup --prune=all -s
            }

            update-ai
        }
        _ => { }
    }
}

# Update CLI AI tools (claude-code, copilot-cli, codex)
def update-ai [] {
    print "🤖 Updating CLI AI tools..."
    if (which claude | is-not-empty) {
        print "  🤖 Updating Claude Code..."
        try { ^claude update } catch { }
    }
    if (which copilot-cli | is-not-empty) {
        print "  🤖 Updating Copilot CLI..."
        try { curl -fsSL https://gh.io/copilot-install | bash } catch { }
    }
    if (which codex | is-not-empty) {
        print "  🤖 Updating Codex CLI..."
        if (which npm | is-not-empty) {
            try { ^npm update -g @openai/codex } catch { }
        }
    }
}

# Chezmoi update + package updates
def cup [...args: string] {
    ^chezmoi update -v ...$args
    sysup
    dcua $env.HOME
    print "✅ Update complete!"
}

# Orca (stably.ai) cask upgrade
def orca-update [] {
    ^brew upgrade --cask stablyai/orca/orca
}

# ============================================================================
# Jujutsu (jj)
# ============================================================================
alias j = jj
alias js = jj st
alias jl = jj log -r 'all()'
alias jd = jj diff
alias jn = jj new
alias jui = jjui
alias jundo = jj undo
alias jp = jj git push
alias jf = jj git fetch

# ============================================================================
# Tmux
# ============================================================================
alias t = tmux
alias ta = tmux attach -t
alias tl = tmux list-sessions
alias tk = tmux kill-session -t
alias tns = tmux new-session -s

# ============================================================================
# lazygit / lazydocker
# ============================================================================
alias lg = lazygit
alias ld = lazydocker

# ============================================================================
# Systemd (Linux only — commands will fail gracefully on macOS)
# ============================================================================
alias sc = sudo systemctl
alias scs = sudo systemctl status
alias scr = sudo systemctl restart
alias sce = sudo systemctl enable --now
alias jf = journalctl -fu

# ============================================================================
# Tailscale
# ============================================================================
alias ts = tailscale
alias tss = tailscale status
alias tsu = sudo tailscale up
alias tsd = sudo tailscale down
alias tssh = tailscale ssh
alias tsip = tailscale ip -4
alias tsping = tailscale ping
def tsnet [] { ^tailscale status --json | from json | get Peer | transpose k v | get v | each { |r| { name: $r.HostName, ip: ($r.TailscaleIPs | first), status: (if $r.Online { "connected" } else { "disconnected" }) } } | sort-by name }

# ============================================================================
# Disk / System
# ============================================================================
# ports: ss on Linux, lsof on macOS
def ports [] {
    if (^uname | str trim) == "Linux" {
        ^sudo ss -tlnp
    } else {
        ^lsof -iTCP -sTCP:LISTEN -n -P
    }
}
def myip [] { ^curl -s ifconfig.me }
def path [] { $env.PATH }

# ============================================================================
# Markdown (glow)
# ============================================================================
alias md = glow

# ============================================================================
# Search (ripgrep / fd)
# ============================================================================
alias rgf = rg --files-with-matches
alias rgi = rg --ignore-case
alias fdf = fd --type f
alias fdd = fd --type d

# ============================================================================
# Python (uv / poetry / venv)
# ============================================================================
# uv
alias uvi = uv init
alias uva = uv add
alias uvr = uv run
alias uvs = uv sync
alias uvp = uv pip
alias uvpi = uv pip install
alias uvvenv = uv venv

# poetry
alias po = poetry
alias poi = poetry install
alias poa = poetry add
alias por = poetry run
alias pos = poetry shell
alias pou = poetry update
alias pol = poetry lock

# venv shortcuts
def venv [dir: string = ".venv"] { ^uv venv $dir }
def --env activate [dir: string = ".venv"] {
    let bin_path = ($dir | path join "bin" | path expand)
    if ($bin_path | path exists) {
        $env.PATH = ($env.PATH | prepend $bin_path)
        $env.VIRTUAL_ENV = ($dir | path expand)
    } else {
        print $"No virtualenv found at ($dir)/bin"
    }
}

# ============================================================================
# Misc
# ============================================================================
def --env mkd [...args: string] {
    mkdir ...$args
    cd ($args | last)
}

# ============================================================================
# Claude Code
# ============================================================================
alias cc = claude --dangerously-skip-permissions
alias ccc = claude --dangerously-skip-permissions -c
alias cco = claude --model opus
alias ccs = claude --model sonnet
alias cch = claude --model haiku

# Claude Context Manager
alias cctx = claude-context

# ============================================================================
# fdupes (duplicate file finder)
# ============================================================================
alias dup = fdupes -r
alias dupsize = fdupes -rS
alias dupsum = fdupes -rm

def dupdel [...args: string] {
    let target = if ($args | is-empty) { "." } else { $args | str join " " }
    print $"WARNING: this will DELETE duplicate files \(keeping one copy\) in: ($target)"
    let reply = (input "Continue? (y/N) ")
    if $reply == "y" or $reply == "Y" {
        if ($args | is-empty) {
            ^fdupes -rdN "."
        } else {
            ^fdupes -rdN ...$args
        }
    } else {
        print "Aborted."
    }
}

# ============================================================================
# Sync local SSH config to 1Password (macOS only)
# ============================================================================
def ssh-sync [] {
    op document edit --vault "Private" "SSH Config" $"($nu.home-dir)/.ssh/config"
    print "SSH config synced to 1Password"
}

# ============================================================================
# SSH wrapper for Kitty kitten ssh
# ============================================================================
def --wrapped ssh [...args: string] {
    if $env.TERM == "xterm-kitty" {
        kitten ssh ...$args
    } else {
        ^ssh ...$args
    }
}
def sshpw [...args: string] { ^ssh -o PreferredAuthentications=password ...$args }

# ============================================================================
# Ruby Configuration
# ============================================================================
let ruby_ver = "3.4.0"
let gem_home = ($nu.home-dir | path join ".gem" "ruby" $ruby_ver)
let gem_bin = ($gem_home | path join "bin")

# Set GEM paths
$env.GEM_HOME = $gem_home
$env.GEM_PATH = $gem_home

# Add gem bin to PATH if it exists
if ($gem_bin | path exists) {
  $env.PATH = ($env.PATH | prepend $gem_bin)
}

# ============================================================================
# Integrations (sourced from cache generated in env.nu)
# ============================================================================
source ~/.cache/starship/init.nu
$env._ZO_DOCTOR = "0"  # silence zoxide init doctor check
source ~/.cache/zoxide/init.nu
source ~/.cache/carapace/init.nu

# =============================================================================
# Package manager wrappers
# =============================================================================
def apt [...args: string] {
    let mp = ($env.MACHINE_PROFILE? | default "")
    if ($mp == "rpi") or ($mp | str starts-with "ubuntu") or ($mp == "debian") {
        ^aptw ...$args
    } else {
        ^apt ...$args
    }
}

def dnf [...args: string] {
    let mp = ($env.MACHINE_PROFILE? | default "")
    if ($mp == "fedora-desktop") or ($mp == "fedora-server") {
        ^dnfw ...$args
    } else {
        ^dnf ...$args
    }
}

def yum [...args: string] {
    let mp = ($env.MACHINE_PROFILE? | default "")
    if ($mp == "fedora-desktop") or ($mp == "fedora-server") {
        ^dnfw ...$args
    } else {
        ^yum ...$args
    }
}

def pacman [...args: string] {
    let mp = ($env.MACHINE_PROFILE? | default "")
    if ($mp | str starts-with "arch-") {
        ^pacmanw ...$args
    } else {
        ^pacman ...$args
    }
}

def yay [...args: string] {
    let mp = ($env.MACHINE_PROFILE? | default "")
    if ($mp == "arch-desktop") {
        ^yayw ...$args
    } else {
        ^yay ...$args
    }
}

# Ubuntu: snap → snapw
def snap [...args: string] {
    let mp = ($env.MACHINE_PROFILE? | default "")
    if ($mp | str starts-with "ubuntu") {
        ^snapw ...$args
    } else {
        ^snap ...$args
    }
}

# Fedora Atomic: rpm-ostree → ostreew
# (nushell does not support hyphens in def names; use an alias instead)
alias "rpm-ostree" = ostreew

# ============================================================================
# Self-hosted agent stacks (moshi / orca / cursor / herdr)
# ============================================================================
# Installation is MANUAL and explicit: chezmoi only drops the units and the
# scripts, nothing is enabled automatically. These aliases are the entry point.
# Details: ~/.local/bin/README.md, "Self-hosted Agent Stacks".

alias asvc = agentsvc
alias asvcs = agentsvc status
alias asvcu = agentsvc update

# --- Moshi (mobile terminal) — Linux + macOS --------------------------------
alias "moshi-install" = moshi-setup
alias mhs = moshi-setup --status
alias mhu = update-moshi

# config.nu is not a chezmoi template: branch on the OS at runtime instead.
def mhl [] {
    if $nu.os-info.name == "macos" {
        ^tail -f $"($nu.home-path)/Library/Logs/moshi-hook.log"
    } else {
        ^journalctl --user -u moshi-hook.service -f
    }
}

def mhr [] {
    if $nu.os-info.name == "macos" {
        let uid = (^id -u | str trim)
        ^launchctl kickstart -k $"gui/($uid)/com.jsoyer.moshi-hook"
    } else {
        ^systemctl --user restart moshi-hook.service
    }
}

# --- Orca (headless runtime) — Linux only, system scope ---------------------
alias "orca-install" = orca-setup
alias ov = orca-version
alias os = orca-setup --status
alias ol = journalctl -u orca-serve.service -f
alias orr = sudo systemctl restart orca-serve.service
alias ogui = orca-gui

# --- Cursor (private worker) — Linux only -----------------------------------
alias "cursor-install" = cursor-setup
alias cws = cursor-setup --status
alias cwl = journalctl --user -u cursor-worker.service -f
alias cwr = systemctl --user restart cursor-worker.service
alias cwu = update-cursor-agent

# --- herdr (multiplexer) — update timer only --------------------------------
alias hu = update-herdr
alias hs = herdr status server
alias hl = journalctl --user -u herdr-update.service -f

source ~/.cache/atuin/init.nu
