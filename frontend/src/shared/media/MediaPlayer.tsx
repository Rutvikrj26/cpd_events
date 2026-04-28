/**
 * MediaPlayer — top-level orchestrator.
 *
 * Composes:
 *   1. <MediaPlayerCore>   — Media Chrome web-component-based player
 *                             (handles ALL controls, keyboard shortcuts,
 *                             tooltips, captions menu, PiP, fullscreen).
 *   2. <TranscriptPanel>   — optional, side-by-side ≥1280px or tabbed
 *                             below. Reads currentTime via a small
 *                             event-listener hook (Media Chrome's store
 *                             is available too but a direct listener
 *                             keeps the dependency surface small).
 *
 * Used by VideoContentViewer (course player), LessonViewer (course
 * player), and EventRecordingPage (recording viewer). One implementation
 * for all video surfaces.
 */

import { useEffect, useImperativeHandle, useRef, useState } from 'react';
import { forwardRef } from 'react';

import { cn } from '@/lib/utils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { MediaPlayerCore } from './MediaPlayerCore';
import { TranscriptPanel } from './transcript/TranscriptPanel';
import { useResumePosition } from './hooks/useResumePosition';
import { useMediaTime } from './hooks/useMediaTime';
import type {
    MediaPlayerHandle,
    MediaPlayerProps,
} from './types';

// 1280px is Tailwind's `xl` breakpoint and a comfortable threshold for
// putting a 380px panel beside a video without crushing either.
const SIDE_BY_SIDE_BREAKPOINT_PX = 1280;

function useViewportLayout(layoutProp: MediaPlayerProps['layout']): 'side-by-side' | 'tabs' {
    const [isWide, setIsWide] = useState(() =>
        typeof window !== 'undefined'
            ? window.innerWidth >= SIDE_BY_SIDE_BREAKPOINT_PX
            : true,
    );
    useEffect(() => {
        if (layoutProp && layoutProp !== 'auto') return;
        const mq = window.matchMedia(`(min-width: ${SIDE_BY_SIDE_BREAKPOINT_PX}px)`);
        const onChange = () => setIsWide(mq.matches);
        onChange();
        mq.addEventListener('change', onChange);
        return () => mq.removeEventListener('change', onChange);
    }, [layoutProp]);
    if (layoutProp === 'side-by-side') return 'side-by-side';
    if (layoutProp === 'tabs') return 'tabs';
    return isWide ? 'side-by-side' : 'tabs';
}

export const MediaPlayer = forwardRef<MediaPlayerHandle, MediaPlayerProps>(
    function MediaPlayer(
        {
            source,
            title,
            chapters: _chapters,
            transcript,
            layout = 'auto',
            onTimeUpdate,
            onComplete,
            completionThreshold = 0.95,
            initialPosition,
            storageKey,
            className,
            footer,
        },
        ref,
    ) {
        const videoRef = useRef<HTMLVideoElement>(null);
        const completedFiredRef = useRef(false);

        // Throttled time tracking for transcript sync + onTimeUpdate +
        // completion detection. Uses standard `timeupdate` event so it
        // doesn't depend on Media Chrome's internal store API.
        const { currentTime, duration } = useMediaTime(videoRef);
        useResumePosition(videoRef, { storageKey, initialPosition });

        // Imperative handle for parent control (transcript click-to-seek,
        // markComplete handlers, etc).
        useImperativeHandle(
            ref,
            () => ({
                play: async () => {
                    await videoRef.current?.play();
                },
                pause: () => videoRef.current?.pause(),
                seekTo: (s: number) => {
                    if (videoRef.current) videoRef.current.currentTime = s;
                },
                getCurrentTime: () => videoRef.current?.currentTime ?? 0,
                getElement: () => videoRef.current,
            }),
            [],
        );

        // Forward time updates.
        useEffect(() => {
            onTimeUpdate?.(currentTime);
        }, [currentTime, onTimeUpdate]);

        // Completion detection. Re-arms when user scrubs back behind threshold.
        useEffect(() => {
            if (!onComplete || duration <= 0) return;
            const ratio = currentTime / duration;
            if (ratio >= completionThreshold && !completedFiredRef.current) {
                completedFiredRef.current = true;
                onComplete();
            } else if (ratio < completionThreshold - 0.05) {
                completedFiredRef.current = false;
            }
        }, [currentTime, duration, onComplete, completionThreshold]);

        const showTranscript =
            !!transcript &&
            layout !== 'video-only' &&
            (transcript.slot ||
                transcript.isLoading ||
                transcript.errorMessage ||
                (transcript.segments && transcript.segments.length > 0));

        const effectiveLayout = useViewportLayout(layout);

        const transcriptNode = transcript ? (
            transcript.slot ?? (
                <TranscriptPanel
                    transcript={transcript}
                    currentMs={currentTime * 1000}
                    onSeek={(s) => {
                        if (videoRef.current) videoRef.current.currentTime = s;
                    }}
                    className="h-full"
                />
            )
        ) : null;

        const videoNode = (
            <MediaPlayerCore
                ref={videoRef}
                source={source}
                className="w-full overflow-hidden rounded-lg"
            />
        );

        // Suppress the otherwise-unused title warning; tooltip-only label.
        void title;

        if (!showTranscript) {
            return (
                <div className={cn('w-full', className)}>
                    {videoNode}
                    {footer && <div className="mt-3">{footer}</div>}
                </div>
            );
        }

        if (effectiveLayout === 'side-by-side') {
            // Inline grid template — arbitrary Tailwind classes with brackets
            // and commas don't always survive the v4 JIT scanner reliably.
            return (
                <div
                    className={cn('grid w-full gap-4', className)}
                    style={{ gridTemplateColumns: 'minmax(0, 1fr) 380px' }}
                >
                    <div className="min-w-0">
                        {videoNode}
                        {footer && <div className="mt-3">{footer}</div>}
                    </div>
                    <div className="h-full min-h-[400px]" style={{ maxHeight: 'calc(100vh - 8rem)' }}>
                        {transcriptNode}
                    </div>
                </div>
            );
        }

        // Tabbed layout — render the video pane as the default tab; the
        // transcript syncs in the background even when hidden, so jumping
        // back to it preserves your place.
        return (
            <div className={cn('w-full', className)}>
                <Tabs defaultValue="video" className="flex flex-col gap-3">
                    <TabsList className="self-start">
                        <TabsTrigger value="video">Video</TabsTrigger>
                        <TabsTrigger value="transcript">Transcript</TabsTrigger>
                    </TabsList>
                    <TabsContent value="video" className="mt-0">
                        {videoNode}
                        {footer && <div className="mt-3">{footer}</div>}
                    </TabsContent>
                    <TabsContent value="transcript" className="mt-0">
                        <div className="h-[60vh] min-h-[400px]">{transcriptNode}</div>
                    </TabsContent>
                </Tabs>
            </div>
        );
    },
);
