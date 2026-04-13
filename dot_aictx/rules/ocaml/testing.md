---
paths:
  - "**/*.ml"
  - "**/test/**"
  - "**/dune"
---
# OCaml Testing

> This file extends [common/testing.md](../common/testing.md) with OCaml-specific content.

## Test Frameworks

- **alcotest** — lightweight unit testing with clear failure diffs
- **QCheck** — property-based testing (QuickCheck port)
- **ppx_inline_test** — expect tests embedded in source files
- dune integrates all three via `(test ...)` stanza

## Alcotest Unit Tests

```ocaml
let test_email_valid () =
  let result = Email.of_string "user@example.com" in
  Alcotest.(check (result string string)) "valid email" (Ok "user@example.com") result

let test_email_invalid () =
  let result = Email.of_string "notanemail" in
  Alcotest.(check bool) "is error" true (Result.is_error result)

let () =
  Alcotest.run "Email" [
    "validation", [
      Alcotest.test_case "accepts valid" `Quick test_email_valid;
      Alcotest.test_case "rejects invalid" `Quick test_email_invalid;
    ]
  ]
```

## QCheck Property Tests

```ocaml
open QCheck

let prop_list_rev =
  Test.make ~name:"reverse involution"
    (list int)
    (fun xs -> List.rev (List.rev xs) = xs)

let () =
  QCheck_runner.run_tests_main [prop_list_rev]
```

## Dune Test Stanza

```lisp
; dune file in test/ directory
(test
 (name test_email)
 (libraries mylib alcotest qcheck))
```

## Testing Commands

```bash
dune test                # Run all tests
dune test --force        # Force re-run even if up-to-date
dune runtest test/       # Run tests in a specific directory
```

## References

See skill: `ocaml-testing` for expect tests, fuzzing with crowbar, and async testing with Lwt.
