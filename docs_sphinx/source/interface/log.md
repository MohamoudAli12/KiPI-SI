(log)=
# Log and progress

## The Log dock

The bottom dock shows the current stage, a progress bar, and **Cancel**, which stops the running task (loading, building nets or solving). The log streams every stage with its timing, solver residuals and warnings: warnings are amber, errors red, stage headers blue.

While anything runs, the right end of the status bar shows a turning spinner with the operation and how long it has taken so far (part 3D models loading in the background included). The spinner keeps turning while KiPI-SI works; a stage that cannot say how far it is moves the progress bar back and forth instead. While the window itself is busy, drawing a big solve's results or saving a snapshot, the mouse pointer shows the wait cursor.

Each session also writes a log file to `kipi_si/` in your temporary folder (`%TEMP%` on Windows, `$TMPDIR` on macOS, `/tmp` on Linux). See {ref}`Troubleshooting <troubleshooting>`.
