# TypeScript Lens

What a reviewer checks on TypeScript lines. Baseline:
https://google.github.io/styleguide/tsguide.html, or the guide the repository
names.

## 1. Types and assertions

- No redundant type assertions; let inference carry the type where it can.
- Use `??` and explicit null checks instead of `Number(x) || 0`, which turns
  a legitimate `0` into the fallback.
- Helper functions use verb names and declare return types.

## 2. Surface

- Don't export a function only so a test can reach it; test the public API.
- A frontend renders what the backend decides. Never rebuild a decision from
  display text: no `text.includes('(paused: ')`, no regex over a marker, no
  `header.split(' ')[0]` (`lenses/common/stack_shape.md` §2).

## 3. Imports

- Every import is used in the file; no side-effect imports without a comment.
- Import from the module that defines the symbol, not from a barrel that
  happens to re-export it, unless the repository's convention is the barrel.
