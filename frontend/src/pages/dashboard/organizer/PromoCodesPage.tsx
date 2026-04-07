import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
    Tag,
    Plus,
    MoreHorizontal,
    Pencil,
    Trash2,
    ToggleLeft,
    ToggleRight,
    Eye,
    Percent,
    DollarSign,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/ui/page-header";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog";
import { DataTable, type DataTableColumn, type DataTableFilter } from "@/components/ui/data-table";
import { FormDialog } from "@/components/ui/form-dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
    getPromoCodes,
    createPromoCode,
    updatePromoCode,
    deletePromoCode,
    togglePromoCodeActive,
    getPromoCodeUsages,
} from "@/api/promo-codes";
import type { PromoCode, PromoCodeUsage, CreatePromoCodeRequest } from "@/api/promo-codes/types";

export default function PromoCodesPage() {
    const [promoCodes, setPromoCodes] = useState<PromoCode[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [statusFilter, setStatusFilter] = useState("");

    // Dialog state
    const [formOpen, setFormOpen] = useState(false);
    const [editingCode, setEditingCode] = useState<PromoCode | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<PromoCode | null>(null);
    const [usageTarget, setUsageTarget] = useState<PromoCode | null>(null);
    const [usages, setUsages] = useState<PromoCodeUsage[]>([]);
    const [usagesLoading, setUsagesLoading] = useState(false);

    // Form state
    const [formLoading, setFormLoading] = useState(false);
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [code, setCode] = useState("");
    const [description, setDescription] = useState("");
    const [discountType, setDiscountType] = useState<"percentage" | "fixed_amount">("percentage");
    const [discountValue, setDiscountValue] = useState("");
    const [maxUses, setMaxUses] = useState("");
    const [validFrom, setValidFrom] = useState("");
    const [validUntil, setValidUntil] = useState("");
    const [firstTimeOnly, setFirstTimeOnly] = useState(false);

    const fetchPromoCodes = useCallback(async () => {
        try {
            setLoading(true);
            const data = await getPromoCodes();
            setPromoCodes(data);
        } catch {
            toast.error("Failed to load promo codes");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPromoCodes();
    }, [fetchPromoCodes]);

    function resetForm() {
        setCode("");
        setDescription("");
        setDiscountType("percentage");
        setDiscountValue("");
        setMaxUses("");
        setValidFrom("");
        setValidUntil("");
        setFirstTimeOnly(false);
        setEditingCode(null);
    }

    function openCreate() {
        resetForm();
        setFormOpen(true);
    }

    function openEdit(promo: PromoCode) {
        setEditingCode(promo);
        setCode(promo.code);
        setDescription(promo.description);
        setDiscountType(promo.discount_type);
        setDiscountValue(promo.discount_value);
        setMaxUses(promo.max_uses?.toString() ?? "");
        setValidFrom(promo.valid_from ? promo.valid_from.slice(0, 16) : "");
        setValidUntil(promo.valid_until ? promo.valid_until.slice(0, 16) : "");
        setFirstTimeOnly(promo.first_time_only);
        setFormOpen(true);
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setFormLoading(true);
        try {
            const payload: CreatePromoCodeRequest = {
                code,
                description,
                discount_type: discountType,
                discount_value: parseFloat(discountValue),
                max_uses: maxUses ? parseInt(maxUses) : undefined,
                valid_from: validFrom || undefined,
                valid_until: validUntil || undefined,
                first_time_only: firstTimeOnly,
            };

            if (editingCode) {
                await updatePromoCode(editingCode.uuid, payload);
                toast.success("Promo code updated");
            } else {
                await createPromoCode(payload);
                toast.success("Promo code created");
            }
            setFormOpen(false);
            resetForm();
            fetchPromoCodes();
        } catch (err: any) {
            toast.error(err?.response?.data?.error?.message || "Failed to save promo code");
        } finally {
            setFormLoading(false);
        }
    }

    async function handleDelete() {
        if (!deleteTarget) return;
        setDeleteLoading(true);
        try {
            await deletePromoCode(deleteTarget.uuid);
            toast.success("Promo code deleted");
            setDeleteTarget(null);
            fetchPromoCodes();
        } catch {
            toast.error("Failed to delete promo code");
        } finally {
            setDeleteLoading(false);
        }
    }

    async function handleToggleActive(promo: PromoCode) {
        try {
            const result = await togglePromoCodeActive(promo.uuid);
            toast.success(result.message);
            fetchPromoCodes();
        } catch {
            toast.error("Failed to toggle status");
        }
    }

    async function openUsages(promo: PromoCode) {
        setUsageTarget(promo);
        setUsagesLoading(true);
        try {
            const data = await getPromoCodeUsages(promo.uuid);
            setUsages(data);
        } catch {
            toast.error("Failed to load usage history");
        } finally {
            setUsagesLoading(false);
        }
    }

    // Filter data
    const filtered = promoCodes.filter((p) => {
        const matchesSearch =
            !searchTerm ||
            p.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
            p.description.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus =
            !statusFilter ||
            (statusFilter === "active" && p.is_active) ||
            (statusFilter === "inactive" && !p.is_active) ||
            (statusFilter === "expired" && p.is_expired);
        return matchesSearch && matchesStatus;
    });

    const columns: DataTableColumn<PromoCode>[] = [
        {
            key: "code",
            header: "Code",
            cell: (row) => (
                <div>
                    <span className="font-mono font-semibold">{row.code}</span>
                    {row.description && (
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                            {row.description}
                        </p>
                    )}
                </div>
            ),
        },
        {
            key: "discount",
            header: "Discount",
            cell: (row) => (
                <div className="flex items-center gap-1.5">
                    {row.discount_type === "percentage" ? (
                        <Percent className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                        <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                    <span>{row.discount_display}</span>
                </div>
            ),
        },
        {
            key: "usage",
            header: "Usage",
            cell: (row) => (
                <span>
                    {row.current_uses}
                    {row.max_uses ? ` / ${row.max_uses}` : ""}
                </span>
            ),
        },
        {
            key: "events",
            header: "Events",
            cell: (row) =>
                row.events_data.length === 0 ? (
                    <span className="text-muted-foreground">All events</span>
                ) : (
                    <div className="flex flex-wrap gap-1">
                        {row.events_data.slice(0, 2).map((e) => (
                            <Badge key={e.uuid} variant="secondary" className="text-xs">
                                {e.title}
                            </Badge>
                        ))}
                        {row.events_data.length > 2 && (
                            <Badge variant="outline" className="text-xs">
                                +{row.events_data.length - 2}
                            </Badge>
                        )}
                    </div>
                ),
        },
        {
            key: "status",
            header: "Status",
            cell: (row) => (
                <Badge variant={row.is_active ? "default" : "secondary"}>
                    {row.is_expired ? "Expired" : row.is_active ? "Active" : "Inactive"}
                </Badge>
            ),
        },
        {
            key: "validity",
            header: "Valid Period",
            cell: (row) => (
                <span className="text-sm text-muted-foreground">
                    {row.valid_from
                        ? new Date(row.valid_from).toLocaleDateString()
                        : "No start"}
                    {" - "}
                    {row.valid_until
                        ? new Date(row.valid_until).toLocaleDateString()
                        : "No end"}
                </span>
            ),
        },
        {
            key: "actions",
            header: "",
            headerClassName: "w-12",
            cell: (row) => (
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEdit(row)}>
                            <Pencil className="mr-2 h-4 w-4" />
                            Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleToggleActive(row)}>
                            {row.is_active ? (
                                <>
                                    <ToggleLeft className="mr-2 h-4 w-4" />
                                    Deactivate
                                </>
                            ) : (
                                <>
                                    <ToggleRight className="mr-2 h-4 w-4" />
                                    Activate
                                </>
                            )}
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => openUsages(row)}>
                            <Eye className="mr-2 h-4 w-4" />
                            View Usage
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => setDeleteTarget(row)}
                            className="text-destructive"
                        >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            ),
        },
    ];

    const filters: DataTableFilter[] = [
        {
            key: "status",
            label: "Status",
            value: statusFilter,
            onChange: setStatusFilter,
            options: [
                { label: "Active", value: "active" },
                { label: "Inactive", value: "inactive" },
                { label: "Expired", value: "expired" },
            ],
        },
    ];

    return (
        <div className="p-4 md:p-6 lg:p-8 space-y-6">
            <PageHeader
                title="Promo Codes"
                description="Create and manage discount codes for your events."
            />

            <DataTable
                columns={columns}
                data={filtered}
                isLoading={loading}
                searchPlaceholder="Search codes..."
                searchValue={searchTerm}
                onSearchChange={setSearchTerm}
                filters={filters}
                toolbarActions={
                    <Button onClick={openCreate}>
                        <Plus className="mr-2 h-4 w-4" />
                        Create Code
                    </Button>
                }
                emptyState={{
                    icon: Tag,
                    title: "No promo codes",
                    description: "Create your first promo code to offer discounts on events.",
                    action: (
                        <Button onClick={openCreate}>
                            <Plus className="mr-2 h-4 w-4" />
                            Create Code
                        </Button>
                    ),
                }}
                rowKey={(row) => row.uuid}
            />

            {/* Create/Edit Dialog */}
            <FormDialog
                open={formOpen}
                onOpenChange={(open) => {
                    setFormOpen(open);
                    if (!open) resetForm();
                }}
                title={editingCode ? "Edit Promo Code" : "Create Promo Code"}
                description={editingCode ? "Update discount code settings." : "Create a new discount code for your events."}
                onSubmit={handleSubmit}
                submitLabel={editingCode ? "Save Changes" : "Create Code"}
                isLoading={formLoading}
            >
                <div className="space-y-2">
                    <Label htmlFor="code">Code</Label>
                    <Input
                        id="code"
                        value={code}
                        onChange={(e) => setCode(e.target.value.toUpperCase())}
                        placeholder="e.g. SUMMER25"
                        required
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                        id="description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Optional description"
                        rows={2}
                    />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label>Discount Type</Label>
                        <Select value={discountType} onValueChange={(v) => setDiscountType(v as "percentage" | "fixed_amount")}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="percentage">Percentage (%)</SelectItem>
                                <SelectItem value="fixed_amount">Fixed Amount ($)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="discountValue">
                            {discountType === "percentage" ? "Percentage" : "Amount"}
                        </Label>
                        <Input
                            id="discountValue"
                            type="number"
                            value={discountValue}
                            onChange={(e) => setDiscountValue(e.target.value)}
                            placeholder={discountType === "percentage" ? "e.g. 25" : "e.g. 10.00"}
                            min="0"
                            max={discountType === "percentage" ? "100" : undefined}
                            step={discountType === "percentage" ? "1" : "0.01"}
                            required
                        />
                    </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="validFrom">Valid From</Label>
                        <Input
                            id="validFrom"
                            type="datetime-local"
                            value={validFrom}
                            onChange={(e) => setValidFrom(e.target.value)}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="validUntil">Valid Until</Label>
                        <Input
                            id="validUntil"
                            type="datetime-local"
                            value={validUntil}
                            onChange={(e) => setValidUntil(e.target.value)}
                        />
                    </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="maxUses">Max Uses</Label>
                        <Input
                            id="maxUses"
                            type="number"
                            value={maxUses}
                            onChange={(e) => setMaxUses(e.target.value)}
                            placeholder="Unlimited"
                            min="1"
                        />
                    </div>
                    <div className="flex items-center space-x-2 pt-6">
                        <Switch
                            id="firstTimeOnly"
                            checked={firstTimeOnly}
                            onCheckedChange={setFirstTimeOnly}
                        />
                        <Label htmlFor="firstTimeOnly">First-time users only</Label>
                    </div>
                </div>
            </FormDialog>

            {/* Delete Confirmation */}
            <ConfirmDialog
                open={!!deleteTarget}
                onOpenChange={(open) => !open && setDeleteTarget(null)}
                title="Delete Promo Code"
                description={`Are you sure you want to delete the code "${deleteTarget?.code}"? This action cannot be undone.`}
                confirmLabel="Delete"
                variant="destructive"
                isLoading={deleteLoading}
                onConfirm={handleDelete}
            />

            {/* Usage History Dialog */}
            <Dialog open={!!usageTarget} onOpenChange={(open) => !open && setUsageTarget(null)}>
                <DialogContent className="sm:max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>
                            Usage History: <span className="font-mono">{usageTarget?.code}</span>
                        </DialogTitle>
                        <DialogDescription>
                            {usageTarget?.current_uses ?? 0} total uses
                        </DialogDescription>
                    </DialogHeader>
                    {usagesLoading ? (
                        <div className="py-8 text-center text-muted-foreground">Loading...</div>
                    ) : usages.length === 0 ? (
                        <div className="py-8 text-center text-muted-foreground">
                            No usage records yet.
                        </div>
                    ) : (
                        <div className="max-h-80 overflow-auto">
                            <DataTable
                                columns={[
                                    { key: "email", header: "User", cell: (u) => u.user_email },
                                    { key: "event", header: "Event", cell: (u) => u.event_title },
                                    {
                                        key: "discount",
                                        header: "Discount",
                                        cell: (u) => `$${u.discount_amount}`,
                                    },
                                    {
                                        key: "date",
                                        header: "Date",
                                        cell: (u) => new Date(u.created_at).toLocaleDateString(),
                                    },
                                ]}
                                data={usages}
                                rowKey={(u) => u.uuid}
                            />
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
