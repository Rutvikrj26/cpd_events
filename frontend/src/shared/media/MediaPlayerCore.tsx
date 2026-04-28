/**
 * MediaPlayerCore — wraps an HTML5/YouTube/HLS media element with
 * Media Chrome's accessible web-component controls.
 *
 * Why Media Chrome over hand-rolled controls or react-player's
 * `controls={true}`:
 *   - react-player v3 is intentionally chromeless; their own docs
 *     recommend Media Chrome for custom UI. `controls={true}` falls
 *     back to native browser chrome (different on every browser, and
 *     YouTube embeds show the YouTube chrome with logo + suggestions).
 *   - Media Chrome ships keyboard shortcuts (space / k / j / l / m / f /
 *     0–9 / arrows / < >), tooltips, ARIA roles, captions menu, PiP,
 *     fullscreen, preview thumbnails — all accessible by default.
 *   - One control bar styled via CSS variables works across MP4,
 *     YouTube, and HLS sources via slot-swappable media elements.
 *
 * Why we keep a thin wrapper instead of inlining at every call site:
 *   - Source-kind discrimination (file / youtube / hls) lives in one
 *     place rather than duplicated across `VideoContentViewer`,
 *     `LessonViewer`, and `EventRecordingPage`.
 *   - The slotted media element exposes `currentTime` / `play` / etc.
 *     via a forwarded ref so the transcript and resume-position hook
 *     can drive playback uniformly.
 *
 * The youtube-video-element / hls-video-element packages are pulled
 * in transitively by react-player; we import their side-effect modules
 * here so `<youtube-video>` / `<hls-video>` register as custom elements.
 */

import { forwardRef, useEffect, useRef } from 'react';
import 'media-chrome';
import 'youtube-video-element';
import 'hls-video-element';
import {
    MediaController,
    MediaControlBar,
    MediaPlayButton,
    MediaSeekBackwardButton,
    MediaSeekForwardButton,
    MediaTimeRange,
    MediaTimeDisplay,
    MediaMuteButton,
    MediaVolumeRange,
    MediaPipButton,
    MediaFullscreenButton,
    MediaCaptionsButton,
    MediaLoadingIndicator,
} from 'media-chrome/react';
import {
    MediaPlaybackRateMenu,
    MediaPlaybackRateMenuButton,
} from 'media-chrome/react/menu';

import type { MediaSource } from './types';

interface MediaPlayerCoreProps {
    source: MediaSource;
    /** Auto-play on mount. Browsers may block without prior user gesture. */
    autoPlay?: boolean;
    /** Forwarded to the wrapper container. */
    className?: string;
}

/**
 * Type-augment JSX to recognize the custom elements we slot into the
 * media-controller. Both packages ship their own custom-element
 * definitions but no React JSX types out-of-the-box.
 */
declare module 'react' {
    namespace JSX {
        interface IntrinsicElements {
            'youtube-video': React.DetailedHTMLProps<
                React.VideoHTMLAttributes<HTMLVideoElement> & { slot?: string },
                HTMLVideoElement
            >;
            'hls-video': React.DetailedHTMLProps<
                React.VideoHTMLAttributes<HTMLVideoElement> & { slot?: string },
                HTMLVideoElement
            >;
        }
    }
}

export const MediaPlayerCore = forwardRef<HTMLVideoElement, MediaPlayerCoreProps>(
    function MediaPlayerCore({ source, autoPlay = false, className }, ref) {
        // Local ref kept in sync with the parent ref via a useEffect — the
        // underlying `<video>` / `<youtube-video>` / `<hls-video>` element
        // mounts inside the slot, and forwarding the ref directly works
        // because all three are HTMLVideoElement-compatible.
        const innerRef = useRef<HTMLVideoElement>(null);

        useEffect(() => {
            if (typeof ref === 'function') ref(innerRef.current);
            else if (ref) ref.current = innerRef.current;
        });

        const sharedProps = {
            ref: innerRef,
            slot: 'media',
            src: source.url,
            poster: source.poster,
            crossOrigin: '',
            playsInline: true,
            autoPlay,
        } as const;

        let mediaElement: React.ReactElement;
        if (source.kind === 'youtube') {
            mediaElement = <youtube-video {...sharedProps} />;
        } else if (source.kind === 'hls') {
            mediaElement = <hls-video {...sharedProps} />;
        } else {
            mediaElement = <video {...sharedProps} />;
        }

        return (
            <MediaController className={className} style={{ width: '100%', height: '100%', aspectRatio: '16 / 9' }}>
                {mediaElement}
                <MediaLoadingIndicator slot="centered-chrome" noAutohide />
                <MediaControlBar>
                    <MediaPlayButton />
                    <MediaSeekBackwardButton seekOffset={10} />
                    <MediaSeekForwardButton seekOffset={10} />
                    <MediaTimeRange />
                    <MediaTimeDisplay showDuration />
                    <MediaMuteButton />
                    <MediaVolumeRange />
                    <MediaPlaybackRateMenu hidden anchor="auto" />
                    <MediaPlaybackRateMenuButton />
                    <MediaCaptionsButton />
                    <MediaPipButton />
                    <MediaFullscreenButton />
                </MediaControlBar>
            </MediaController>
        );
    },
);
