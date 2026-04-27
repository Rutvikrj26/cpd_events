import { useCallback, useEffect, useState } from "react";
import { z } from "zod";
import { toast } from "sonner";
import {
    Mic,
    Plus,
    MoreHorizontal,
    Pencil,
    Trash2,
    Mail,
    Link2 as Linkedin,
} from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/shared/ui/avatar";
import { PageHeader } from "@/shared/ui/page-header";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { DataTable, type DataTableColumn } from "@/shared/ui/data-table";
import { FormDialog } from "@/shared/ui/form-dialog";
import { ConfirmDialog } from "@/shared/ui/confirm-dialog";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/shared/ui/form";
import { useZodForm } from "@/shared/lib";
import { nonEmpty } from "@/shared/schemas/primitives";
import {
    getSpeakers,
    createSpeaker,
    updateSpeaker,
    deleteSpeaker,
} from "@/api/speakers";
import type { Speaker, CreateSpeakerRequest } from "@/api/speakers/types";

/**
 * Speaker form schema. Email + LinkedIn URL are optional but validated
 * when provided. The empty-string ↔ undefined coercion happens in the
 * submit handler so the request body matches the API expectation
 * (`field?: string`).
 */
const speakerSchema = z.object({
    name: nonEmpty("Name"),
    bio: z.string().trim().optional(),
    qualifications: z.string().trim().optional(),
    email: z.union([z.literal(""), z.string().email("Enter a valid email")]).optional(),
    linkedin_url: z
        .union([z.literal(""), z.string().url("Enter a valid URL")])
        .optional(),
});

type SpeakerFormValues = z.infer<typeof speakerSchema>;

const EMPTY_SPEAKER_VALUES: SpeakerFormValues = {
    name: "",
    bio: "",
    qualifications: "",
    email: "",
    linkedin_url: "",
};

export default function SpeakersPage() {
    const [speakers, setSpeakers] = useState<Speaker[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");

    // Dialog state
    const [formOpen, setFormOpen] = useState(false);
    const [editingSpeaker, setEditingSpeaker] = useState<Speaker | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<Speaker | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    const form = useZodForm(speakerSchema, {
        defaultValues: EMPTY_SPEAKER_VALUES,
    });

    const fetchSpeakers = useCallback(async () => {
        try {
            setLoading(true);
            const data = await getSpeakers();
            setSpeakers(data);
        } catch {
            toast.error("Failed to load speakers");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSpeakers();
    }, [fetchSpeakers]);

    function openCreate() {
        form.reset(EMPTY_SPEAKER_VALUES);
        setEditingSpeaker(null);
        setFormOpen(true);
    }

    function openEdit(speaker: Speaker) {
        setEditingSpeaker(speaker);
        form.reset({
            name: speaker.name,
            bio: speaker.bio || "",
            qualifications: speaker.qualifications || "",
            email: speaker.email || "",
            linkedin_url: speaker.linkedin_url || "",
        });
        setFormOpen(true);
    }

    const onSubmit = form.handleSubmit(async (values) => {
        try {
            const payload: CreateSpeakerRequest = {
                name: values.name,
                bio: values.bio || undefined,
                qualifications: values.qualifications || undefined,
                email: values.email || undefined,
                linkedin_url: values.linkedin_url || undefined,
            };

            if (editingSpeaker) {
                await updateSpeaker(editingSpeaker.uuid, payload);
                toast.success("Speaker updated");
            } else {
                await createSpeaker(payload);
                toast.success("Speaker created");
            }
            setFormOpen(false);
            form.reset(EMPTY_SPEAKER_VALUES);
            setEditingSpeaker(null);
            fetchSpeakers();
        } catch (err: any) {
            toast.error(err?.response?.data?.error?.message || "Failed to save speaker");
        }
    });

    async function handleDelete() {
        if (!deleteTarget) return;
        setDeleteLoading(true);
        try {
            await deleteSpeaker(deleteTarget.uuid);
            toast.success("Speaker deleted");
            setDeleteTarget(null);
            fetchSpeakers();
        } catch {
            toast.error("Failed to delete speaker");
        } finally {
            setDeleteLoading(false);
        }
    }

    const filtered = speakers.filter(
        (s) =>
            !searchTerm ||
            s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            s.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const columns: DataTableColumn<Speaker>[] = [
        {
            key: "name",
            header: "Speaker",
            cell: (row) => (
                <div className="flex items-center gap-3">
                    <Avatar className="h-9 w-9">
                        <AvatarImage src={row.photo || undefined} alt={row.name} />
                        <AvatarFallback>
                            {row.name
                                .split(" ")
                                .map((n) => n[0])
                                .join("")
                                .slice(0, 2)
                                .toUpperCase()}
                        </AvatarFallback>
                    </Avatar>
                    <div>
                        <p className="font-medium">{row.name}</p>
                        {row.email && (
                            <p className="text-xs text-muted-foreground">{row.email}</p>
                        )}
                    </div>
                </div>
            ),
        },
        {
            key: "qualifications",
            header: "Qualifications",
            cell: (row) => (
                <span className="text-sm text-muted-foreground line-clamp-1">
                    {row.qualifications || "-"}
                </span>
            ),
        },
        {
            key: "bio",
            header: "Bio",
            cell: (row) => (
                <span className="text-sm text-muted-foreground line-clamp-2">
                    {row.bio || "-"}
                </span>
            ),
        },
        {
            key: "links",
            header: "Links",
            cell: (row) => (
                <div className="flex gap-2 text-muted-foreground">
                    {row.email && (
                        <a
                            href={`mailto:${row.email}`}
                            title={row.email}
                            className="hover:text-foreground"
                        >
                            <Mail className="h-4 w-4" />
                        </a>
                    )}
                    {row.linkedin_url && (
                        <a
                            href={row.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="LinkedIn"
                            className="hover:text-foreground"
                        >
                            <Linkedin className="h-4 w-4" />
                        </a>
                    )}
                </div>
            ),
        },
        {
            key: "actions",
            header: "",
            cell: (row) => (
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                        >
                            <MoreHorizontal className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEdit(row)}>
                            <Pencil className="mr-2 h-4 w-4" />
                            Edit
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

    return (
        <div className="p-4 md:p-6 lg:p-8 space-y-6">
            <PageHeader
                title="Speakers"
                description="Manage your speaker pool. Speakers can be assigned to events and sessions."
            />

            <DataTable
                columns={columns}
                data={filtered}
                isLoading={loading}
                searchPlaceholder="Search speakers..."
                searchValue={searchTerm}
                onSearchChange={setSearchTerm}
                toolbarActions={
                    <Button onClick={openCreate}>
                        <Plus className="mr-2 h-4 w-4" />
                        Add Speaker
                    </Button>
                }
                emptyState={{
                    icon: Mic,
                    title: "No speakers",
                    description: "Add speakers to assign them to your events and sessions.",
                    action: (
                        <Button onClick={openCreate}>
                            <Plus className="mr-2 h-4 w-4" />
                            Add Speaker
                        </Button>
                    ),
                }}
                rowKey={(row) => row.uuid}
            />

            {/* Create / Edit dialog */}
            <FormDialog
                open={formOpen}
                onOpenChange={(open) => {
                    setFormOpen(open);
                    if (!open) {
                        form.reset(EMPTY_SPEAKER_VALUES);
                        setEditingSpeaker(null);
                    }
                }}
                title={editingSpeaker ? "Edit Speaker" : "Add Speaker"}
                description={
                    editingSpeaker
                        ? "Update speaker details."
                        : "Add a new speaker to your pool."
                }
                onSubmit={onSubmit}
                submitLabel={editingSpeaker ? "Save Changes" : "Add Speaker"}
                isLoading={form.formState.isSubmitting}
            >
                <Form {...form}>
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Name *</FormLabel>
                                <FormControl>
                                    <Input placeholder="Full name" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="email"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Email</FormLabel>
                                <FormControl>
                                    <Input
                                        type="email"
                                        placeholder="speaker@example.com"
                                        {...field}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="qualifications"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Qualifications</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g. MD, PhD, CPA" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="bio"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Bio</FormLabel>
                                <FormControl>
                                    <Textarea
                                        placeholder="Brief biography"
                                        rows={3}
                                        {...field}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="linkedin_url"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>LinkedIn URL</FormLabel>
                                <FormControl>
                                    <Input
                                        type="url"
                                        placeholder="https://linkedin.com/in/..."
                                        {...field}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </Form>
            </FormDialog>

            {/* Delete confirmation */}
            <ConfirmDialog
                open={!!deleteTarget}
                onOpenChange={(open) => !open && setDeleteTarget(null)}
                title="Delete Speaker"
                description={`Are you sure you want to delete "${deleteTarget?.name}"? This speaker will be removed from all events.`}
                confirmLabel="Delete"
                variant="destructive"
                isLoading={deleteLoading}
                onConfirm={handleDelete}
            />
        </div>
    );
}
