import * as React from "react";
import { Link } from "react-router-dom";
import { Card, type CardElevation, type CardProps } from "@/shared/ui/card";
import { cn } from "@/lib/utils";

/**
 * CardRow — horizontal "list item card" primitive.
 *
 * The single canonical layout for any card that puts a leading visual
 * (avatar, icon tile, date block) next to a title + subtitle and an
 * optional trailing slot (actions, arrow, status pill). Use this rather
 * than re-inventing flex-row + items-center per call site.
 *
 * Alignment defaults:
 *   - Leading and body are **top-aligned** so the heading reads at the
 *     same baseline as the leading visual's top. (items-center floated
 *     headings to mid-row when the leading was taller, which read as a
 *     bug.)
 *   - Trailing slot is **self-center** so action buttons stay balanced.
 *   - On mobile (`<sm`), the layout stacks vertically with no center
 *     ambiguity.
 *
 * Usage:
 *     <CardRow
 *         leading={<AvatarTile icon={GraduationCap} tone="success" />}
 *         title="Certificate"
 *         subtitle={`Issued ${date}`}
 *         trailing={<ArrowButton href="/certificates/abc" />}
 *     />
 */

interface CardRowProps extends Omit<CardProps, "children" | "title"> {
    leading?: React.ReactNode;
    /** Heading text. Required unless `body` is provided. */
    title?: React.ReactNode;
    subtitle?: React.ReactNode;
    /** Custom body content. If provided, `title` and `subtitle` are ignored. */
    body?: React.ReactNode;
    trailing?: React.ReactNode;
    /** Wrap the whole card in a Link. Mutually exclusive with `onClick`. */
    href?: string;
    /** Make the card clickable (uses div + role=button). */
    onClick?: () => void;
    /** Override default elevation. Defaults to `interactive` for clickable cards, `rest` otherwise. */
    elevation?: CardElevation;
    /**
     * Vertical alignment of the row. Default `start` aligns the heading
     * with the top of the leading visual. Use `center` only when leading
     * and body are guaranteed to be similar heights.
     */
    align?: "start" | "center";
    /** Compact padding (p-tight) vs default (p-card). */
    density?: "default" | "compact";
}

const CardRow = React.forwardRef<HTMLDivElement, CardRowProps>(
    (
        {
            leading,
            title,
            subtitle,
            body,
            trailing,
            href,
            onClick,
            elevation,
            align = "start",
            density = "default",
            className,
            ...rest
        },
        ref
    ) => {
        const isClickable = Boolean(href || onClick);
        const resolvedElevation = elevation ?? (isClickable ? "interactive" : "rest");

        const inner = (
            <div
                className={cn(
                    "flex flex-col gap-card sm:flex-row sm:gap-3",
                    align === "start" ? "sm:items-start" : "sm:items-center",
                    density === "compact" ? "p-tight" : "p-card"
                )}
            >
                {leading ? (
                    <div className="shrink-0">{leading}</div>
                ) : null}
                <div className={cn("min-w-0 flex-1", align === "start" && "sm:pt-0.5")}>
                    {body ?? (
                        <>
                            <div className="truncate text-body font-medium leading-snug text-foreground">
                                {title}
                            </div>
                            {subtitle ? (
                                <div className="mt-0.5 text-caption leading-snug text-muted-foreground">
                                    {subtitle}
                                </div>
                            ) : null}
                        </>
                    )}
                </div>
                {trailing ? (
                    <div className="flex shrink-0 items-center gap-tight sm:self-center">
                        {trailing}
                    </div>
                ) : null}
            </div>
        );

        const cardClassName = cn(
            "overflow-hidden",
            isClickable && "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
            className
        );

        if (href) {
            return (
                <Card ref={ref} elevation={resolvedElevation} className={cardClassName} {...rest}>
                    <Link to={href} className="block">
                        {inner}
                    </Link>
                </Card>
            );
        }

        if (onClick) {
            return (
                <Card
                    ref={ref}
                    elevation={resolvedElevation}
                    className={cardClassName}
                    role="button"
                    tabIndex={0}
                    onClick={onClick}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            onClick();
                        }
                    }}
                    {...rest}
                >
                    {inner}
                </Card>
            );
        }

        return (
            <Card ref={ref} elevation={resolvedElevation} className={cardClassName} {...rest}>
                {inner}
            </Card>
        );
    }
);
CardRow.displayName = "CardRow";

export { CardRow };
export type { CardRowProps };
