import React from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StarRatingProps {
    value: number;
    onChange?: (value: number) => void;
    max?: number;
    size?: 'sm' | 'md' | 'lg';
    readonly?: boolean;
    showLabel?: boolean;
    label?: string;
}

const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
};

const ratingLabels: Record<number, string> = {
    1: 'Poor',
    2: 'Fair',
    3: 'Good',
    4: 'Very Good',
    5: 'Excellent'
};

export function StarRating({
    value,
    onChange,
    max = 5,
    size = 'md',
    readonly = false,
    showLabel = false,
    label
}: StarRatingProps) {
    const [hoverValue, setHoverValue] = React.useState(0);

    const handleClick = (rating: number) => {
        if (!readonly && onChange) {
            onChange(rating);
        }
    };

    const handleMouseEnter = (rating: number) => {
        if (!readonly) {
            setHoverValue(rating);
        }
    };

    const handleMouseLeave = () => {
        setHoverValue(0);
    };

    const displayValue = hoverValue || value;
    const displayLabel = ratingLabels[displayValue] || '';

    return (
        <div className="space-y-1">
            {label && (
                <label className="text-sm font-medium text-foreground">{label}</label>
            )}
            <div className="flex items-center gap-1">
                <div
                    className={cn(
                        "flex items-center gap-0.5",
                        !readonly && "cursor-pointer"
                    )}
                    onMouseLeave={handleMouseLeave}
                >
                    {Array.from({ length: max }, (_, i) => {
                        const rating = i + 1;
                        const isFilled = rating <= displayValue;

                        return (
                            <button
                                key={rating}
                                type="button"
                                onClick={() => handleClick(rating)}
                                onMouseEnter={() => handleMouseEnter(rating)}
                                disabled={readonly}
                                className={cn(
                                    "transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-sm",
                                    !readonly && "hover:scale-110 transition-transform",
                                    readonly && "cursor-default"
                                )}
                                aria-label={`Rate ${rating} out of ${max}`}
                            >
                                <Star
                                    className={cn(
                                        sizeClasses[size],
                                        "transition-colors",
                                        isFilled
                                            ? "fill-yellow-400 text-yellow-400"
                                            : "text-muted-foreground/40"
                                    )}
                                />
                            </button>
                        );
                    })}
                </div>
                {showLabel && displayValue > 0 && (
                    <span className="ml-2 text-sm text-muted-foreground">
                        {displayLabel}
                    </span>
                )}
            </div>
        </div>
    );
}

// Display-only version for showing average ratings
interface RatingDisplayProps {
    value: number;
    max?: number;
    size?: 'sm' | 'md' | 'lg';
    showValue?: boolean;
    count?: number;
}

export function RatingDisplay({
    value,
    max = 5,
    size = 'sm',
    showValue = true,
    count
}: RatingDisplayProps) {
    const fullStars = Math.floor(value);
    const hasHalfStar = value - fullStars >= 0.5;

    return (
        <div className="flex items-center gap-1.5">
            <div className="flex items-center gap-0.5">
                {Array.from({ length: max }, (_, i) => {
                    const isFull = i < fullStars;
                    const isHalf = i === fullStars && hasHalfStar;

                    return (
                        <Star
                            key={i}
                            className={cn(
                                sizeClasses[size],
                                isFull || isHalf
                                    ? "fill-yellow-400 text-yellow-400"
                                    : "text-muted-foreground/30"
                            )}
                        />
                    );
                })}
            </div>
            {showValue && (
                <span className="text-sm font-medium text-foreground">
                    {value.toFixed(1)}
                </span>
            )}
            {count !== undefined && (
                <span className="text-sm text-muted-foreground">
                    ({count})
                </span>
            )}
        </div>
    );
}
