---
paths:
  - "**/*.ml"
  - "**/*.mli"
---
# OCaml Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with OCaml-specific content.

## Modules as Interfaces (First-Class Modules)

Use modules as the primary unit of abstraction:

```ocaml
module type Repository = sig
  type t
  val find_by_id : int -> (t option, string) result
  val save       : t -> (t, string) result
end

module UserService (R : Repository) = struct
  let get_or_create id =
    match R.find_by_id id with
    | Ok (Some u) -> Ok u
    | Ok None     -> R.save (User.default id)
    | Error e     -> Error e
end
```

## Functors

Parameterize modules over other modules:

```ocaml
module Make (Ord : Map.OrderedType) = struct
  include Map.Make(Ord)

  let find_or ~default key m =
    match find_opt key m with Some v -> v | None -> default
end

module StringMap = Make(String)
```

## GADTs for Type-Safe DSLs

Use GADTs to encode invariants in the type system:

```ocaml
type _ expr =
  | Int  : int             -> int expr
  | Bool : bool            -> bool expr
  | Add  : int expr * int expr -> int expr
  | If   : bool expr * 'a expr * 'a expr -> 'a expr

let rec eval : type a. a expr -> a = function
  | Int n         -> n
  | Bool b        -> b
  | Add (l, r)    -> eval l + eval r
  | If (c, t, e) -> if eval c then eval t else eval e
```

## Result Monad

Chain fallible operations with `let*` (bind operator):

```ocaml
let ( let* ) = Result.bind

let process_order id =
  let* order = Order.find id in
  let* _     = Payment.charge order.total in
  let* saved = Order.mark_paid order in
  Ok saved
```

## Smart Constructors with Private Types

```ocaml
module Email : sig
  type t
  val of_string : string -> (t, string) result
  val to_string : t -> string
end = struct
  type t = string
  let of_string s =
    if String.contains s '@' then Ok s
    else Error ("invalid email: " ^ s)
  let to_string s = s
end
```

## References

See skill: `ocaml-patterns` for comprehensive functional patterns and Lwt/Async concurrency.
