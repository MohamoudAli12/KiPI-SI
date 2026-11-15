(ac-solving)=
# Solving a rail

## Rail, Ground and Solve rail

Below the tabs: **Rail** lists each VRM and its output net; **Ground** lists the ticked nets with grounds first, defaulting to the VRM's ground pins' net. **Solve rail** saves the setup and runs the sweep; problems that stop it are listed in red above. The log shows the field solves as they go.

Click **Report** next to **Solve rail** to write `<board>_<rail>_ac_report_<date>_<time>.html` (or, with **PDF** chosen, `.pdf`) of the shown rail's results in the `kipi_si_reports` folder next to the board, once it is solved or its saved results are opened; the report opens when it is written, and **Open report** opens the shown rail's report again later. See {ref}`AC report <ac-report>`.

Each rail keeps its last result: switch **Rail** to look at another rail's curves without solving again. If you change the rail while a solve is running, the result is kept for its own rail and the notes say so.
