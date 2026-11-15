# License

KiPI-SI is free software: you can redistribute it and/or modify it under the terms of the
[GNU General Public License](https://github.com/MohamoudAli12/KiPI-SI/blob/main/LICENSE) as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version. It is distributed WITHOUT
ANY WARRANTY; see the license for details. Copyright © 2026 Drew Maatman (KiPI) and
the KiPI-SI contributors.

**Note on the mesher.** KiPI-SI meshes copper with Jonathan Shewchuk's
[Triangle](https://www.cs.cmu.edu/~quake/triangle.html), through the
[`triangle`](https://pypi.org/project/triangle/) Python package. Triangle is not open source
in the OSI sense. Its author's terms allow free use and redistribution, but it **may not be
sold or included in commercial products without a license from its author**. Using KiPI-SI for
your own design work is fine. The meshing code is isolated in `kipi_si/core/mesh/` for this reason.

The other dependencies are under permissive licenses, apart from PySide6 (LGPL-3.0). All of
them are compatible with the GPL.

The author of KiPI-SI prohibits the package from inclusion in commercial software. Use it, fork it, and modify it to your heart's content.
