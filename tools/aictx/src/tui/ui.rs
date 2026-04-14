use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Tabs},
    Frame,
};

use super::app::{App, PreviewAction, ResourceTab};
use crate::doctor;
use crate::plugins::Origin;

pub fn draw(frame: &mut Frame, app: &App) {
    let area = frame.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // header
            Constraint::Length(3), // CLI tabs
            Constraint::Length(3), // resource tabs
            Constraint::Min(10),   // content
            Constraint::Length(3), // footer
        ])
        .split(area);

    draw_header(frame, app, chunks[0]);
    draw_cli_tabs(frame, app, chunks[1]);
    draw_resource_tabs(frame, app, chunks[2]);
    draw_content(frame, app, chunks[3]);
    draw_footer(frame, app, chunks[4]);

    if app.global_search_mode {
        draw_global_search(frame, app, chunks[3]);
    } else if app.preview_mode {
        draw_preview(frame, app, chunks[3]);
    } else if app.cli_toggle_mode {
        draw_cli_toggle(frame, app, chunks[3]);
    } else if app.profile_mode {
        draw_profile_selector(frame, app, chunks[3]);
    }
}

fn draw_header(frame: &mut Frame, app: &App, area: Rect) {
    let detected: Vec<String> = app
        .fingerprint
        .languages
        .iter()
        .take(5)
        .map(|l| l.name.clone())
        .collect();

    let header_text = format!(
        " AI Context Manager  {}  Detected: {}",
        app.project_name,
        if detected.is_empty() {
            "(empty project)".to_string()
        } else {
            detected.join(", ")
        }
    );

    let header = Paragraph::new(header_text)
        .style(
            Style::default()
                .fg(app.theme.blue)
                .add_modifier(Modifier::BOLD),
        )
        .block(
            Block::default()
                .borders(Borders::BOTTOM)
                .border_style(Style::default().fg(app.theme.surface)),
        );

    frame.render_widget(header, area);
}

fn draw_cli_tabs(frame: &mut Frame, app: &App, area: Rect) {
    let tab_titles: Vec<Line> = app
        .cli_tabs
        .iter()
        .map(|cli| {
            // Count total enabled across all resource tabs for this CLI
            let total_enabled: usize = cli
                .resource_tabs
                .iter()
                .filter_map(|rt| app.items.get(&(cli.cli_name.clone(), *rt)))
                .flat_map(|items| items.iter())
                .filter(|i| i.enabled)
                .count();
            Line::from(format!(
                " {} ({}) ",
                capitalize(&cli.cli_name),
                total_enabled
            ))
        })
        .collect();

    let tabs = Tabs::new(tab_titles)
        .select(app.active_cli_idx)
        .style(Style::default().fg(app.theme.subtext))
        .highlight_style(
            Style::default()
                .fg(app.theme.mauve)
                .add_modifier(Modifier::BOLD)
                .add_modifier(Modifier::UNDERLINED),
        )
        .divider(" | ");

    frame.render_widget(tabs, area);
}

fn draw_resource_tabs(frame: &mut Frame, app: &App, area: Rect) {
    if app.cli_tabs.is_empty() {
        return;
    }
    let cli = app.active_cli();
    let match_counts = app.filter_match_counts();

    let tab_titles: Vec<Line> = cli
        .resource_tabs
        .iter()
        .map(|rt| {
            let items = app.items.get(&(cli.cli_name.clone(), *rt));
            let enabled = items
                .map(|v| v.iter().filter(|i| i.enabled).count())
                .unwrap_or(0);
            let total = items.map(|v| v.len()).unwrap_or(0);
            let count_str = if !app.filter.is_empty() {
                match_counts
                    .iter()
                    .find(|(t, _)| t == rt)
                    .map(|(_, c)| format!(" ({})", c))
                    .unwrap_or_default()
            } else {
                String::new()
            };
            Line::from(format!(
                " {} {}/{}{} ",
                rt.label(),
                enabled,
                total,
                count_str
            ))
        })
        .collect();

    let tabs = Tabs::new(tab_titles)
        .select(cli.active_resource_idx)
        .style(Style::default().fg(app.theme.subtext))
        .highlight_style(
            Style::default()
                .fg(app.theme.blue)
                .add_modifier(Modifier::BOLD)
                .add_modifier(Modifier::UNDERLINED),
        )
        .divider(" | ");

    frame.render_widget(tabs, area);
}

fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(c) => c.to_uppercase().collect::<String>() + chars.as_str(),
    }
}

fn status_indicator(
    item: &super::app::ToggleItem,
    theme: &crate::theme::Theme,
) -> (&'static str, Style) {
    if item.enabled {
        ("🟢 installed", Style::default().fg(theme.green))
    } else if item.available {
        ("🟡 available", Style::default().fg(theme.yellow))
    } else {
        ("🔵 remote", Style::default().fg(theme.peach))
    }
}

fn source_indicator(
    item: &super::app::ToggleItem,
    theme: &crate::theme::Theme,
) -> (&'static str, Style) {
    match item.origin {
        Origin::Local => (
            "L",
            Style::default()
                .fg(theme.green)
                .add_modifier(Modifier::BOLD),
        ),
        Origin::Remote => (
            "R",
            Style::default()
                .fg(theme.peach)
                .add_modifier(Modifier::BOLD),
        ),
    }
}

fn symlink_indicator(
    item: &super::app::ToggleItem,
    theme: &crate::theme::Theme,
) -> (&'static str, Style) {
    if item.enabled {
        ("✔", Style::default().fg(theme.green))
    } else {
        ("✖", Style::default().fg(theme.overlay))
    }
}

fn draw_content(frame: &mut Frame, app: &App, area: Rect) {
    // If filtering, split area: content + filter bar
    let (content_area, filter_area) = if app.filtering || !app.filter.is_empty() {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Min(5), Constraint::Length(1)])
            .split(area);
        (chunks[0], Some(chunks[1]))
    } else {
        (area, None)
    };

    let filtered = app.filtered_items();
    let total_items = filtered.len();

    let visible_items: Vec<_> = filtered
        .iter()
        .skip(app.scroll_offset)
        .take(app.visible_height)
        .collect();

    let items: Vec<ListItem> = visible_items
        .iter()
        .enumerate()
        .map(|(visible_idx, (_, item))| {
            let display_idx = visible_idx + app.scroll_offset;
            let is_selected = display_idx == app.cursor;

            // Checkbox: green bold [x] for active, mauve [~] for suggested, dim [ ] for inactive
            let (checkbox_str, checkbox_style) = if item.enabled {
                (
                    "[x]",
                    Style::default()
                        .fg(app.theme.green)
                        .add_modifier(Modifier::BOLD),
                )
            } else if item.suggested {
                ("[~]", Style::default().fg(app.theme.mauve))
            } else {
                ("[ ]", Style::default().fg(app.theme.overlay))
            };

            // Name: white for active, mauve for suggested, dim for inactive
            // Blue+bold override when cursor is on it
            let name_style = if is_selected {
                Style::default()
                    .fg(app.theme.blue)
                    .add_modifier(Modifier::BOLD)
            } else if item.enabled {
                Style::default().fg(app.theme.text)
            } else if item.suggested {
                Style::default().fg(app.theme.subtext)
            } else {
                Style::default().fg(app.theme.overlay)
            };

            let (status_label, status_style) = status_indicator(item, &app.theme);
            let (source_label, source_style) = source_indicator(item, &app.theme);
            let (link_label, link_style) = symlink_indicator(item, &app.theme);

            // CLI indicators for skills
            let cli_indicators = if !app.cli_tabs.is_empty()
                && app.active_cli().active_resource() == ResourceTab::Skills
            {
                let active_clis = app.cli_active_map.get(&item.name);
                let mut spans = Vec::new();
                for ct in &app.cli_tabs {
                    let initial = ct
                        .cli_name
                        .chars()
                        .next()
                        .unwrap_or('?')
                        .to_uppercase()
                        .next()
                        .unwrap_or('?');
                    let is_active_in_cli = active_clis
                        .map(|v| v.contains(&ct.cli_name))
                        .unwrap_or(false);
                    if is_active_in_cli {
                        spans.push(Span::styled(
                            format!("[{}]", initial),
                            Style::default().fg(app.theme.teal),
                        ));
                    }
                }
                if !spans.is_empty() {
                    spans.insert(0, Span::raw(" "));
                }
                spans
            } else {
                Vec::new()
            };

            // Score bar only if score > 0
            let score_spans = if item.score > 0.0 {
                let bar = score_bar(item.score);
                let tier = confidence_tier(item.score);
                vec![
                    Span::styled(
                        format!(" {} ", bar),
                        Style::default().fg(score_color(item.score, &app.theme)),
                    ),
                    Span::styled(
                        format!("{:<5}", tier),
                        Style::default().fg(tier_color(item.score, &app.theme)),
                    ),
                ]
            } else {
                vec![Span::raw("                  ")]
            };

            let is_pinned = app.pinned.contains(&item.name);
            let pin_prefix = if is_pinned { "* " } else { "  " };
            let pin_style = Style::default()
                .fg(app.theme.yellow)
                .add_modifier(Modifier::BOLD);

            let mut line_spans = vec![
                Span::styled(
                    if is_selected { "> " } else { "  " },
                    Style::default().fg(app.theme.mauve),
                ),
                Span::styled(format!("{} ", checkbox_str), checkbox_style),
                Span::styled(pin_prefix.to_string(), pin_style),
                Span::styled(format!("[{}] ", source_label), source_style),
                Span::styled(format!("{:<30}", item.name), name_style),
                Span::styled(format!(" {:<10}", status_label), status_style),
                Span::styled(format!(" {}", link_label), link_style),
                Span::raw("  "),
            ];
            line_spans.extend(score_spans);
            if !item.reason.is_empty() {
                line_spans.push(Span::raw("  "));
                line_spans.push(Span::styled(
                    item.reason.clone(),
                    Style::default().fg(app.theme.overlay),
                ));
            }
            if !cli_indicators.is_empty() {
                line_spans.push(Span::raw("  "));
                line_spans.extend(cli_indicators);
            }

            ListItem::new(Line::from(line_spans))
        })
        .collect();

    let scroll_indicator = if total_items > app.visible_height {
        format!(
            " {}-{}/{} ",
            app.scroll_offset + 1,
            (app.scroll_offset + app.visible_height).min(total_items),
            total_items
        )
    } else {
        format!(" {} ", total_items)
    };

    let rtab_label = if app.cli_tabs.is_empty() {
        "Skills"
    } else {
        app.active_cli().active_resource().label()
    };
    let sort_label = match app.sort_mode {
        super::app::SortMode::Default => "",
        super::app::SortMode::Score => " [sort: score]",
        super::app::SortMode::Name => " [sort: name]",
        super::app::SortMode::Origin => " [sort: origin]",
    };
    let title = format!(" {}{}{}", rtab_label, sort_label, scroll_indicator);

    let list = List::new(items).block(
        Block::default()
            .title(title)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(app.theme.surface)),
    );

    frame.render_widget(list, content_area);

    // Filter bar
    if let Some(filter_rect) = filter_area {
        let filter_line = if app.filtering {
            Line::from(vec![
                Span::styled(
                    " / ",
                    Style::default()
                        .fg(app.theme.yellow)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled(
                    &app.filter,
                    Style::default()
                        .fg(app.theme.text)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled(
                    "_",
                    Style::default()
                        .fg(app.theme.yellow)
                        .add_modifier(Modifier::RAPID_BLINK),
                ),
                Span::styled(
                    format!("  ({} matches)", total_items),
                    Style::default().fg(app.theme.subtext),
                ),
            ])
        } else {
            Line::from(vec![
                Span::styled(" filter: ", Style::default().fg(app.theme.subtext)),
                Span::styled(&app.filter, Style::default().fg(app.theme.yellow)),
                Span::styled(
                    format!("  ({} matches, / to edit, Esc to clear)", total_items),
                    Style::default().fg(app.theme.overlay),
                ),
            ])
        };
        frame.render_widget(Paragraph::new(filter_line), filter_rect);
    }
}

fn draw_footer(frame: &mut Frame, app: &App, area: Rect) {
    let keys = if app.preview_mode {
        vec![
            ("Enter", "confirm apply"),
            ("Esc/q", "cancel"),
            ("j/k", "scroll"),
        ]
    } else if app.global_search_mode {
        vec![
            ("Esc", "close"),
            ("Enter", "jump to tab"),
            ("j/k", "nav"),
            ("type", "search"),
        ]
    } else if app.filtering {
        vec![("Esc", "cancel"), ("Enter", "confirm"), ("type", "filter")]
    } else {
        vec![
            ("H/L", "cli"),
            ("Tab/h/l", "tab"),
            ("j/k", "nav"),
            ("Space", "toggle"),
            (
                "s",
                match app.sort_mode {
                    super::app::SortMode::Default => "sort",
                    super::app::SortMode::Score => "sort:score",
                    super::app::SortMode::Name => "sort:name",
                    super::app::SortMode::Origin => "sort:origin",
                },
            ),
            ("/", "filter"),
            ("?", "global search"),
            ("!", "pin to top"),
            ("i", "install"),
            ("t", "toggle CLIs"),
            ("p", "profiles"),
            ("A/N", "all/none"),
            ("a", "preview+apply"),
            ("q", "quit"),
        ]
    };

    let spans: Vec<Span> = keys
        .iter()
        .flat_map(|(key, desc)| {
            vec![
                Span::styled(
                    format!(" {} ", key),
                    Style::default()
                        .fg(app.theme.yellow)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled(format!("{} ", desc), Style::default().fg(app.theme.subtext)),
                Span::styled(" | ", Style::default().fg(app.theme.surface)),
            ]
        })
        .collect();

    let footer = Paragraph::new(Line::from(spans)).block(
        Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(app.theme.surface)),
    );

    frame.render_widget(footer, area);
}

fn draw_preview(frame: &mut Frame, app: &App, area: Rect) {
    frame.render_widget(Clear, area);

    let block = Block::default()
        .borders(Borders::ALL)
        .title(" Preview — Enter: apply  Esc: cancel  j/k: scroll ")
        .border_style(Style::default().fg(app.theme.mauve));

    let inner = block.inner(area);
    frame.render_widget(block, area);

    if app.preview_lines.is_empty() {
        let p = Paragraph::new("  No changes to apply.");
        frame.render_widget(p, inner);
        return;
    }

    let mut lines: Vec<Line> = Vec::new();
    let mut current_category = String::new();

    for pl in &app.preview_lines {
        if pl.category != current_category {
            if !current_category.is_empty() {
                lines.push(Line::from(""));
            }
            lines.push(Line::from(Span::styled(
                format!("  {}", pl.category),
                Style::default()
                    .fg(app.theme.blue)
                    .add_modifier(Modifier::BOLD),
            )));
            current_category = pl.category.clone();
        }

        let (symbol, color) = match pl.action {
            PreviewAction::Add => ("+", app.theme.green),
            PreviewAction::Remove => ("-", app.theme.red),
        };

        lines.push(Line::from(Span::styled(
            format!("    {} {}", symbol, pl.name),
            Style::default().fg(color),
        )));
    }

    // Apply scroll offset
    let visible_lines: Vec<Line> = lines.into_iter().skip(app.preview_scroll).collect();

    let paragraph = Paragraph::new(visible_lines);
    frame.render_widget(paragraph, inner);
}

fn draw_cli_toggle(frame: &mut Frame, app: &App, area: Rect) {
    if app.cli_toggle_selections.is_empty() {
        return;
    }

    // Compute popup dimensions
    let inner_width = 36u16;
    let popup_width = inner_width + 2; // borders
    let popup_height = (app.cli_toggle_selections.len() as u16) + 4; // entries + title + blank + hint

    // Center the popup within area
    let x = area.x + area.width.saturating_sub(popup_width) / 2;
    let y = area.y + area.height.saturating_sub(popup_height) / 2;
    let popup_rect = Rect {
        x,
        y,
        width: popup_width.min(area.width),
        height: popup_height.min(area.height),
    };

    // Clear background behind popup
    frame.render_widget(Clear, popup_rect);

    // Build lines: one per CLI
    let mut lines: Vec<Line> = app
        .cli_toggle_selections
        .iter()
        .enumerate()
        .map(|(i, (cli_name, enabled))| {
            let is_cursor = i == app.cli_toggle_cursor;
            let checkbox = if *enabled { "[x]" } else { "[ ]" };
            let checkbox_style = if *enabled {
                Style::default()
                    .fg(app.theme.green)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(app.theme.overlay)
            };
            let name_style = if is_cursor {
                Style::default()
                    .fg(app.theme.mauve)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(app.theme.subtext)
            };
            Line::from(vec![
                Span::styled(
                    if is_cursor { "> " } else { "  " },
                    Style::default().fg(app.theme.mauve),
                ),
                Span::styled(format!("{} ", checkbox), checkbox_style),
                Span::styled(cli_name.clone(), name_style),
            ])
        })
        .collect();

    // Blank separator line
    lines.push(Line::from(""));

    // Hint line
    lines.push(Line::from(vec![
        Span::styled(
            "  Space",
            Style::default()
                .fg(app.theme.yellow)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(": toggle  ", Style::default().fg(app.theme.subtext)),
        Span::styled(
            "Enter",
            Style::default()
                .fg(app.theme.yellow)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(": apply", Style::default().fg(app.theme.subtext)),
    ]));

    let title = format!(" {} ", app.cli_toggle_resource_name);
    let block = Block::default()
        .title(title)
        .borders(Borders::ALL)
        .border_style(Style::default().fg(app.theme.mauve));

    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, popup_rect);
}

fn draw_profile_selector(frame: &mut Frame, app: &App, area: Rect) {
    let height = (app.profile_list.len() as u16 + 4).min(15);
    let width = 52u16;
    let x = area.x + area.width.saturating_sub(width) / 2;
    let y = area.y + area.height.saturating_sub(height) / 2;
    let popup = Rect::new(x, y, width.min(area.width), height.min(area.height));

    frame.render_widget(Clear, popup);

    let title = if app.profile_save_mode {
        " Save Profile "
    } else {
        " Profiles "
    };
    let block = Block::default()
        .borders(Borders::ALL)
        .title(title)
        .border_style(Style::default().fg(app.theme.mauve));
    let inner = block.inner(popup);
    frame.render_widget(block, popup);

    if app.profile_save_mode {
        let lines = vec![
            Line::from(Span::styled(
                "  Profile name:",
                Style::default().fg(app.theme.text),
            )),
            Line::from(Span::styled(
                format!("  > {}_", app.profile_save_input),
                Style::default().fg(app.theme.green),
            )),
            Line::from(""),
            Line::from(Span::styled(
                "  Enter: save  Esc: cancel",
                Style::default().fg(app.theme.subtext),
            )),
        ];
        frame.render_widget(Paragraph::new(lines), inner);
        return;
    }

    let mut lines: Vec<Line> = app
        .profile_list
        .iter()
        .enumerate()
        .map(|(i, (name, skills, agents))| {
            let cursor = if i == app.profile_cursor {
                "▸ "
            } else {
                "  "
            };
            let style = if i == app.profile_cursor {
                Style::default()
                    .fg(app.theme.mauve)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(app.theme.text)
            };
            let detail = format!("{} skills, {} agents", skills, agents);
            Line::from(vec![
                Span::styled(format!("{}{:<22}", cursor, name), style),
                Span::styled(detail, Style::default().fg(app.theme.subtext)),
            ])
        })
        .collect();

    lines.push(Line::from(""));
    lines.push(Line::from(Span::styled(
        "  Enter: load  s: save current  Esc: close",
        Style::default().fg(app.theme.subtext),
    )));

    frame.render_widget(Paragraph::new(lines), inner);
}

fn draw_global_search(frame: &mut Frame, app: &App, area: Rect) {
    frame.render_widget(Clear, area);
    let block = Block::default()
        .borders(Borders::ALL)
        .title(format!(" Search: {} ", app.filter))
        .border_style(Style::default().fg(app.theme.mauve));
    let inner = block.inner(area);
    frame.render_widget(block, area);

    if app.global_search_results.is_empty() {
        let msg = if app.filter.is_empty() {
            "Type to search..."
        } else {
            "No matches"
        };
        frame.render_widget(Paragraph::new(format!("  {}", msg)), inner);
        return;
    }

    let lines: Vec<Line> = app
        .global_search_results
        .iter()
        .enumerate()
        .map(|(i, (tab, _, name))| {
            let cursor = if i == app.global_search_cursor {
                "▸ "
            } else {
                "  "
            };
            let tag = format!("[{:<8}]", tab.label());
            let style = if i == app.global_search_cursor {
                Style::default()
                    .fg(app.theme.mauve)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(app.theme.text)
            };
            Line::from(vec![
                Span::styled(cursor, style),
                Span::styled(tag, Style::default().fg(app.theme.subtext)),
                Span::styled(format!(" {}", name), style),
            ])
        })
        .collect();

    frame.render_widget(Paragraph::new(lines), inner);
}

fn score_bar(score: f32) -> String {
    let filled = (score * 10.0) as usize;
    let empty = 10usize.saturating_sub(filled);
    format!("{}{}", "█".repeat(filled), "░".repeat(empty))
}

fn confidence_tier(score: f32) -> &'static str {
    if score >= doctor::TIER_CRITICAL {
        "CRIT"
    } else if score >= doctor::TIER_HIGH {
        "HIGH"
    } else if score >= doctor::TIER_MEDIUM {
        "MED"
    } else if score > 0.0 {
        "LOW"
    } else {
        ""
    }
}

fn score_color(score: f32, theme: &crate::theme::Theme) -> Color {
    if score >= doctor::TIER_CRITICAL {
        theme.green
    } else if score >= doctor::TIER_HIGH {
        theme.teal
    } else if score >= doctor::TIER_MEDIUM {
        theme.yellow
    } else if score > 0.0 {
        theme.peach
    } else {
        theme.overlay
    }
}

fn tier_color(score: f32, theme: &crate::theme::Theme) -> Color {
    score_color(score, theme)
}
