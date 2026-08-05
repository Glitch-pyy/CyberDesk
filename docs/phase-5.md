# Phase 5: Desktop Plugin Foundation

Phase 5 introduces desktop plugins so data collection and serial formatting no
longer have to be hard-coded into the control panel. Phase 5.1 keeps this
foundation deliberately small: plugins are created explicitly in Python and
stored in a registry. Dynamic discovery and filesystem importing are not part
of this step.

## Plugin Interface

Every desktop plugin inherits from `DesktopPlugin` and provides:

- a stable `plugin_id` for registry lookup;
- a human-readable `display_name`;
- an `enabled` state;
- `collect()` for returning a structured data snapshot; and
- `format_serial_command()` for encoding that snapshot for the device.

`PluginRegistry` registers plugin instances, rejects duplicate IDs, retrieves
plugins by ID, lists all or only enabled plugins, and enables or disables a
registered plugin. It does not automatically import plugin files.

## System Metrics Plugin

`SystemMetricsPlugin` is the first plugin. It collects CPU usage, memory usage,
battery percentage, plugged-power state, hostname, and operating-system name
with `psutil` and the Python standard library. Battery fields are `None` on
systems without battery information.

The plugin continues to generate the existing `DESKTOP_UPDATE` command used in
Phase 4. Hostnames are sanitized and length-limited before formatting so text
cannot insert extra fields into the pipe-delimited serial message. The firmware
and its existing protocol are unchanged in Phase 5.1.

## Next Step

The next Phase 5 step will add generic firmware widget messages. Until then,
the desktop plugin foundation intentionally emits only the existing
`DESKTOP_UPDATE` message understood by the current firmware.
