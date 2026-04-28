"""Conferencing signal hooks.

The Zoom-model lifecycle has no eager VideoRoom creation — rooms are
provisioned on-demand when a host clicks **Start meeting** (see
``StartMeetingView``). This module is intentionally empty so the
``conferencing.apps`` ``ready()`` import keeps working; it stays
importable in case we add room-adjacent signals later (e.g. cleanup
hooks on Event delete).
"""
