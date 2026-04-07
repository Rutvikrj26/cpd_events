import * as React from "react";
import { Search, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination, type PaginationProps } from "@/components/ui/pagination";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableHeader,
    TableBody,
    TableHead,
    TableRow,
    TableCell,
} from "@/components/ui/table";

// --- Types ---

export interface DataTableColumn<T> {
    /** Unique key identifying this column */
    key: string;
    /** Header label */
    header: string;
    /** Render function for cell content */
    cell: (row: T, index: number) => React.ReactNode;
    /** Optional className for the header cell */
    headerClassName?: string;
    /** Optional className for body cells */
    className?: string;
    /** Whether column is sortable (future use) */
    sortable?: boolean;
}

export interface DataTableFilter {
    /** Unique key for the filter */
    key: string;
    /** Display label */
    label: string;
    /** Options to show */
    options: { label: string; value: string }[];
    /** Currently selected value ("" for all) */
    value: string;
    /** Callback when value changes */
    onChange: (value: string) => void;
}

export interface DataTableBulkAction {
    /** Display label */
    label: string;
    /** Icon component */
    icon?: React.ReactNode;
    /** Variant */
    variant?: "default" | "destructive" | "outline" | "secondary";
    /** Callback with selected row indices */
    onClick: (selectedRows: number[]) => void;
}

export interface DataTableProps<T> {
    /** Column definitions */
    columns: DataTableColumn<T>[];
    /** Data rows */
    data: T[];
    /** Whether data is loading */
    isLoading?: boolean;
    /** Number of skeleton rows to show when loading */
    skeletonRows?: number;

    // --- Search ---
    /** Placeholder for search input */
    searchPlaceholder?: string;
    /** Current search value */
    searchValue?: string;
    /** Callback when search changes */
    onSearchChange?: (value: string) => void;

    // --- Filters ---
    /** Array of filter configurations */
    filters?: DataTableFilter[];

    // --- Pagination ---
    /** Pagination config. If omitted, no pagination is shown. */
    pagination?: PaginationProps;

    // --- Selection ---
    /** Enable row selection checkboxes */
    selectable?: boolean;
    /** Selected row indices (controlled) */
    selectedRows?: number[];
    /** Callback when selection changes */
    onSelectedRowsChange?: (indices: number[]) => void;
    /** Bulk actions shown when rows are selected */
    bulkActions?: DataTableBulkAction[];

    // --- Empty state ---
    /** Custom empty state config */
    emptyState?: {
        icon?: React.ComponentType<{ className?: string }>;
        title: string;
        description: string;
        action?: React.ReactNode;
    };

    // --- Toolbar ---
    /** Additional content rendered in the toolbar (right side) */
    toolbarActions?: React.ReactNode;

    /** className for the outermost wrapper */
    className?: string;

    /** Unique key extractor for rows (defaults to index) */
    rowKey?: (row: T, index: number) => string | number;
}

// --- Component ---

export function DataTable<T>({
    columns,
    data,
    isLoading = false,
    skeletonRows = 5,
    searchPlaceholder = "Search...",
    searchValue,
    onSearchChange,
    filters,
    pagination,
    selectable = false,
    selectedRows = [],
    onSelectedRowsChange,
    bulkActions,
    emptyState,
    toolbarActions,
    className,
    rowKey,
}: DataTableProps<T>) {
    const hasToolbar = onSearchChange || (filters && filters.length > 0) || toolbarActions;
    const hasActiveFilters = filters?.some((f) => f.value !== "");
    const hasSelection = selectable && selectedRows.length > 0;

    const allSelected = data.length > 0 && selectedRows.length === data.length;
    const someSelected = selectedRows.length > 0 && !allSelected;

    function handleSelectAll(checked: boolean) {
        if (!onSelectedRowsChange) return;
        onSelectedRowsChange(checked ? data.map((_, i) => i) : []);
    }

    function handleSelectRow(index: number, checked: boolean) {
        if (!onSelectedRowsChange) return;
        if (checked) {
            onSelectedRowsChange([...selectedRows, index]);
        } else {
            onSelectedRowsChange(selectedRows.filter((i) => i !== index));
        }
    }

    function clearFilters() {
        filters?.forEach((f) => f.onChange(""));
    }

    return (
        <div className={cn("space-y-4", className)}>
            {/* Toolbar: Search + Filters + Actions */}
            {hasToolbar && (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-1 items-center gap-3">
                        {onSearchChange && (
                            <div className="relative w-full max-w-sm">
                                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    placeholder={searchPlaceholder}
                                    value={searchValue ?? ""}
                                    onChange={(e) => onSearchChange(e.target.value)}
                                    className="pl-9 pr-9"
                                />
                                {searchValue && (
                                    <button
                                        onClick={() => onSearchChange("")}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                    >
                                        <X className="h-4 w-4" />
                                    </button>
                                )}
                            </div>
                        )}
                        {filters?.map((filter) => (
                            <Select
                                key={filter.key}
                                value={filter.value || "__all__"}
                                onValueChange={(v) => filter.onChange(v === "__all__" ? "" : v)}
                            >
                                <SelectTrigger className="h-10 w-[160px]">
                                    <SelectValue placeholder={filter.label} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">All {filter.label}</SelectItem>
                                    {filter.options.map((opt) => (
                                        <SelectItem key={opt.value} value={opt.value}>
                                            {opt.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        ))}
                        {hasActiveFilters && (
                            <Button variant="ghost" size="sm" onClick={clearFilters}>
                                <X className="mr-1 h-4 w-4" />
                                Clear filters
                            </Button>
                        )}
                    </div>
                    {toolbarActions && (
                        <div className="flex items-center gap-2">
                            {toolbarActions}
                        </div>
                    )}
                </div>
            )}

            {/* Bulk actions bar */}
            {hasSelection && bulkActions && (
                <div className="flex items-center gap-3 rounded-md border bg-muted/50 px-4 py-2">
                    <span className="text-sm font-medium">
                        {selectedRows.length} selected
                    </span>
                    <div className="flex items-center gap-2">
                        {bulkActions.map((action) => (
                            <Button
                                key={action.label}
                                variant={action.variant ?? "outline"}
                                size="sm"
                                onClick={() => action.onClick(selectedRows)}
                            >
                                {action.icon}
                                {action.label}
                            </Button>
                        ))}
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="ml-auto"
                        onClick={() => onSelectedRowsChange?.([])}
                    >
                        Clear selection
                    </Button>
                </div>
            )}

            {/* Table */}
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            {selectable && (
                                <TableHead className="w-12">
                                    <Checkbox
                                        checked={allSelected}
                                        ref={(el) => {
                                            if (el) {
                                                (el as unknown as HTMLInputElement).indeterminate = someSelected;
                                            }
                                        }}
                                        onCheckedChange={(checked) => handleSelectAll(!!checked)}
                                        aria-label="Select all"
                                    />
                                </TableHead>
                            )}
                            {columns.map((col) => (
                                <TableHead
                                    key={col.key}
                                    className={col.headerClassName}
                                >
                                    {col.header}
                                </TableHead>
                            ))}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            Array.from({ length: skeletonRows }).map((_, i) => (
                                <TableRow key={`skeleton-${i}`}>
                                    {selectable && (
                                        <TableCell>
                                            <Skeleton className="h-4 w-4" />
                                        </TableCell>
                                    )}
                                    {columns.map((col) => (
                                        <TableCell key={col.key} className={col.className}>
                                            <Skeleton className="h-4 w-full" />
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : data.length === 0 ? (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length + (selectable ? 1 : 0)}
                                    className="h-48"
                                >
                                    {emptyState ? (
                                        <EmptyState
                                            icon={emptyState.icon as any}
                                            title={emptyState.title}
                                            description={emptyState.description}
                                            action={emptyState.action}
                                            className="border-0 bg-transparent"
                                        />
                                    ) : (
                                        <div className="text-center text-muted-foreground">
                                            No results found.
                                        </div>
                                    )}
                                </TableCell>
                            </TableRow>
                        ) : (
                            data.map((row, index) => {
                                const key = rowKey ? rowKey(row, index) : index;
                                const isSelected = selectedRows.includes(index);
                                return (
                                    <TableRow
                                        key={key}
                                        data-state={isSelected ? "selected" : undefined}
                                    >
                                        {selectable && (
                                            <TableCell>
                                                <Checkbox
                                                    checked={isSelected}
                                                    onCheckedChange={(checked) =>
                                                        handleSelectRow(index, !!checked)
                                                    }
                                                    aria-label={`Select row ${index + 1}`}
                                                />
                                            </TableCell>
                                        )}
                                        {columns.map((col) => (
                                            <TableCell key={col.key} className={col.className}>
                                                {col.cell(row, index)}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                );
                            })
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            {pagination && !isLoading && data.length > 0 && (
                <Pagination {...pagination} />
            )}
        </div>
    );
}
