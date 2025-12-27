

import React, { useState, useEffect } from "react";
import {
    Search,
    Download,
    Mail,
    MoreHorizontal,
    Filter,
    Users,
    Plus,
    Loader2
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
import { getContactLists, getContacts, Contact, ContactList } from "@/api/contacts";

export function ContactsPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentList, setCurrentList] = useState<ContactList | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            // 1. Get Lists
            const lists = await getContactLists();
            if (lists.results.length > 0) {
                // Use default or first list
                const defaultList = lists.results.find(l => l.is_default) || lists.results[0];
                setCurrentList(defaultList);

                // 2. Get Contacts for this list
                await fetchContacts(defaultList.uuid);
            } else {
                setContacts([]);
                setLoading(false);
            }
        } catch (error) {
            console.error("Failed to fetch contacts data", error);
            toast.error("Failed to load contacts.");
            setLoading(false);
        }
    };

    const fetchContacts = async (listUuid: string, search?: string) => {
        setLoading(true);
        try {
            const params: any = {};
            if (search) params.search = search;

            const response = await getContacts(listUuid, params);
            setContacts(response.results);
        } catch (error) {
            console.error("Failed to fetch contacts", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (term: string) => {
        setSearchTerm(term);
        if (currentList) {
            // Debounce could be added here
            fetchContacts(currentList.uuid, term);
        }
    };

    const handleExport = () => {
        toast.success("Export functionality coming soon");
    };

    const handleEmail = (email: string) => {
        window.location.href = `mailto:${email}`;
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Contacts Manager"
                description={currentList ? `Managing list: ${currentList.name}` : "Manage your attendee database and view interaction history."}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={fetchData} title="Refresh">
                            Refresh
                        </Button>
                        <Button onClick={handleExport} variant="outline" className="flex items-center gap-2">
                            <Download className="h-4 w-4" /> Export CSV
                        </Button>
                    </div>
                }
            />

            <Card>
                <CardContent className="p-0">
                    <div className="p-4 border-b flex flex-col sm:flex-row gap-4 items-center justify-between bg-muted/30">
                        <div className="relative w-full sm:w-96">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search contacts..."
                                className="pl-9 bg-background"
                                value={searchTerm}
                                onChange={(e) => handleSearch(e.target.value)}
                            />
                        </div>
                        <div className="flex items-center gap-2 w-full sm:w-auto">
                            <Button variant="outline" size="sm" className="ml-auto">
                                <Filter className="h-4 w-4 mr-2" /> Filter
                            </Button>
                        </div>
                    </div>

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
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Events Attended</TableHead>
                                        <TableHead className="text-right">Last Atended</TableHead>
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
                                                {contact.email_bounced ? (
                                                    <Badge variant="destructive">Bounced</Badge>
                                                ) : contact.email_opted_out ? (
                                                    <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">Opted Out</Badge>
                                                ) : (
                                                    <Badge variant="outline" className="text-primary border-primary/20 bg-primary/5">Active</Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right font-medium">{contact.events_attended_count}</TableCell>
                                            <TableCell className="text-right text-muted-foreground text-sm">
                                                {contact.last_attended_at ? new Date(contact.last_attended_at).toLocaleDateString() : '-'}
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
                                                        <DropdownMenuItem onClick={() => handleEmail(contact.email)}>
                                                            <Mail className="mr-2 h-4 w-4" /> Email Contact
                                                        </DropdownMenuItem>
                                                        {/* Details view could be added later */}
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
                                    description={searchTerm ? `No results for "${searchTerm}"` : "You haven't added any contacts yet."}
                                    action={
                                        <Button variant="outline">
                                            <Plus className="mr-2 h-4 w-4" /> Import Contacts
                                        </Button>
                                    }
                                />
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}


