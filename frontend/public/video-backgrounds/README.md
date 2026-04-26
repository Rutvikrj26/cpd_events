# Video backgrounds

Drop landscape JPGs here to populate the **Effects → Backgrounds** picker in the
in-room video toolbar. Filenames must match the IDs declared in
`src/components/video/BackgroundEffectsPicker.tsx → PRESET_BACKGROUNDS`:

- `office.jpg`
- `library.jpg`
- `window.jpg`

Recommended: 1920×1080, JPEG, < 500 KB. The image is applied as a per-frame
virtual background via `@livekit/track-processors` (MediaPipe under the hood),
so larger files just slow first-paint without improving quality.

The blur effects (light / strong) work without any image assets.
