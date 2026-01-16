import * as React from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export interface PaginationProps {
    page: number;
    totalPages: number;
    totalCount: number;
    pageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange?: (pageSize: number) => void;
    pageSizeOptions?: number[];
    showPageSizeSelector?: boolean;
    showSummary?: boolean;
    className?: string;
}

/**
 * Generate page numbers with ellipsis for large page counts.
 * Shows: first page, last page, current page, and neighbors.
 */
function getPageNumbers(current: number, total: number): (number | "ellipsis")[] {
    if (total <= 7) {
        return Array.from({ length: total }, (_, i) => i + 1);
    }

    const pages: (number | "ellipsis")[] = [];

    // Always show first page
    pages.push(1);

    // Calculate range around current page
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);

    // Add ellipsis if gap after first page
    if (start > 2) {
        pages.push("ellipsis");
    }

    // Add pages around current
    for (let i = start; i <= end; i++) {
        pages.push(i);
    }

    // Add ellipsis if gap before last page
    if (end < total - 1) {
        pages.push("ellipsis");
    }

    // Always show last page
    if (total > 1) {
        pages.push(total);
    }

    return pages;
}

export function Pagination({
    page,
    totalPages,
    totalCount,
    pageSize,
    onPageChange,
    onPageSizeChange,
    pageSizeOptions = [10, 20, 50, 100],
    showPageSizeSelector = false,
    showSummary = true,
    className,
}: PaginationProps) {
    if (totalPages <= 1 && !showSummary) {
        return null;
    }

    const startItem = (page - 1) * pageSize + 1;
    const endItem = Math.min(page * pageSize, totalCount);
    const pageNumbers = getPageNumbers(page, totalPages);

    return (
        <div
            className={cn(
                "flex flex-col sm:flex-row items-center justify-between gap-4 py-4",
                className
            )}
        >
            {/* Summary text */}
            {showSummary && (
                <div className="text-sm text-muted-foreground order-2 sm:order-1">
                    Showing <span className="font-medium">{startItem}</span> to{" "}
                    <span className="font-medium">{endItem}</span> of{" "}
                    <span className="font-medium">{totalCount}</span> results
                </div>
            )}

            {/* Page size selector */}
            {showPageSizeSelector && onPageSizeChange && (
                <div className="flex items-center gap-2 order-3 sm:order-2">
                    <span className="text-sm text-muted-foreground">Per page:</span>
                    <Select
                        value={String(pageSize)}
                        onValueChange={(value) => onPageSizeChange(Number(value))}
                    >
                        <SelectTrigger className="h-8 w-[70px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {pageSizeOptions.map((size) => (
                                <SelectItem key={size} value={String(size)}>
                                    {size}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            )}

            {/* Page navigation */}
            {totalPages > 1 && (
                <div className="flex items-center gap-1 order-1 sm:order-3">
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onPageChange(page - 1)}
                        disabled={page <= 1}
                    >
                        <ChevronLeft className="h-4 w-4" />
                        <span className="sr-only">Previous page</span>
                    </Button>

                    {pageNumbers.map((pageNum, idx) =>
                        pageNum === "ellipsis" ? (
                            <div
                                key={`ellipsis-${idx}`}
                                className="flex h-8 w-8 items-center justify-center"
                            >
                                <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                            </div>
                        ) : (
                            <Button
                                key={pageNum}
                                variant={pageNum === page ? "default" : "outline"}
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => onPageChange(pageNum)}
                            >
                                {pageNum}
                            </Button>
                        )
                    )}

                    <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onPageChange(page + 1)}
                        disabled={page >= totalPages}
                    >
                        <ChevronRight className="h-4 w-4" />
                        <span className="sr-only">Next page</span>
                    </Button>
                </div>
            )}
        </div>
    );
}
