/**
 * Shared cross-feature composites.
 *
 * Higher-level than `shared/ui/` primitives — these compose multiple
 * primitives into common app patterns (list-item card, calendar tile,
 * etc.). Use these instead of re-inventing layouts per feature.
 */
export { CardRow } from "./CardRow";
export type { CardRowProps } from "./CardRow";
export { AvatarTile } from "./AvatarTile";
export type { AvatarTileTone, AvatarTileSize, AvatarTileProps } from "./AvatarTile";
export { DateBlock } from "./DateBlock";
export type { DateBlockTone, DateBlockProps } from "./DateBlock";
