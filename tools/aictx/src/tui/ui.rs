use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Tabs},
    Frame,
};

use super::app::{App, ResourceTab};
use crate::doctor;
use crate::plugins::Origin;

// Catppuccin Mocha palette
const BLUE: Color = Color::Rgb(137, 180, 250);
const GREEN: Color = Color::Rgb(166, 227, 161);
const _RED: Color = Color::Rgb(243, 139, 168);
const YELLOW: Color = Color::Rgb(249, 226, 175);
const MAUVE: Color = Color::Rgb(203, 166, 247);
const TEAL: Color = Color::Rgb(148, 226, 213);
const PEACH: Color = Color::Rgb(250, 179, 135);
const TEXT: Color = Color::Rgb(205, 214, 244);
const SUBTEXT: Color = Color::Rgb(166, 173, 200);
const SURFACE0: Color = Color::Rgb(49, 50, 68);
const _BASE: Color = Color::Rgb(30, 30, 46);
const OVERLAY0: Color = Color::Rgb(108, 112, 134);

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
        .style(Style::default().fg(BLUE).add_modifier(Modifier::BOLD))
        .block(
            Block::default()
                .borders(Borders::BOTTOM)
                .border_style(Style::default().fg(SURFACE0)),
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
        .style(Style::default().fg(SUBTEXT))
        .highlight_style(
            Style::default()
                .fg(MAUVE)
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

    let tab_titles: Vec<Line> = cli
        .resource_tabs
        .iter()
        .map(|rt| {
            let items = app.items.get(&(cli.cli_name.clone(), *rt));
            let enabled = items
                .map(|v| v.iter().filter(|i| i.enabled).count())
                .unwrap_or(0);
            let total = items.map(|v| v.len()).unwrap_or(0);
            Line::from(format!(" {} {}/{} ", rt.label(), enabled, total))
        })
        .collect();

    let tabs = Tabs::new(tab_titles)
        .select(cli.active_resource_idx)
        .style(Style::default().fg(SUBTEXT))
        .highlight_style(
            Style::default()
                .fg(BLUE)
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

fn status_indicator(item: &super::app::ToggleItem) -> (&'static str, Style) {
    if item.enabled {
        ("🟢 installed", Style::default().fg(GREEN))
    } else if item.available {
        ("🟡 available", Style::default().fg(YELLOW))
    } else {
        ("🔵 remote", Style::default().fg(PEACH))
    }
}

fn source_indicator(item: &super::app::ToggleItem) -> (&'static str, Style) {
    match item.origin {
        Origin::Local => ("cache", Style::default().fg(SUBTEXT)),
        Origin::Remote => ("remote", Style::default().fg(PEACH)),
    }
}

fn symlink_indicator(item: &super::app::ToggleItem) -> (&'static str, Style) {
    if item.enabled {
        ("✔", Style::default().fg(GREEN))
    } else {
        ("✖", Style::default().fg(OVERLAY0))
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
                    Style::default().fg(GREEN).add_modifier(Modifier::BOLD),
                )
            } else if item.suggested {
                ("[~]", Style::default().fg(MAUVE))
            } else {
                ("[ ]", Style::default().fg(OVERLAY0))
            };

            // Name: white for active, mauve for suggested, dim for inactive
            // Blue+bold override when cursor is on it
            let name_style = if is_selected {
                Style::default().fg(BLUE).add_modifier(Modifier::BOLD)
            } else if item.enabled {
                Style::default().fg(TEXT)
            } else if item.suggested {
                Style::default().fg(SUBTEXT)
            } else {
                Style::default().fg(OVERLAY0)
            };

            let (status_label, status_style) = status_indicator(item);
            let (source_label, source_style) = source_indicator(item);
            let (link_label, link_style) = symlink_indicator(item);

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
                            Style::default().fg(TEAL),
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
                        Style::default().fg(score_color(item.score)),
                    ),
                    Span::styled(
                        format!("{:<5}", tier),
                        Style::default().fg(tier_color(item.score)),
                    ),
                ]
            } else {
                vec![Span::raw("                  ")]
            };

            let mut line_spans = vec![
                Span::styled(
                    if is_selected { "> " } else { "  " },
                    Style::default().fg(MAUVE),
                ),
                Span::styled(format!("{} ", checkbox_str), checkbox_style),
                Span::styled(format!("{:<30}", item.name), name_style),
                Span::raw("  "),
                Span::styled(format!("{:<12}", status_label), status_style),
                Span::raw("  "),
                Span::styled(format!("{:<8}", source_label), source_style),
                Span::raw("  link "),
                Span::styled(link_label.to_string(), link_style),
                Span::raw("  "),
            ];
            line_spans.extend(score_spans);
            if !item.reason.is_empty() {
                line_spans.push(Span::raw("  "));
                line_spans.push(Span::styled(
                    item.reason.clone(),
                    Style::default().fg(OVERLAY0),
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
    };
    let title = format!(" {}{}{}", rtab_label, sort_label, scroll_indicator);

    let list = List::new(items).block(
        Block::default()
            .title(title)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(SURFACE0)),
    );

    frame.render_widget(list, content_area);

    // Filter bar
    if let Some(filter_rect) = filter_area {
        let filter_line = if app.filtering {
            Line::from(vec![
                Span::styled(
                    " / ",
                    Style::default().fg(YELLOW).add_modifier(Modifier::BOLD),
                ),
                Span::styled(
                    &app.filter,
                    Style::default().fg(TEXT).add_modifier(Modifier::BOLD),
                ),
                Span::styled(
                    "_",
                    Style::default()
                        .fg(YELLOW)
                        .add_modifier(Modifier::RAPID_BLINK),
                ),
                Span::styled(
                    format!("  ({} matches)", total_items),
                    Style::default().fg(SUBTEXT),
                ),
            ])
        } else {
            Line::from(vec![
                Span::styled(" filter: ", Style::default().fg(SUBTEXT)),
                Span::styled(&app.filter, Style::default().fg(YELLOW)),
                Span::styled(
                    format!("  ({} matches, / to edit, Esc to clear)", total_items),
                    Style::default().fg(OVERLAY0),
                ),
            ])
        };
        frame.render_widget(Paragraph::new(filter_line), filter_rect);
    }
}

fn draw_footer(frame: &mut Frame, app: &App, area: Rect) {
    let keys = if app.filtering {
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
                },
            ),
            ("/", "filter"),
            ("i", "install"),
            ("t", "toggle-cli"),
            ("A/N", "all/none"),
            ("a", "apply"),
            ("q", "quit"),
        ]
    };

    let spans: Vec<Span> = keys
        .iter()
        .flat_map(|(key, desc)| {
            vec![
                Span::styled(
                    format!(" {} ", key),
                    Style::default().fg(YELLOW).add_modifier(Modifier::BOLD),
                ),
                Span::styled(format!("{} ", desc), Style::default().fg(SUBTEXT)),
                Span::styled(" | ", Style::default().fg(SURFACE0)),
            ]
        })
        .collect();

    let footer = Paragraph::new(Line::from(spans)).block(
        Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(SURFACE0)),
    );

    frame.render_widget(footer, area);
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

fn score_color(score: f32) -> Color {
    if score >= doctor::TIER_CRITICAL {
        GREEN
    } else if score >= doctor::TIER_HIGH {
        TEAL
    } else if score >= doctor::TIER_MEDIUM {
        YELLOW
    } else if score > 0.0 {
        PEACH
    } else {
        OVERLAY0
    }
}

fn tier_color(score: f32) -> Color {
    score_color(score)
}
