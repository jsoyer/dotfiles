use ratatui::style::Color;

#[derive(Debug, Clone, PartialEq)]
pub struct Theme {
    pub blue: Color,
    pub green: Color,
    pub red: Color,
    pub yellow: Color,
    pub mauve: Color,
    pub teal: Color,
    pub peach: Color,
    pub text: Color,
    pub subtext: Color,
    pub surface: Color,
    pub base: Color,
    pub overlay: Color,
}

impl Theme {
    pub fn by_name(name: &str) -> Self {
        match name {
            "catppuccin-latte" => Self::catppuccin_latte(),
            "snazzy" => Self::snazzy(),
            "nord" => Self::nord(),
            "dracula" => Self::dracula(),
            "gruvbox" => Self::gruvbox(),
            "tokyo-night" => Self::tokyo_night(),
            _ => Self::catppuccin_mocha(), // default (includes "catppuccin-mocha")
        }
    }

    pub fn catppuccin_mocha() -> Self {
        Self {
            blue: Color::Rgb(137, 180, 250),
            green: Color::Rgb(166, 227, 161),
            red: Color::Rgb(243, 139, 168),
            yellow: Color::Rgb(249, 226, 175),
            mauve: Color::Rgb(203, 166, 247),
            teal: Color::Rgb(148, 226, 213),
            peach: Color::Rgb(250, 179, 135),
            text: Color::Rgb(205, 214, 244),
            subtext: Color::Rgb(166, 173, 200),
            surface: Color::Rgb(49, 50, 68),
            base: Color::Rgb(30, 30, 46),
            overlay: Color::Rgb(108, 112, 134),
        }
    }

    pub fn catppuccin_latte() -> Self {
        Self {
            blue: Color::Rgb(30, 102, 245),
            green: Color::Rgb(64, 160, 43),
            red: Color::Rgb(210, 15, 57),
            yellow: Color::Rgb(223, 142, 29),
            mauve: Color::Rgb(136, 57, 239),
            teal: Color::Rgb(23, 146, 153),
            peach: Color::Rgb(254, 100, 11),
            text: Color::Rgb(76, 79, 105),
            subtext: Color::Rgb(108, 111, 133),
            surface: Color::Rgb(204, 208, 218),
            base: Color::Rgb(239, 241, 245),
            overlay: Color::Rgb(156, 160, 176),
        }
    }

    pub fn snazzy() -> Self {
        Self {
            blue: Color::Rgb(87, 199, 255),
            green: Color::Rgb(90, 247, 142),
            red: Color::Rgb(255, 85, 85),
            yellow: Color::Rgb(243, 249, 157),
            mauve: Color::Rgb(255, 106, 193),
            teal: Color::Rgb(154, 237, 254),
            peach: Color::Rgb(255, 158, 100),
            text: Color::Rgb(235, 235, 235),
            subtext: Color::Rgb(180, 180, 180),
            surface: Color::Rgb(52, 52, 68),
            base: Color::Rgb(40, 42, 54),
            overlay: Color::Rgb(130, 130, 150),
        }
    }

    pub fn nord() -> Self {
        Self {
            blue: Color::Rgb(136, 192, 208),
            green: Color::Rgb(163, 190, 140),
            red: Color::Rgb(191, 97, 106),
            yellow: Color::Rgb(235, 203, 139),
            mauve: Color::Rgb(180, 142, 173),
            teal: Color::Rgb(143, 188, 187),
            peach: Color::Rgb(208, 135, 112),
            text: Color::Rgb(236, 239, 244),
            subtext: Color::Rgb(216, 222, 233),
            surface: Color::Rgb(59, 66, 82),
            base: Color::Rgb(46, 52, 64),
            overlay: Color::Rgb(76, 86, 106),
        }
    }

    pub fn dracula() -> Self {
        Self {
            blue: Color::Rgb(139, 233, 253),
            green: Color::Rgb(80, 250, 123),
            red: Color::Rgb(255, 85, 85),
            yellow: Color::Rgb(241, 250, 140),
            mauve: Color::Rgb(189, 147, 249),
            teal: Color::Rgb(139, 233, 253),
            peach: Color::Rgb(255, 184, 108),
            text: Color::Rgb(248, 248, 242),
            subtext: Color::Rgb(189, 189, 189),
            surface: Color::Rgb(68, 71, 90),
            base: Color::Rgb(40, 42, 54),
            overlay: Color::Rgb(98, 114, 164),
        }
    }

    pub fn gruvbox() -> Self {
        Self {
            blue: Color::Rgb(131, 165, 152),
            green: Color::Rgb(184, 187, 38),
            red: Color::Rgb(251, 73, 52),
            yellow: Color::Rgb(250, 189, 47),
            mauve: Color::Rgb(211, 134, 155),
            teal: Color::Rgb(142, 192, 124),
            peach: Color::Rgb(254, 128, 25),
            text: Color::Rgb(235, 219, 178),
            subtext: Color::Rgb(189, 174, 147),
            surface: Color::Rgb(60, 56, 54),
            base: Color::Rgb(40, 40, 40),
            overlay: Color::Rgb(124, 111, 100),
        }
    }

    pub fn tokyo_night() -> Self {
        Self {
            blue: Color::Rgb(122, 162, 247),
            green: Color::Rgb(158, 206, 106),
            red: Color::Rgb(247, 118, 142),
            yellow: Color::Rgb(224, 175, 104),
            mauve: Color::Rgb(187, 154, 247),
            teal: Color::Rgb(115, 218, 202),
            peach: Color::Rgb(255, 158, 100),
            text: Color::Rgb(192, 202, 245),
            subtext: Color::Rgb(145, 155, 199),
            surface: Color::Rgb(41, 46, 66),
            base: Color::Rgb(26, 27, 38),
            overlay: Color::Rgb(86, 95, 137),
        }
    }

    #[allow(dead_code)]
    pub fn available() -> &'static [&'static str] {
        &[
            "catppuccin-mocha",
            "catppuccin-latte",
            "snazzy",
            "nord",
            "dracula",
            "gruvbox",
            "tokyo-night",
        ]
    }
}
