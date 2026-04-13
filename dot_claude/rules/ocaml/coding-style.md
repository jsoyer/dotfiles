---
paths:
  - "**/*.ml"
  - "**/*.mli"
  - "**/dune"
  - "**/dune-project"
---
# OCaml Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with OCaml-specific content.

## Formatting

- **ocamlformat** for enforcement — run before committing
- **dune** as the build system — always provide a `dune` file per directory
- 2-space indent; max line width 80 characters (ocamlformat default)

```bash
ocamlformat --inplace src/**/*.ml src/**/*.mli
dune build @check   # type-check without producing artifacts
```

## Module Signatures

Every public module should have a `.mli` interface file:

```ocaml
(* user.mli — public contract *)
type t
val create : string -> string -> (t, string) result
val email  : t -> string
```

```ocaml
(* user.ml — implementation *)
type t = { name : string; email : string }

let create name email =
  if String.contains email '@' then Ok { name; email }
  else Error "invalid email"

let email u = u.email
```

## Labeled and Optional Arguments

Prefer labeled arguments for functions with multiple parameters of the same type:

```ocaml
let create_server ~host ~port ?(max_conn = 100) () =
  { host; port; max_conn }

(* Call site is self-documenting *)
let s = create_server ~host:"localhost" ~port:8080 ()
```

## PPX Annotations

Use ppx for derived functionality — keep manual boilerplate minimal:

```ocaml
type user = {
  id    : int;
  name  : string;
  email : string;
} [@@deriving show, eq, yojson]
```

## Error Handling

Prefer `result` over exceptions for expected failures:

```ocaml
let ( let* ) = Result.bind

let load_config path =
  let* content = In_channel.input_all_opt path
    |> Option.to_result ~none:"file not found" in
  let* cfg = Config.of_string content in
  Ok cfg
```

## References

See skill: `ocaml-patterns` for functors, GADTs, and module patterns.
