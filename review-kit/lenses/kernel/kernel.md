# Linux Kernel Lens

What a reviewer checks on a kernel patch, on top of `lenses/c/c.md`.
Baseline: `Documentation/process/coding-style.rst`,
`Documentation/process/submitting-patches.rst` and the subsystem's own
rules. `scripts/checkpatch.pl` is the configured `reviewkit.lintCmd`, and
`reviewkit.requireTrailers` lists `Signed-off-by`.

## 1. The patch

- One logical change per patch, bisectable: every patch in the series
  builds and boots on its own. A rename and a behavior change are two
  patches. A fix found while writing a feature goes first, on its own.
- Subject: `subsystem: imperative summary` under 75 columns, the prefix
  matching `git log --oneline -- <path>` for that file.
- Body: what is wrong today, why, and how the patch fixes it, wrapped at
  75 columns, in the imperative. A user-visible symptom quotes the oops,
  warning or wrong output.
- Trailers: `Signed-off-by` (DCO) from everyone who handled the patch;
  `Fixes: <12+ hex> ("subject")` for a regression fix;
  `Cc: stable@vger.kernel.org` when it must reach stable; `Reported-by`,
  `Closes:` or `Link:` for a report; `Reviewed-by`, `Tested-by` and
  `Acked-by` kept verbatim across versions.
- AI and other tools (Documentation/process/coding-assistants.rst and
  generated-content.rst): an AI agent never adds `Signed-off-by`, and
  neither does a `Co-developed-by` name one; only a human certifies the
  DCO, after reviewing and understanding every line. When a tool wrote a
  meaningful part of the code or the changelog, or found the bug, the
  changelog or cover letter says so: which tools, the prompts or a summary
  of them, which portions they affected, and how the change was tested.
  Mainline defines no trailer for this; follow the maintainer's preference
  where a subsystem has one. Reformatting and identifier completion are out
  of scope. `scripts/gate.py` enforces the DCO half: in a kernel tree its
  message check blocks only DCO trailers naming an AI tool.
- A bug found by a tool comes with a reproducer, a fix that builds without
  new warnings and passes checkpatch, a `Fixes:` tag, and an explicit note
  of whatever could not be built or tested.
- A new version carries a changelog below the `---` line, not in the
  message. The cover letter says what the series does as a whole.
- `scripts/get_maintainer.pl` picks the recipients; the patch touches no
  file outside the subsystem without that maintainer in Cc.

## 2. Style

- Tabs of 8, 80 columns (`reviewkit.maxCols 80`), K&R braces, one
  statement per line, `switch` cases at the same indent as the `switch`.
- No `typedef` for structs or pointers; `lowercase_with_underscores`
  names; `static` for everything file-local; no `extern` in a `.c` file.
- Fixed types from the kernel (`u32`, `__le32`, `__user`), never
  `uint32_t` outside uAPI headers; `sizeof(*ptr)` over `sizeof(struct x)`.
- `kzalloc` or `kcalloc` with `struct_size()`, `array_size()` and
  `check_add_overflow()` for every computed size; `strscpy` over `strcpy`
  and `strlcpy`; no VLA.
- Headers have include guards and include what they use; a `.c` file
  includes its own header first.
- Comments say why; the file-top comment carries the SPDX line.

## 3. Errors and resources

- Return a negative `errno`; `ERR_PTR()`/`IS_ERR()` where a pointer is
  returned; never `-1`, never a bool for a fallible operation.
- Unwind with `goto` labels in reverse order of acquisition; `devm_*`
  managed resources where a device owns them, and then no manual free.
- `BUG_ON` only where continuing corrupts memory or data; recoverable
  invariants use `WARN_ON_ONCE` and an error path. No `BUG()` in drivers.
- Every allocation and every `copy_from_user` result is checked; user
  pointers carry `__user` and are only read through the `copy_*_user`,
  `get_user`/`put_user` helpers.
- Endianness conversions at the boundary only (`le32_to_cpu` once, then a
  CPU-order variable); sparse (`make C=1`) is clean.

## 4. Locking and context

- Every lock has a comment stating what it protects, and every accessor
  that needs it holds it or asserts it (`lockdep_assert_held`).
- No sleeping (`mutex_lock`, `GFP_KERNEL`, `msleep`) in atomic context:
  interrupt handlers, spinlock sections, RCU read sides. `GFP_ATOMIC` only
  where sleeping is impossible, with a comment.
- RCU readers are bounded and never block; updates use the matching
  `rcu_assign_pointer`/`rcu_dereference` pair and a grace period before
  freeing.
- Interrupt handlers do the minimum and defer to a threaded handler,
  workqueue or tasklet; shared state with the handler is protected by the
  same lock the handler takes.

## 5. Interfaces

- uAPI (`include/uapi/`, sysfs, ioctl numbers, netlink) is forever: no
  renames, no reordered fields, padding explicit, documented in
  `Documentation/ABI/`. A new interface adds its documentation in the same
  series.
- Logging: `pr_fmt` defined, `dev_*` with the device where one exists,
  rate-limited in paths user input can trigger, no printk in a hot path.
- `CONFIG_` gating for optional code with `IS_ENABLED()` over `#ifdef`
  where it compiles either way; `__init`/`__exit` on probe-time code;
  `EXPORT_SYMBOL_GPL` only for symbols another module needs.
- A behavior change comes with a kselftest or KUnit test where the
  subsystem has them, and the message says how it was tested (which
  hardware, which config, which test).
- The test build has `CONFIG_KASAN` and `CONFIG_UBSAN` on, and
  `CONFIG_PROVE_LOCKING` (lockdep). A change to locking, RCU or data
  shared between CPUs also runs in a second build with `CONFIG_KCSAN` and
  without `CONFIG_KASAN`: Kconfig makes KCSAN depend on `!KASAN`. The
  message names the configs the tests ran with.
