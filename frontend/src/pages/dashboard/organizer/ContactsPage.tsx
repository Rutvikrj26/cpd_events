import React, { useState } from "react";
import {
    Search,
    Download,
    Mail,
    MoreHorizontal,
    ArrowUpDown,
    Filter
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

// Mock Data
interface Contact {
    id: string;
    name: string;
    email: string;
    company: string;
    role: string;
    eventsAttended: number;
    lastActive: string;
    status: "active" | "inactive";
}

const MOCK_CONTACTS: Contact[] = [
    { id: "1", name: "Alice Johnson", email: "alice@example.com", company: "TechCorp", role: "Developer", eventsAttended: 5, lastActive: "2024-03-10", status: "active" },
    { id: "2", name: "Bob Smith", email: "bob@example.com", company: "Innovate Inc", role: "Manager", eventsAttended: 3, lastActive: "2024-02-28", status: "inactive" },
    { id: "3", name: "Charlie Brown", email: "charlie@example.com", company: "EduLearn", role: "Designer", eventsAttended: 8, lastActive: "2024-03-15", status: "active" },
    { id: "4", name: "Diana Prince", email: "diana@example.com", company: "Amazonia", role: "Director", eventsAttended: 12, lastActive: "2024-03-20", status: "active" },
    { id: "5", name: "Evan Wright", email: "evan@example.com", company: "Wright Designs", role: "Freelancer", eventsAttended: 1, lastActive: "2024-01-15", status: "inactive" },
];

export function ContactsPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [contacts, setContacts] = useState(MOCK_CONTACTS);

    const handleSearch = (term: string) => {
        setSearchTerm(term);
        const filtered = MOCK_CONTACTS.filter(contact =>
            contact.name.toLowerCase().includes(term.toLowerCase()) ||
            contact.email.toLowerCase().includes(term.toLowerCase()) ||
            contact.company.toLowerCase().includes(term.toLowerCase())
        );
        setContacts(filtered);
    };

    const handleExport = () => {
        toast.success("Exporting contacts to CSV...");
        // Simulate export
    };

    const handleEmail = (email: string) => {
        window.location.href = `mailto:${email}`;
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Contacts Manager"
                description="Manage your attendee database and view interaction history."
                actions={
                    <Button onClick={handleExport} variant="outline" className="flex items-center gap-2">
                        <Download className="h-4 w-4" /> Export CSV
                    </Button>
                }
            />

            <Card>
                <CardContent className="p-0">
                    <div className="p-4 border-b flex flex-col sm:flex-row gap-4 items-center justify-between bg-zinc-50/50">
                        <div className="relative w-full sm:w-96">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search contacts..."
                                className="pl-9 bg-card"
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

                    <div className="relative w-full overflow-auto">
                        {contacts.length > 0 ? (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-[250px]">Name</TableHead>
                                        <TableHead>Role / Company</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Events Attended</TableHead>
                                        <TableHead className="text-right">Last Active</TableHead>
                                        <TableHead className="w-[50px]"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {contacts.map((contact) => (
                                        <TableRow key={contact.id}>
                                            <TableCell className="font-medium">
                                                <div className="flex flex-col">
                                                    <span className="text-foreground">{contact.name}</span>
                                                    <span className="text-xs text-muted-foreground">{contact.email}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    <span className="text-foreground text-sm">{contact.role}</span>
                                                    <span className="text-xs text-muted-foreground">{contact.company}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant={contact.status === 'active' ? 'default' : 'secondary'} className="capitalize">
                                                    {contact.status}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-right font-medium">{contact.eventsAttended}</TableCell>
                                            <TableCell className="text-right text-muted-foreground text-sm">{contact.lastActive}</TableCell>
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
                                                        <DropdownMenuItem>View Profile</DropdownMenuItem>
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
                                    icon={UsersIcon}
                                    title="No contacts found"
                                    description={searchTerm ? `No results for "${searchTerm}"` : "You haven't had any attendees yet."}
                                />
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

function UsersIcon({ className }: { className?: string }) {
    return (
        <svg
            className={className}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
    )
}
