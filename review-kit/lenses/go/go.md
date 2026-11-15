# Go Lens

What a reviewer checks on Go lines. Baseline: Effective Go
(https://go.dev/doc/effective_go), the Go code review comments
(https://go.dev/wiki/CodeReviewComments) and the repository's own guide.
`gofmt` (or `goimports`) and `go vet` run before every commit; `staticcheck`
or `golangci-lint` is the configured `reviewkit.lintCmd`.

## 1. Errors

- Every error is handled or returned; `_ = f()` needs a comment saying why
  the error does not matter.
- Wrap with context and `%w` (`fmt.Errorf("open %s: %w", path, err)`), so
  callers can `errors.Is` and `errors.As`. Never wrap twice with the same
  context; never log and return the same error.
- Sentinel errors are exported as `ErrName`; error types end in `Error`.
- Libraries never `panic` on bad input or `os.Exit`; only `main` decides.
- Check the error before using the value; `defer f.Close()` on a writer
  loses the close error, so close explicitly on the write path.

## 2. Concurrency

- Every goroutine has an owner that knows when it ends: a `context.Context`
  for cancellation and an `errgroup.Group` or `sync.WaitGroup` to wait.
  A goroutine the function starts and does not wait for is a finding.
- `ctx` is the first parameter and is never stored in a struct.
- Channels carry a direction in signatures (`<-chan T`, `chan<- T`). The
  sender closes; a receive-only side never does.
- Never copy a `sync.Mutex` or embed one in an exported struct's public
  fields; guard the fields it protects with a comment naming the mutex.
- Shared maps need a lock or `sync.Map`; tests run with `-race`.
- Time: `time.Duration`, never an `int` of seconds; `time.Ticker` and
  `time.Timer` are stopped.

## 3. API shape

- Accept interfaces, return concrete types. Define an interface where it is
  consumed, keep it to 1-3 methods, and never for a single implementation
  only so a test can mock it.
- Zero values are useful: a struct works without a constructor, or the
  constructor is `NewX` and the fields are unexported.
- No package-level mutable state and no `init()` with side effects; pass
  dependencies explicitly.
- Options: a struct for 2+ optional settings, functional options only when
  the API is public and will grow.
- Names: `MixedCaps`, no stutter (`http.Server`, not `http.HTTPServer`),
  acronyms one case (`ID`, `URL`, `HTTP`), receivers one or two letters and
  the same across all methods, no `Get` prefix on getters.
- Generics only where they remove a real duplicate; never to avoid writing
  an interface.

## 4. Correctness and performance

- Slices: preallocate with `make([]T, 0, n)` when `n` is known; never take
  the address of a loop variable before Go 1.22; a sub-slice shares memory
  with its parent, so copy before returning it from an API.
- Strings in loops use `strings.Builder`, not `+=`.
- `defer` in a loop runs at function end, not iteration end; hoist the
  loop body into a function.
- Comparisons of floats, times (`Equal`, not `==`) and errors (`errors.Is`)
  use the method made for them.
- Doc comments start with the name of the thing (`// Reader reads ...`)
  and every exported identifier has one.

## 5. Tests

- Table-driven with `t.Run(tc.name, ...)`; each case names what it checks.
- Helpers call `t.Helper()`; comparisons use `cmp.Diff` or
  `reflect.DeepEqual` with the diff in the failure message; no
  `if got != want { t.Errorf("fail") }` without values.
- `t.Parallel()` on tests that share nothing; `t.Cleanup` over manual
  teardown; `t.TempDir()` over `os.MkdirTemp`.
- Test the exported API from an external test package (`package foo_test`)
  unless an internal detail needs it.
- No sleeps to wait for goroutines; synchronize on channels or use
  `synctest` where available.
- Benchmarks report `b.ReportAllocs()`; a performance claim in the message
  cites `benchstat` output.
