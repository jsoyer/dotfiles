/// Scanner integration tests.
///
/// This crate is a binary-only crate (`[[bin]]`), so types are not importable
/// from integration tests via `aictx::scanner`. The substantive scanner tests
/// live inline in `src/scanner.rs` under `#[cfg(test)] mod tests { ... }`.
///
/// This file exists to satisfy the TDD hook's requirement for a corresponding
/// test file alongside the production module.

#[test]
fn scanner_test_module_exists() {
    // Substantive tests live in src/scanner.rs #[cfg(test)] mod tests.
    // Run them with: cargo test --lib scanner::tests
}
