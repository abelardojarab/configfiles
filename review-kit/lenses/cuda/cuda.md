# CUDA Lens

What a reviewer checks in `.cu` and `.cuh` files, on top of
`lenses/cpp/cpp.md`. Baseline: the CUDA C++ Programming Guide and Best
Practices Guide (https://docs.nvidia.com/cuda/). The sweep treats CUDA
sources as C++.

## 1. Kernel contract

- The comment above every `__global__` function states the launch
  geometry it assumes (block size, how the grid is derived from the problem
  size), the units of each dimension, and which pointers may alias. Device
  pointers that do not alias are `const T* __restrict__`.
- Every kernel bounds-checks its index against the problem size
  (`if (i >= n) return;` or a grid-stride loop) and handles `n == 0`.
  Never assume the grid divides the problem.
- Block size is a `constexpr` or template parameter shared between the
  kernel and its launch; a literal `256` in both places is a finding.
- `__syncthreads()` is reached by every thread of the block or by none:
  never inside a branch or loop whose condition varies across the block.
  Early `return` before a later barrier is the same bug.
- Shared helpers are `__host__ __device__` and have one definition; no
  exceptions, no `std::` containers, no virtual dispatch in device code.

## 2. Errors and synchronization

- Every runtime or driver call goes through one checking macro
  (`CUDA_CHECK(cudaMalloc(...))`) that reports file, line and
  `cudaGetErrorString`. A bare call is a finding.
- After every launch: `cudaGetLastError()`. `cudaDeviceSynchronize()` only
  behind a debug flag or in tests; production code synchronizes on a
  stream or an event.
- Work is issued on an explicit stream passed in by the caller, never the
  legacy default stream; transfers overlap compute with `cudaMemcpyAsync`
  from pinned host memory. A `cudaMemcpy` in a hot path is a finding.
- Allocation in a loop is a finding: allocate once (or `cudaMallocAsync`
  from a pool) and reuse; library handles (cuBLAS, cuDNN, cuFFT) are
  created once and bound to the stream.
- No deprecated API (`cudaThreadSynchronize`, `cudaMemcpyToSymbol` of a
  non-constant, the `<<<>>>` default-stream launch in library code).

## 3. Memory and performance

- Global memory access is coalesced: consecutive threads read consecutive
  addresses; structure-of-arrays over array-of-structures for hot data.
  A strided or scattered pattern needs a comment saying why.
- Shared memory indices avoid bank conflicts (pad the row when the stride
  is a multiple of 32 words); dynamic shared memory size is computed from
  the same constants as the kernel.
- Local arrays indexed by a runtime value spill to local memory; use
  compile-time indices, registers or shared memory.
- Reductions and scans use warp primitives with the full mask
  (`__shfl_down_sync(0xffffffff, ...)`), cooperative groups, or CUB/Thrust,
  before a hand-rolled loop of atomics. Atomics on one address from every
  thread is a finding.
- `double` only where the algorithm needs it; `fmaf`, `rsqrtf` and the
  fast-math intrinsics only with a comment on the accuracy trade.
- `__launch_bounds__` on kernels whose occupancy matters, and the message
  cites the register and shared-memory report (`-Xptxas -v`) or an `ncu`
  summary for a performance claim. "Faster" without numbers is a finding.
- Before and after numbers for a kernel change (`change_hygiene.md` §3)
  come from the same GPU, and the message says which. When the change can
  alter results (reordered math, a new precision, fast-math), it also shows
  the outputs still match the CPU reference within the tolerance of §5.
- A new kernel, or a change whose message claims a speedup, is benchmarked
  against the CPU implementation of the same operation when one already
  exists in the tree or earlier in the stack; never write a CPU version
  only to have something to compare. Use Google Benchmark at several
  sizes, including small ones where the CPU may win, after warm-up runs,
  timing the GPU with CUDA events. Count host-device copies or say they
  are excluded. The message names the CPU and GPU and the size at which
  the GPU starts to win, or says it never does in the range measured.

## 4. Portability

- Architecture-specific code is behind `__CUDA_ARCH__` guards with a
  fallback, and the build lists the `-gencode` targets the project ships.
  A feature needing a minimum compute capability says so where it is used.
- Host and device agree on struct layout: fixed-width types, explicit
  padding, `static_assert` on `sizeof` for structs crossed by `cudaMemcpy`.
- Unified memory is used knowingly: prefetch (`cudaMemPrefetchAsync`) and
  advise, with a comment on which side touches the data when.

## 5. Tests

- Every kernel has a test against a CPU reference on the same inputs, with
  a tolerance stated in ULPs or relative error, never exact float
  equality; NaN and infinity inputs are covered where they can occur.
- Sizes tested: `0`, `1`, one block minus one, one block plus one, and a
  size that is not a multiple of the block or warp.
- Tests run under `compute-sanitizer` (`memcheck`, `racecheck`,
  `initcheck`, `synccheck`) in CI or the message says they were run.
- A reduction that must be deterministic has a test that runs it twice and
  compares bit for bit; one that need not says so in its comment.
- Device tests check `cudaGetLastError()` after each launch so an
  asynchronous fault is attributed to the right kernel.
