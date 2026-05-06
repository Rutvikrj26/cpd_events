"""
Video provider factory.

Instantiates the configured video provider based on settings.VIDEO_PROVIDER.
"""

import logging

from django.conf import settings

from conferencing.provider import VideoProvider

logger = logging.getLogger(__name__)

_provider_instance: VideoProvider | None = None


def get_video_provider() -> VideoProvider:
    """Get the configured video provider singleton."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = getattr(settings, 'VIDEO_PROVIDER', 'livekit')

    if provider_name == 'livekit':
        from conferencing.providers.livekit import LiveKitProvider

        _provider_instance = LiveKitProvider()
    elif provider_name == 'zoom':
        from conferencing.providers.zoom import ZoomProvider

        _provider_instance = ZoomProvider()
    else:
        raise ValueError(f"Unknown video provider: {provider_name}")

    if not _provider_instance.is_configured():
        logger.warning("Video provider '%s' is not fully configured", provider_name)

    return _provider_instance
