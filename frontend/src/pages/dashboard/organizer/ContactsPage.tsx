import React, { useState, useEffect } from "react";
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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "sonner";
import {
    getContacts,
    getTags,
    exportContacts,
    Contact,
    Tag
} from "@/api/contacts";
import {
    ContactFormDialog,
    DeleteContactDialog,
    TagFilter,
    ImportDialog
} from "@/components/contacts";

export function ContactsPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [tags, setTags] = useState<Tag[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedTagUuids, setSelectedTagUuids] = useState<string[]>([]);

    // Dialog states
    const [addDialogOpen, setAddDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [importDialogOpen, setImportDialogOpen] = useState(false);
    const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    useEffect(() => {
        fetchContacts(searchTerm, selectedTagUuids);
    }, [selectedTagUuids]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [contactsRes, tagsRes] = await Promise.all([
                getContacts(),
                getTags()
            ]);
            setContacts(contactsRes.results);
            setTags(tagsRes.results);
        } catch (error) {
            console.error("Failed to fetch contacts data", error);
            toast.error("Failed to load contacts.");
        } finally {
            setLoading(false);
        }
    };

    const fetchContacts = async (search?: string, tagUuids?: string[]) => {
        setLoading(true);
        try {
            const params: Record<string, string> = {};
            if (search) params.search = search;
            if (tagUuids && tagUuids.length > 0) {
                params.tags = tagUuids.join(',');
            }
            const response = await getContacts(params);
            setContacts(response.results);
        } catch (error) {
            console.error("Failed to fetch contacts", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (term: string) => {
        setSearchTerm(term);
        fetchContacts(term, selectedTagUuids);
    };

    const handleTagsChange = (uuids: string[]) => {
        setSelectedTagUuids(uuids);
    };

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

    const handleContactSaved = () => {
        fetchContacts(searchTerm, selectedTagUuids);
    };

    const handleContactDeleted = () => {
        fetchContacts(searchTerm, selectedTagUuids);
    };

    const handleImportComplete = () => {
        fetchContacts(searchTerm, selectedTagUuids);
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Contacts"
                description="Manage your contacts. Use tags to organize and segment."
                actions={
                    <div className="flex gap-2">
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
                                onChange={(e) => handleSearch(e.target.value)}
                            />
                        </div>
                        <TagFilter
                            tags={tags}
                            selectedTagUuids={selectedTagUuids}
                            onTagsChange={handleTagsChange}
                            loading={loading}
                        />
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
                                        <TableHead>Tags</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Events</TableHead>
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
                                        searchTerm || selectedTagUuids.length > 0
                                            ? "Try adjusting your search or filters"
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
                onSuccess={handleContactSaved}
            />
            <ContactFormDialog
                open={editDialogOpen}
                onOpenChange={(open) => {
                    setEditDialogOpen(open);
                    if (!open) setSelectedContact(null);
                }}
                contact={selectedContact}
                onSuccess={handleContactSaved}
            />
            <DeleteContactDialog
                open={deleteDialogOpen}
                onOpenChange={(open) => {
                    setDeleteDialogOpen(open);
                    if (!open) setSelectedContact(null);
                }}
                contact={selectedContact}
                onSuccess={handleContactDeleted}
            />
            <ImportDialog
                open={importDialogOpen}
                onOpenChange={setImportDialogOpen}
                onSuccess={handleImportComplete}
            />
        </div>
    );
}
