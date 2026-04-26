import { useEffect, useMemo, useRef, useState } from "react";
import { FlipHorizontal2, Loader2, RotateCw, Sparkles } from "lucide-react";
import { useLocalParticipant } from "@livekit/components-react";
import { LocalVideoTrack, Track } from "livekit-client";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface ImageTransform {
    flipH: boolean;
    rotate: 0 | 90 | 180 | 270;
}

const IDENTITY_TRANSFORM: ImageTransform = { flipH: false, rotate: 0 };

/**
 * Bake a user transform (horizontal flip + 90° rotation) into the source
 * image and return a blob URL that the VirtualBackground processor can load.
 *
 * Why this exists: the local self-view is mirrored by the browser/WebRTC
 * layer (so the user sees themselves naturally), which makes any text on a
 * static background read backwards in the local preview. Other participants
 * see it correctly. The flip control lets the user pre-flip their image so
 * their own preview matches what others see.
 */
function bakeTransformedImage(srcUrl: string, transform: ImageTransform): Promise<string> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
            const canvas = document.createElement("canvas");
            const swapDims = transform.rotate === 90 || transform.rotate === 270;
            canvas.width = swapDims ? img.height : img.width;
            canvas.height = swapDims ? img.width : img.height;
            const ctx = canvas.getContext("2d");
            if (!ctx) return reject(new Error("canvas 2d unsupported"));

            ctx.translate(canvas.width / 2, canvas.height / 2);
            if (transform.rotate) ctx.rotate((transform.rotate * Math.PI) / 180);
            if (transform.flipH) ctx.scale(-1, 1);
            ctx.drawImage(img, -img.width / 2, -img.height / 2);

            canvas.toBlob((blob) => {
                if (!blob) return reject(new Error("toBlob failed"));
                resolve(URL.createObjectURL(blob));
            }, "image/png");
        };
        img.onerror = () => reject(new Error("failed to load image"));
        img.src = srcUrl;
    });
}

type EffectKind = "none" | "blur-light" | "blur-strong" | "image";

interface PresetBackground {
    id: string;
    label: string;
    /** CSS background for the tile (matches what the processor will use). */
    cssGradient: string;
    /** Two-stop gradient drawn into a 1920×1080 canvas at runtime. */
    stops: [string, string];
}

// Built-in backgrounds — runtime-generated gradients so we don't ship image
// assets. Replace with photographic JPGs in /public/video-backgrounds/ and
// switch back to file-based presets when product is ready.
const PRESET_BACKGROUNDS: PresetBackground[] = [
    { id: "soft",  label: "Soft",  cssGradient: "linear-gradient(135deg, #1f7a4d 0%, #0a3d28 100%)", stops: ["#1f7a4d", "#0a3d28"] },
    { id: "warm",  label: "Warm",  cssGradient: "linear-gradient(135deg, #d97706 0%, #7c2d12 100%)", stops: ["#d97706", "#7c2d12"] },
    { id: "cool",  label: "Cool",  cssGradient: "linear-gradient(135deg, #475569 0%, #1e293b 100%)", stops: ["#475569", "#1e293b"] },
];

/**
 * Render a 1920x1080 gradient image for use as a virtual background.
 * Returns a blob: URL that the VirtualBackground processor can load.
 */
function buildGradientImageUrl(stops: [string, string]): Promise<string> {
    return new Promise((resolve, reject) => {
        const canvas = document.createElement("canvas");
        canvas.width = 1920;
        canvas.height = 1080;
        const ctx = canvas.getContext("2d");
        if (!ctx) return reject(new Error("canvas 2d unsupported"));
        const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        grad.addColorStop(0, stops[0]);
        grad.addColorStop(1, stops[1]);
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
            if (!blob) return reject(new Error("toBlob failed"));
            resolve(URL.createObjectURL(blob));
        }, "image/png");
    });
}

export function BackgroundEffectsPicker() {
    const { localParticipant } = useLocalParticipant();
    const [effect, setEffect] = useState<EffectKind>("none");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [supported, setSupported] = useState<boolean | null>(null);
    const [open, setOpen] = useState(false);
    const [activeBgId, setActiveBgId] = useState<string | null>(null);
    /** Original (untransformed) image as user uploaded it. */
    const [customImageOrigUrl, setCustomImageOrigUrl] = useState<string | null>(null);
    /** Transformed blob currently fed to VirtualBackground. */
    const customBakedUrlRef = useRef<string | null>(null);
    const [customTransform, setCustomTransform] = useState<ImageTransform>(IDENTITY_TRANSFORM);

    const fileInputId = useMemo(() => `bg-upload-${Math.random().toString(36).slice(2, 8)}`, []);

    // Check browser support once.
    useEffect(() => {
        let cancelled = false;
        import("@livekit/track-processors")
            .then((m) => {
                if (cancelled) return;
                setSupported(m.supportsBackgroundProcessors?.() ?? false);
            })
            .catch(() => { if (!cancelled) setSupported(false); });
        return () => { cancelled = true; };
    }, []);

    // Revoke blob URLs we created when the picker unmounts. Original upload
    // lives until the user picks another file; the baked URL is replaced
    // every time the transform changes.
    useEffect(() => {
        return () => {
            if (customImageOrigUrl?.startsWith("blob:")) URL.revokeObjectURL(customImageOrigUrl);
            if (customBakedUrlRef.current?.startsWith("blob:")) URL.revokeObjectURL(customBakedUrlRef.current);
        };
    }, [customImageOrigUrl]);

    function getCameraTrack(): LocalVideoTrack | null {
        const pub = localParticipant.getTrackPublication(Track.Source.Camera);
        const track = pub?.track;
        return track instanceof LocalVideoTrack ? track : null;
    }

    async function applyEffect(next: EffectKind, opts: { bgId?: string | null; imageSrc?: string | null } = {}) {
        const track = getCameraTrack();
        if (!track) {
            setError("Camera not on yet — turn camera on first.");
            return;
        }

        setBusy(true);
        setError(null);
        try {
            const m = await import("@livekit/track-processors");

            if (next === "none") {
                await track.stopProcessor();
            } else if (next === "blur-light" || next === "blur-strong") {
                const blurRadius = next === "blur-light" ? 8 : 18;
                const proc = m.BackgroundBlur(blurRadius);
                await track.setProcessor(proc);
            } else if (next === "image" && opts.imageSrc) {
                const proc = m.VirtualBackground(opts.imageSrc);
                await track.setProcessor(proc);
            }

            setEffect(next);
            setActiveBgId(next === "image" ? (opts.bgId ?? null) : null);
            setOpen(false);
        } catch (e: any) {
            console.error(e);
            setError(e?.message || "Couldn't apply effect");
        } finally {
            setBusy(false);
        }
    }

    async function applyPresetGradient(bg: PresetBackground) {
        try {
            const url = await buildGradientImageUrl(bg.stops);
            await applyEffect("image", { bgId: bg.id, imageSrc: url });
        } catch (e: any) {
            setError(e?.message || "Couldn't render background");
        }
    }

    async function applyCustomImage(origUrl: string, transform: ImageTransform) {
        try {
            const baked = await bakeTransformedImage(origUrl, transform);
            // Free the previous baked URL before replacing.
            if (customBakedUrlRef.current?.startsWith("blob:")) URL.revokeObjectURL(customBakedUrlRef.current);
            customBakedUrlRef.current = baked;
            await applyEffect("image", { bgId: "custom", imageSrc: baked });
        } catch (e: any) {
            setError(e?.message || "Couldn't transform image");
        }
    }

    async function handleCustomFile(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        // reset input so the same file can be re-selected later
        e.target.value = "";
        if (!file) return;
        if (!file.type.startsWith("image/")) {
            setError("Please pick an image file.");
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            setError("Image is over 10 MB — please pick a smaller file.");
            return;
        }
        // Free any previous source URL we owned (baked URL handled by applyCustomImage)
        if (customImageOrigUrl?.startsWith("blob:")) URL.revokeObjectURL(customImageOrigUrl);
        const orig = URL.createObjectURL(file);
        setCustomImageOrigUrl(orig);
        const transform = IDENTITY_TRANSFORM;
        setCustomTransform(transform);
        await applyCustomImage(orig, transform);
    }

    /** Re-bake the current custom image with a new transform. */
    async function updateCustomTransform(next: ImageTransform) {
        if (!customImageOrigUrl) return;
        setCustomTransform(next);
        await applyCustomImage(customImageOrigUrl, next);
    }

    if (supported === false) {
        // Don't render the button at all if the browser can't run the processors.
        return null;
    }

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5"
                    disabled={busy || supported === null}
                    title="Background effects"
                >
                    {busy ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                    )}
                    Effects
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-3 space-y-2" align="end">
                <p className="text-xs text-muted-foreground">
                    Background. Applies to your camera feed only.
                </p>
                <div className="grid grid-cols-3 gap-2">
                    <EffectTile
                        label="None"
                        active={effect === "none"}
                        onClick={() => applyEffect("none")}
                    />
                    <EffectTile
                        label="Blur"
                        active={effect === "blur-light"}
                        onClick={() => applyEffect("blur-light")}
                    />
                    <EffectTile
                        label="Strong blur"
                        active={effect === "blur-strong"}
                        onClick={() => applyEffect("blur-strong")}
                    />
                </div>
                <p className="text-xs text-muted-foreground pt-1">Backgrounds</p>
                <div className="grid grid-cols-4 gap-2">
                    {PRESET_BACKGROUNDS.map((bg) => (
                        <GradientTile
                            key={bg.id}
                            label={bg.label}
                            background={bg.cssGradient}
                            active={effect === "image" && activeBgId === bg.id}
                            onClick={() => applyPresetGradient(bg)}
                        />
                    ))}
                    <CustomUploadTile
                        fileInputId={fileInputId}
                        active={effect === "image" && activeBgId === "custom"}
                        previewUrl={customImageOrigUrl}
                        onFile={handleCustomFile}
                    />
                </div>
                {effect === "image" && activeBgId === "custom" && customImageOrigUrl && (
                    <div className="flex items-center gap-2 pt-1 border-t border-border">
                        <span className="text-xs text-muted-foreground flex-1">Adjust your image</span>
                        <Button
                            size="sm"
                            variant={customTransform.flipH ? "default" : "outline"}
                            className="h-7 px-2 gap-1"
                            onClick={() => updateCustomTransform({ ...customTransform, flipH: !customTransform.flipH })}
                            title="Flip horizontally"
                            disabled={busy}
                        >
                            <FlipHorizontal2 className="h-3 w-3" /> Flip
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 gap-1"
                            onClick={() => updateCustomTransform({
                                ...customTransform,
                                rotate: ((customTransform.rotate + 90) % 360) as 0 | 90 | 180 | 270,
                            })}
                            title="Rotate 90°"
                            disabled={busy}
                        >
                            <RotateCw className="h-3 w-3" /> Rotate
                        </Button>
                    </div>
                )}
                {error && <p className="text-xs text-destructive">{error}</p>}
            </PopoverContent>
        </Popover>
    );
}

function EffectTile({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "h-16 rounded-md border text-xs font-medium flex items-center justify-center transition-colors",
                "hover:bg-accent",
                active ? "border-primary bg-primary/10" : "border-border bg-background",
            )}
        >
            {label}
        </button>
    );
}

function GradientTile({ label, background, active, onClick }: { label: string; background: string; active: boolean; onClick: () => void }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "relative h-16 rounded-md overflow-hidden border transition-colors",
                "hover:opacity-90",
                active ? "border-primary ring-2 ring-primary/40" : "border-border",
            )}
            style={{ background }}
            title={label}
        >
            <span className="absolute inset-x-0 bottom-0 bg-black/40 text-white text-[10px] py-0.5 text-center">
                {label}
            </span>
        </button>
    );
}

function CustomUploadTile({
    fileInputId,
    active,
    previewUrl,
    onFile,
}: {
    fileInputId: string;
    active: boolean;
    previewUrl: string | null;
    onFile: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
    return (
        <>
            <label
                htmlFor={fileInputId}
                className={cn(
                    "relative h-16 rounded-md overflow-hidden border-2 border-dashed transition-colors cursor-pointer flex items-center justify-center",
                    "hover:bg-accent",
                    active ? "border-primary ring-2 ring-primary/40" : "border-border",
                )}
                title="Upload your own image"
                style={previewUrl && active ? { backgroundImage: `url(${previewUrl})`, backgroundSize: "cover", backgroundPosition: "center" } : undefined}
            >
                {!previewUrl || !active ? (
                    <span className="text-[10px] font-medium text-muted-foreground text-center px-1">
                        + Upload
                    </span>
                ) : null}
                <span className="absolute inset-x-0 bottom-0 bg-black/40 text-white text-[10px] py-0.5 text-center">
                    Custom
                </span>
            </label>
            <input
                id={fileInputId}
                type="file"
                accept="image/*"
                className="sr-only"
                onChange={onFile}
            />
        </>
    );
}
