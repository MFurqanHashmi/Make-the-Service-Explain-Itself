# Implementation notes

The complete lab carries forward the real-Docker metrics validation findings:

- `check_metrics.py` uses a pre-window baseline for every grouped counter series, treating a series that did not exist before the traffic window as zero and handling counter resets after hot reload.
- `validate-full` restores starter code and stops Docker through an unconditional trap. It cannot leave the solved checkpoint in the participant tree.
- `./lab test` uses Python's standard-library `unittest`; pytest is not an undeclared dependency.
- Recovery starts stopped services idempotently, restores cumulative known-good code, generates fresh traffic, and checks the real backend.
- The old `validate-slice` command was removed. `validate-full` is the sole implementation gate.

The metrics slice has been validated on real Docker. The traces, structured-log translation, datasource correlations, and complete timing require `./lab validate-full` on the target participant platform before delivery because the build sandbox has no Docker daemon.
