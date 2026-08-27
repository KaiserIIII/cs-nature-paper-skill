# Template layout

`v3/` is the only runtime source of truth for new V3.1 state. The files at
this directory's historical root are retained for V2/V3 compatibility tests and
older callers; they are not read by the V3.1 initializer. V2 templates copied
from the historical layout live under `assets/legacy/v2/` and are read only by
explicit migration commands.
