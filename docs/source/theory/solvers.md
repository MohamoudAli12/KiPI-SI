(sg-solvers)=
# Linear solvers and PARDISO

Every analysis ends in a large sparse system of equations, one unknown per mesh node. DC and thermal systems are symmetric positive definite; AC systems are complex. How KiPI-SI solves them:

```{list-table}
:header-rows: 1
:class: kipi-table

* - Solver
  - How it works
  - Used for
* - SuperLU (SciPy)
  - A sparse direct solver: it factorizes the matrix once, then each right-hand side is a fast forward and back substitution. Single-threaded. Always installed.
  - Systems up to about 200k unknowns without PARDISO.
* - AMG-CG
  - Conjugate gradients, an iterative solver, preconditioned by algebraic multigrid (pyamg). Uses much less memory than a factorization, but has to iterate for every right-hand side.
  - DC and thermal systems above the direct limit.
* - PARDISO (Intel MKL)
  - A parallel sparse direct solver. It factorizes on every CPU core and handles complex systems too.
  - Up to 1M unknowns, if installed.
```

PARDISO is an optional install (the `pypardiso` package). Its benefits:

- **Speed on large boards.** Factorizing is the slow step, and PARDISO uses every core. On a 645k-unknown rail one solve drops from about 8 s to 1.2 s, and a four-pass electro-thermal run from about 90 s to 34 s.
- **A higher direct-solve limit.** With PARDISO, KiPI-SI factorizes systems of up to 1M unknowns instead of 200k. A factorization is reused for every load, power-tree iteration and AC port, which an iterative solver cannot do, so fine meshes stay fast.
- **AC sweeps.** Each field frequency of an AC sweep is a complex factorization, so large AC models gain the most.

The drawbacks: Intel MKL is about 600 MB installed, it exists only for x86-64 Windows and Linux (not macOS or ARM), and small boards, which solve in a second either way, gain little. KiPI-SI offers it, ticked, the first time it starts (or sets up, standalone) on a computer that can have it, and it can be turned down there or removed later under *About → Manage dependencies…*. KiPI-SI falls back to SuperLU on its own if PARDISO is missing, cannot load, or returns an inaccurate result, and the results are the same either way. Each factorization is checked by its backward error, the smallest relative change to the system that would make the solution exact; a working solve gives about 1e-16 however stiff the board's copper and vias make the system. Because PARDISO utilizes all cores, the machine running the simulation will really stretch its legs. Expect high CPU utilization and higher junction temperatures, at the gain of simulation speed. *About → Copy version info* says which solver is in use.
