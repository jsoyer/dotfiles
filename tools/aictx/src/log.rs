use std::sync::OnceLock;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Level {
    Quiet,
    Verbose,
    Debug,
}

static LOG_LEVEL: OnceLock<Level> = OnceLock::new();

pub fn init(verbose: bool, debug: bool) {
    let level = if debug {
        Level::Debug
    } else if verbose {
        Level::Verbose
    } else {
        Level::Quiet
    };
    let _ = LOG_LEVEL.set(level);
}

pub fn level() -> Level {
    LOG_LEVEL.get().copied().unwrap_or(Level::Quiet)
}

/// Print a verbose message (shown with -v or --debug)
#[macro_export]
macro_rules! verbose {
    ($($arg:tt)*) => {
        if $crate::log::level() >= $crate::log::Level::Verbose {
            eprintln!($($arg)*);
        }
    };
}

/// Print a debug message (shown only with --debug)
#[macro_export]
macro_rules! debug_log {
    ($($arg:tt)*) => {
        if $crate::log::level() >= $crate::log::Level::Debug {
            eprintln!("[debug] {}", format!($($arg)*));
        }
    };
}
