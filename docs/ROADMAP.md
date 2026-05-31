# Roadmap

## v0.1.0-alpha — Core SDK ✓
- ✓ Serial-stable WebSocket pose stream
- ✓ Robotics + body tracking visualisers
- ✓ Battery monitoring
- ✓ --fps flag (30/60/100Hz)
- ✓ Screenshots + demo videos in README

## v0.2.0-alpha — Developer Toolkit ✓
- ✓ Tracker role assignment UI
- ✓ Recorder + playback + CSV export
- ✓ Spatial measurement tool
- ✓ Calibration + named anchors
- ✓ MCP Server (Claude Code integration)
- ✓ examples/ (Python, Node.js, Unity, ROS stub)
- ✓ Installer .exe with component selection
- ✓ Legal audit — MIT, no proprietary content
- ✓ ACCURACY.md — 0.30mm RMS noise floor measured
- ✓ How-to guides in all tools

## v0.3.0-alpha — Hybrid Tracking ✓
- ✓ Space calibration — VUT + Lighthouse alignment (Kabsch transform, spacecal.html)
- ✓ Anchor drift correction — stationary LH tracker corrects VUT SLAM drift in real time
- ✓ Noise floor measurement tool (Measurement page → Noise Floor tab)
- ✓ 3D View — live 3D tracker visualisation with movement trails (view3d.html)

## v0.4 — Research Toolkit (next)
- Printed sheet calibration (NeuRA method)
- MessagePack encoding option
- Monado / Linux support
- ROS bridge
- Data quality metrics panel
- BVH / CSV / C3D / TRC export formats
- Sync markers (multi-modal studies)
- Trial protocol manager
- Accuracy benchmark tool
- vut-skeleton-mcp
- tools/triggers (spatial event system)
