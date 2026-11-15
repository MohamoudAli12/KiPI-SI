(dc-solving)=
# Solving

## Solve all, report and Cancel

**Solve all** saves the setup, meshes every ticked net group and solves the power tree. It is disabled while there are problems (listed in red). If you click it while the 3D view is still building nets, the solve is queued and starts as soon as that finishes.

Once there are results, after a solve or with saved results opened, click **Report** to write `<board>_kipi_si_report_<date>_<time>.html` of them in the `kipi_si_reports` folder next to the board; the time stamp keeps each report instead of overwriting the last one. It opens in your web browser when it is written, and **Open report** opens it again later. The report is a single offline file with every table, an interactive 3D view of each net group, per-layer statistics and maps, and the temperature map. Over each 3D view, a tickbox per copper layer (and one for the vias) hides or shows that layer in the view and its voltage and current-density maps; the 3D views attached to a PDF report have them too.

Choose **PDF** beside **Report** for a `.pdf` to print or attach instead. It has the same tables and maps, without the sortable columns. It opens in your PDF viewer. Its **User notes** box is a form field: click in it and type in Acrobat, a web browser, Preview or most other PDF viewers, then save the PDF to keep the notes in it. Printed, it is an empty box to write in.

A PDF can't show the interactive 3D views, so they travel inside it: a web page of their own, `<report>_3d.html`, attached to the PDF (nothing extra is written next to it). The **3D Results View** link at the top of the report, and the one under each net group, opens it in your web browser: click the link in Acrobat, Foxit or PDF-XChange, or double-click the paperclip beside it in Firefox or Okular. It is also in the viewer's attachments panel, which Acrobat opens the PDF on; Chrome's and Edge's own viewers and macOS Preview mostly don't, so there save the PDF and open it in one that does, or extract the attachment with a PDF tool. The static views stay in the PDF either way. It adds about 1–2 MB to the PDF. Should the page fail to go in, KiPI-SI saves it beside the PDF instead, and the links open it there.

The report's **Pins** section, and `_pins.csv` in **Export ▾ Tables as CSV…**, list every pin each group was solved with. That covers VRM output, phase, input and sense pins, load supply and ground pins, and DC connection pins. Each row gives the pin's position, voltage, drop or boost from the VRM regulated voltage (0 V for a ground), and current. The current is what the pin draws from the copper, so it is negative where current is delivered into the copper, as at a VRM output. VRM output pin currents are solved, so they show how the current shares between the pins. A load's current is split equally across its pins, as the solver applies it, and a DC connection's current across the pins on each side.

A solve that fails on a setup problem (e.g. no copper path) shows **Cannot solve** in the Notes tab with the reason. Untick the group with the problem in the Solve tab to solve the rest.
