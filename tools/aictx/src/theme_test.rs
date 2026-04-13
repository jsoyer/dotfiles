#[cfg(test)]
mod tests {
    use crate::theme::Theme;
    use ratatui::style::Color;

    #[test]
    fn catppuccin_mocha_is_default() {
        let t = Theme::by_name("unknown-theme");
        // default falls back to catppuccin-mocha
        assert_eq!(t.blue, Color::Rgb(137, 180, 250));
        assert_eq!(t.base, Color::Rgb(30, 30, 46));
    }

    #[test]
    fn by_name_catppuccin_mocha() {
        let t = Theme::by_name("catppuccin-mocha");
        assert_eq!(t.blue, Color::Rgb(137, 180, 250));
        assert_eq!(t.green, Color::Rgb(166, 227, 161));
        assert_eq!(t.red, Color::Rgb(243, 139, 168));
    }

    #[test]
    fn by_name_catppuccin_latte() {
        let t = Theme::by_name("catppuccin-latte");
        assert_eq!(t.blue, Color::Rgb(30, 102, 245));
        assert_eq!(t.base, Color::Rgb(239, 241, 245));
    }

    #[test]
    fn by_name_snazzy() {
        let t = Theme::by_name("snazzy");
        assert_eq!(t.blue, Color::Rgb(87, 199, 255));
        assert_eq!(t.green, Color::Rgb(90, 247, 142));
    }

    #[test]
    fn by_name_nord() {
        let t = Theme::by_name("nord");
        assert_eq!(t.blue, Color::Rgb(136, 192, 208));
        assert_eq!(t.base, Color::Rgb(46, 52, 64));
    }

    #[test]
    fn by_name_dracula() {
        let t = Theme::by_name("dracula");
        assert_eq!(t.blue, Color::Rgb(139, 233, 253));
        assert_eq!(t.mauve, Color::Rgb(189, 147, 249));
    }

    #[test]
    fn by_name_gruvbox() {
        let t = Theme::by_name("gruvbox");
        assert_eq!(t.blue, Color::Rgb(131, 165, 152));
        assert_eq!(t.base, Color::Rgb(40, 40, 40));
    }

    #[test]
    fn by_name_tokyo_night() {
        let t = Theme::by_name("tokyo-night");
        assert_eq!(t.blue, Color::Rgb(122, 162, 247));
        assert_eq!(t.base, Color::Rgb(26, 27, 38));
    }

    #[test]
    fn available_contains_all_builtins() {
        let themes = Theme::available();
        assert!(themes.contains(&"catppuccin-mocha"));
        assert!(themes.contains(&"catppuccin-latte"));
        assert!(themes.contains(&"snazzy"));
        assert!(themes.contains(&"nord"));
        assert!(themes.contains(&"dracula"));
        assert!(themes.contains(&"gruvbox"));
        assert!(themes.contains(&"tokyo-night"));
        assert_eq!(themes.len(), 7);
    }

    #[test]
    fn all_themes_have_correct_text_color() {
        for name in Theme::available() {
            let t = Theme::by_name(name);
            match *name {
                "catppuccin-mocha" => assert_eq!(t.text, Color::Rgb(205, 214, 244)),
                "catppuccin-latte" => assert_eq!(t.text, Color::Rgb(76, 79, 105)),
                "snazzy" => assert_eq!(t.text, Color::Rgb(235, 235, 235)),
                "nord" => assert_eq!(t.text, Color::Rgb(236, 239, 244)),
                "dracula" => assert_eq!(t.text, Color::Rgb(248, 248, 242)),
                "gruvbox" => assert_eq!(t.text, Color::Rgb(235, 219, 178)),
                "tokyo-night" => assert_eq!(t.text, Color::Rgb(192, 202, 245)),
                _ => {}
            }
        }
    }
}
