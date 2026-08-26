"""Everything that runs the lab: checkpoints, telemetry config, traffic, checks, tests.

Participants never import from here. It is a package so that `workshop.scripts.*`
and `workshop.tests.*` resolve from the repository root, which is what the
containers mount at /workspace.
"""
