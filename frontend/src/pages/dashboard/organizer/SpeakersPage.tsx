import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
    Mic,
    Plus,
    MoreHorizontal,
    Pencil,
    Trash2,
    Mail,
    Linkedin,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { PageHeader } from "@/components/ui/page-header";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DataTable, type DataTableColumn } from "@/components/ui/data-table";
import { FormDialog } from "@/components/ui/form-dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
    getSpeakers,
    createSpeaker,
    updateSpeaker,
    deleteSpeaker,
} from "@/api/speakers";
import type { Speaker, CreateSpeakerRequest } from "@/api/speakers/types";

export default function SpeakersPage() {
    const [speakers, setSpeakers] = useState<Speaker[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");

    // Dialog state
    const [formOpen, setFormOpen] = useState(false);
    const [editingSpeaker, setEditingSpeaker] = useState<Speaker | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<Speaker | null>(null);
    const [formLoading, setFormLoading] = useState(false);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Form fields
    const [name, setName] = useState("");
    const [bio, setBio] = useState("");
    const [qualifications, setQualifications] = useState("");
    const [email, setEmail] = useState("");
    const [linkedinUrl, setLinkedinUrl] = useState("");

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

    function resetForm() {
        setName("");
        setBio("");
        setQualifications("");
        setEmail("");
        setLinkedinUrl("");
        setEditingSpeaker(null);
    }

    function openCreate() {
        resetForm();
        setFormOpen(true);
    }

    function openEdit(speaker: Speaker) {
        setEditingSpeaker(speaker);
        setName(speaker.name);
        setBio(speaker.bio || "");
        setQualifications(speaker.qualifications || "");
        setEmail(speaker.email || "");
        setLinkedinUrl(speaker.linkedin_url || "");
        setFormOpen(true);
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setFormLoading(true);
        try {
            const payload: CreateSpeakerRequest = {
                name,
                bio: bio || undefined,
                qualifications: qualifications || undefined,
                email: email || undefined,
                linkedin_url: linkedinUrl || undefined,
            };

            if (editingSpeaker) {
                await updateSpeaker(editingSpeaker.uuid, payload);
                toast.success("Speaker updated");
            } else {
                await createSpeaker(payload);
                toast.success("Speaker created");
            }
            setFormOpen(false);
            resetForm();
            fetchSpeakers();
        } catch (err: any) {
            toast.error(err?.response?.data?.error?.message || "Failed to save speaker");
        } finally {
            setFormLoading(false);
        }
    }

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
                <span className="text-sm text-muted-foreground line-clamp-1 max-w-xs">
                    {row.bio || "-"}
                </span>
            ),
        },
        {
            key: "links",
            header: "Links",
            cell: (row) => (
                <div className="flex items-center gap-2">
                    {row.email && (
                        <a href={`mailto:${row.email}`} className="text-muted-foreground hover:text-foreground">
                            <Mail className="h-4 w-4" />
                        </a>
                    )}
                    {row.linkedin_url && (
                        <a href={row.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground">
                            <Linkedin className="h-4 w-4" />
                        </a>
                    )}
                </div>
            ),
        },
        {
            key: "status",
            header: "Status",
            cell: (row) => (
                <Badge variant={row.is_active ? "default" : "secondary"}>
                    {row.is_active ? "Active" : "Inactive"}
                </Badge>
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

            {/* Create/Edit Dialog */}
            <FormDialog
                open={formOpen}
                onOpenChange={(open) => {
                    setFormOpen(open);
                    if (!open) resetForm();
                }}
                title={editingSpeaker ? "Edit Speaker" : "Add Speaker"}
                description={editingSpeaker ? "Update speaker details." : "Add a new speaker to your pool."}
                onSubmit={handleSubmit}
                submitLabel={editingSpeaker ? "Save Changes" : "Add Speaker"}
                isLoading={formLoading}
            >
                <div className="space-y-2">
                    <Label htmlFor="speakerName">Name *</Label>
                    <Input
                        id="speakerName"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Full name"
                        required
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="speakerEmail">Email</Label>
                    <Input
                        id="speakerEmail"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="speaker@example.com"
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="speakerQualifications">Qualifications</Label>
                    <Input
                        id="speakerQualifications"
                        value={qualifications}
                        onChange={(e) => setQualifications(e.target.value)}
                        placeholder="e.g. MD, PhD, CPA"
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="speakerBio">Bio</Label>
                    <Textarea
                        id="speakerBio"
                        value={bio}
                        onChange={(e) => setBio(e.target.value)}
                        placeholder="Brief biography"
                        rows={3}
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="speakerLinkedin">LinkedIn URL</Label>
                    <Input
                        id="speakerLinkedin"
                        type="url"
                        value={linkedinUrl}
                        onChange={(e) => setLinkedinUrl(e.target.value)}
                        placeholder="https://linkedin.com/in/..."
                    />
                </div>
            </FormDialog>

            {/* Delete Confirmation */}
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
