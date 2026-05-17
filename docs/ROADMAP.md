# Roadmap

## v0.1.0-alpha (released May 2026)

- Headless 6DoF pose streaming via WebSocket
- Serial-keyed flat JSON format
- HTTP file server + static tool hosting
- Robotics visualiser (top-down + 3D)
- Tracker role assignment (setup.html)
- Recorder — record, playback, export CSV/JSON
- Measurement tool — live distance and angle
- Calibration tool — origin + named anchors + zones
- MCP server (vut-mcp) — Claude Code integration
- ACCURACY.md — validated noise floor measurement
- PLATFORM.md — OpenXR investigation findings

## v0.2 (in progress)

- HTTP endpoint routing hardening (`_clean_path`)
- Prominent error banners across all tools
- vut-mcp anchor tools (`get_anchors`, `distance_to_anchor`)
- PyPI package (`pip install vut-sdk`)

## Future

- Tracking map quality indicator
    Surface coverage score, dead zone detection,
    environment setup guidance in first-run wizard
- vut-skeleton-mcp — skeleton joint data via MCP
- Linux via Monado OpenXR runtime
- ROS bridge (vut_ros package)
- PyPI package publication (vut-sdk on PyPI)
- anchor_to_anchor_distance MCP tool
