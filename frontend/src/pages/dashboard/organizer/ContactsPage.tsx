import React, { useMemo, useState } from "react";
// TAGGING-DISABLED: Link + TagIcon imports removed while tag UI is hidden.
// import { Link } from "react-router-dom";
import {
    Search,
    Download,
    Upload,
    Mail,
    MoreHorizontal,
    Users,
    Plus,
    Loader2,
    Pencil,
    Trash2,
    // Tag as TagIcon, // TAGGING-DISABLED
} from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/shared/ui/table";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { PageHeader } from "@/shared/ui/page-header";
import { EmptyState } from "@/shared/ui/empty-state";
import { Badge } from "@/shared/ui/badge";
import { Card, CardContent } from "@/shared/ui/card";
import { toast } from "sonner";
import { exportContacts, type Contact } from "@/api/contacts";
import { useContacts } from "@/features/contacts";
import { useDebounce } from "@/shared/hooks";
import {
    ContactFormDialog,
    DeleteContactDialog,
    // TagFilter, // TAGGING-DISABLED
    ImportDialog,
} from "@/components/contacts";

export function ContactsPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const debouncedSearch = useDebounce(searchTerm, 250);

    // Build params reactively — empty string means "no filter".
    const queryParams = useMemo(() => {
        const params: Record<string, string> = {};
        if (debouncedSearch.trim()) params.search = debouncedSearch.trim();
        return params;
    }, [debouncedSearch]);

    const { data: contacts = [], isLoading: loading } = useContacts(queryParams);

    // Dialog states
    const [addDialogOpen, setAddDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [importDialogOpen, setImportDialogOpen] = useState(false);
    const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
    const [exporting, setExporting] = useState(false);

    const handleExport = async () => {
        setExporting(true);
        try {
            await exportContacts();
            toast.success('Contacts exported successfully');
        } catch (error) {
            console.error('Failed to export contacts:', error);
        } finally {
            setExporting(false);
        }
    };

    const handleEmail = (email: string) => {
        window.location.href = `mailto:${email}`;
    };

    const handleEdit = (contact: Contact) => {
        setSelectedContact(contact);
        setEditDialogOpen(true);
    };

    const handleDelete = (contact: Contact) => {
        setSelectedContact(contact);
        setDeleteDialogOpen(true);
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Contacts"
                description="Manage your contacts."
                actions={
                    <div className="flex gap-2">
                        {/* TAGGING-DISABLED: restore Manage tags link when re-enabling.
                        <Button asChild variant="outline" className="flex items-center gap-2">
                            <Link to="/organizer/contacts/tags">
                                <TagIcon className="h-4 w-4" /> Manage tags
                            </Link>
                        </Button>
                        */}
                        <Button onClick={() => setImportDialogOpen(true)} variant="outline" className="flex items-center gap-2">
                            <Upload className="h-4 w-4" /> Import
                        </Button>
                        <Button onClick={handleExport} variant="outline" className="flex items-center gap-2" disabled={exporting}>
                            {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} Export
                        </Button>
                        <Button onClick={() => setAddDialogOpen(true)} className="flex items-center gap-2">
                            <Plus className="h-4 w-4" /> Add Contact
                        </Button>
                    </div>
                }
            />

            <Card>
                <CardContent className="p-0">
                    {/* Toolbar */}
                    <div className="p-4 border-b flex flex-col sm:flex-row gap-4 items-center justify-between bg-muted/30">
                        <div className="relative flex-1 sm:w-64">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search contacts..."
                                className="pl-9 bg-background"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        {/* TAGGING-DISABLED: restore TagFilter when re-enabling.
                        <TagFilter
                            tags={tags}
                            selectedTagUuids={selectedTagUuids}
                            onTagsChange={handleTagsChange}
                            loading={loading}
                        />
                        */}
                    </div>

                    {/* Contact table */}
                    <div className="relative w-full overflow-auto min-h-[400px]">
                        {loading ? (
                            <div className="flex items-center justify-center h-64">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                            </div>
                        ) : contacts.length > 0 ? (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-[250px]">Name</TableHead>
                                        <TableHead>Organization</TableHead>
                                        {/* TAGGING-DISABLED: <TableHead>Tags</TableHead> */}
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Events</TableHead>
                                        <TableHead className="text-right">Courses</TableHead>
                                        <TableHead className="w-[50px]"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {contacts.map((contact) => (
                                        <TableRow key={contact.uuid}>
                                            <TableCell className="font-medium">
                                                <div className="flex flex-col">
                                                    <span className="text-foreground">{contact.full_name}</span>
                                                    <span className="text-xs text-muted-foreground">{contact.email}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    <span className="text-foreground text-sm">{contact.professional_title || '-'}</span>
                                                    <span className="text-xs text-muted-foreground">{contact.organization_name || '-'}</span>
                                                </div>
                                            </TableCell>
                                            {/* TAGGING-DISABLED: tag cell hidden. Restore when tag UI returns.
                                            <TableCell>
                                                <div className="flex flex-wrap gap-1">
                                                    {contact.tags.slice(0, 3).map(tag => (
                                                        <Badge
                                                            key={tag.uuid}
                                                            variant="outline"
                                                            className="text-xs"
                                                            style={{ borderColor: tag.color, color: tag.color }}
                                                        >
                                                            {tag.name}
                                                        </Badge>
                                                    ))}
                                                    {contact.tags.length > 3 && (
                                                        <Badge variant="outline" className="text-xs">
                                                            +{contact.tags.length - 3}
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                            */}
                                            <TableCell>
                                                {contact.email_bounced ? (
                                                    <Badge variant="destructive">Bounced</Badge>
                                                ) : contact.email_opted_out ? (
                                                    <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">Opted Out</Badge>
                                                ) : (
                                                    <Badge variant="outline" className="text-primary border-primary/20 bg-primary/5">Active</Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex flex-col text-sm">
                                                    <span className="font-medium">{contact.events_attended_count} attended</span>
                                                    <span className="text-xs text-muted-foreground">{contact.events_invited_count} invited</span>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex flex-col text-sm">
                                                    <span className="font-medium">{contact.courses_enrolled_count ?? 0} enrolled</span>
                                                    <span className="text-xs text-muted-foreground">{contact.courses_completed_count ?? 0} completed</span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild>
                                                        <Button variant="ghost" className="h-8 w-8 p-0">
                                                            <span className="sr-only">Open menu</span>
                                                            <MoreHorizontal className="h-4 w-4" />
                                                        </Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem onClick={() => handleEdit(contact)}>
                                                            <Pencil className="mr-2 h-4 w-4" /> Edit
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem onClick={() => handleEmail(contact.email)}>
                                                            <Mail className="mr-2 h-4 w-4" /> Email Contact
                                                        </DropdownMenuItem>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem
                                                            onClick={() => handleDelete(contact)}
                                                            className="text-destructive focus:text-destructive"
                                                        >
                                                            <Trash2 className="mr-2 h-4 w-4" /> Delete
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="py-12">
                                <EmptyState
                                    icon={Users}
                                    title="No contacts found"
                                    description={
                                        searchTerm
                                            ? "Try adjusting your search"
                                            : "You haven't added any contacts yet."
                                    }
                                    action={
                                        <Button onClick={() => setAddDialogOpen(true)}>
                                            <Plus className="mr-2 h-4 w-4" /> Add Contact
                                        </Button>
                                    }
                                />
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Dialogs */}
            <ContactFormDialog
                open={addDialogOpen}
                onOpenChange={setAddDialogOpen}
            />
            <ContactFormDialog
                open={editDialogOpen}
                onOpenChange={(open) => {
                    setEditDialogOpen(open);
                    if (!open) setSelectedContact(null);
                }}
                contact={selectedContact}
            />
            <DeleteContactDialog
                open={deleteDialogOpen}
                onOpenChange={(open) => {
                    setDeleteDialogOpen(open);
                    if (!open) setSelectedContact(null);
                }}
                contact={selectedContact}
            />
            <ImportDialog
                open={importDialogOpen}
                onOpenChange={setImportDialogOpen}
            />
        </div>
    );
}
