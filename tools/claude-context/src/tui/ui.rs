use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Tabs},
    Frame,
};

use super::app::{App, Tab};
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
const _TEXT: Color = Color::Rgb(205, 214, 244);
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
            Constraint::Length(3), // tabs
            Constraint::Min(10),  // content
            Constraint::Length(3), // footer
        ])
        .split(area);

    draw_header(frame, app, chunks[0]);
    draw_tabs(frame, app, chunks[1]);
    draw_content(frame, app, chunks[2]);
    draw_footer(frame, app, chunks[3]);
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
        " Claude Context Manager  {}  Detected: {}",
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

fn draw_tabs(frame: &mut Frame, app: &App, area: Rect) {
    let tab_titles: Vec<Line> = Tab::all()
        .iter()
        .map(|t| {
            let items = match t {
                Tab::Skills => &app.skills,
                Tab::Agents => &app.agents,
                Tab::Commands => &app.commands,
                Tab::Mcp => &app.mcp,
                Tab::Rules => &app.rules,
                Tab::Plugins => &app.plugins,
            };
            let enabled = items.iter().filter(|i| i.enabled).count();
            let total = items.len();
            Line::from(format!(" {} {}/{} ", t.label(), enabled, total))
        })
        .collect();

    let selected = Tab::all()
        .iter()
        .position(|t| *t == app.active_tab)
        .unwrap_or(0);

    let tabs = Tabs::new(tab_titles)
        .select(selected)
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

fn draw_content(frame: &mut Frame, app: &App, area: Rect) {
    let filtered = app.filtered_items();
    let total_items = filtered.len();

    // Apply scroll offset
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
            let bar = score_bar(item.score);
            let tier = confidence_tier(item.score);
            let reason = if item.reason.is_empty() {
                String::new()
            } else {
                format!("  {}", item.reason)
            };

            let is_selected = display_idx == app.cursor;

            let style = if is_selected {
                Style::default().fg(BLUE).add_modifier(Modifier::BOLD)
            } else if item.enabled {
                Style::default().fg(GREEN)
            } else {
                Style::default().fg(SUBTEXT)
            };

            let checkbox_style = if item.enabled {
                Style::default().fg(GREEN)
            } else {
                Style::default().fg(OVERLAY0)
            };

            let origin_indicator = match item.origin {
                Origin::Local => Span::styled("[L] ", Style::default().fg(GREEN)),
                Origin::Remote => Span::styled("[R] ", Style::default().fg(PEACH)),
            };

            let line = Line::from(vec![
                Span::styled(
                    if is_selected { "> " } else { "  " },
                    Style::default().fg(MAUVE),
                ),
                Span::styled(
                    format!("{} ", if item.enabled { "[x]" } else { "[ ]" }),
                    checkbox_style,
                ),
                origin_indicator,
                Span::styled(format!("{:<28}", item.name), style),
                Span::styled(
                    format!(" {} ", bar),
                    Style::default().fg(score_color(item.score)),
                ),
                Span::styled(
                    format!("{:<6}", tier),
                    Style::default().fg(tier_color(item.score)),
                ),
                Span::styled(reason, Style::default().fg(OVERLAY0)),
            ]);

            ListItem::new(line)
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

    let title = if app.filtering {
        format!(" {} (/{}){}", app.active_tab.label(), app.filter, scroll_indicator)
    } else if !app.filter.is_empty() {
        format!(
            " {} [filter: {}]{}",
            app.active_tab.label(),
            app.filter,
            scroll_indicator
        )
    } else {
        format!(" {}{}", app.active_tab.label(), scroll_indicator)
    };

    let list = List::new(items).block(
        Block::default()
            .title(title)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(SURFACE0)),
    );

    frame.render_widget(list, area);
}

fn draw_footer(frame: &mut Frame, app: &App, area: Rect) {
    let keys = if app.filtering {
        vec![
            ("Esc", "cancel"),
            ("Enter", "confirm"),
            ("type", "filter"),
        ]
    } else {
        vec![
            ("Tab/h/l", "tab"),
            ("j/k", "nav"),
            ("Space", "toggle"),
            ("/", "filter"),
            ("i", "install"),
            ("A/N", "all/none"),
            ("PgUp/Dn", "scroll"),
            ("g/G", "top/bottom"),
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
