/**
 * Organization Switcher Component
 *
 * Dropdown for switching between personal account and organizations.
 * Shows in the sidebar/header.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, ChevronDown, User, Plus, Check } from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useOrganization } from '@/contexts/OrganizationContext';
import { useAuth } from '@/contexts/AuthContext';

interface OrganizationSwitcherProps {
    variant?: 'default' | 'compact';
}

export const OrganizationSwitcher: React.FC<OrganizationSwitcherProps> = ({
    variant = 'default',
}) => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const { organizations, currentOrg, setCurrentOrg, clearCurrentOrg, isLoading } = useOrganization();

    const handleSelectPersonal = () => {
        clearCurrentOrg();
        navigate('/organizer');
    };

    const handleSelectOrg = async (org: typeof organizations[0]) => {
        // Navigate to org dashboard - will load org context there
        navigate(`/org/${org.slug}`);
    };

    const handleCreateOrg = () => {
        navigate('/organizations/new');
    };

    const displayName = currentOrg ? currentOrg.name : (user?.organization_name || 'Personal Account');
    const displayInitial = currentOrg ? currentOrg.name[0] : (user?.full_name?.[0] || 'P');

    if (variant === 'compact') {
        return (
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Avatar className="h-6 w-6">
                            {currentOrg?.logo_url ? (
                                <AvatarImage src={currentOrg.logo_url} alt={currentOrg.name} />
                            ) : null}
                            <AvatarFallback className="text-xs">
                                {displayInitial}
                            </AvatarFallback>
                        </Avatar>
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                    <SwitcherContent
                        user={user}
                        organizations={organizations}
                        currentOrg={currentOrg}
                        isLoading={isLoading}
                        onSelectPersonal={handleSelectPersonal}
                        onSelectOrg={handleSelectOrg}
                        onCreateOrg={handleCreateOrg}
                    />
                </DropdownMenuContent>
            </DropdownMenu>
        );
    }

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="outline"
                    className="w-full justify-between gap-2 px-3 py-2"
                    disabled={isLoading}
                >
                    <div className="flex items-center gap-2 truncate">
                        {currentOrg ? (
                            <Building2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        ) : (
                            <User className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        )}
                        <span className="truncate">{displayName}</span>
                    </div>
                    <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-64">
                <SwitcherContent
                    user={user}
                    organizations={organizations}
                    currentOrg={currentOrg}
                    isLoading={isLoading}
                    onSelectPersonal={handleSelectPersonal}
                    onSelectOrg={handleSelectOrg}
                    onCreateOrg={handleCreateOrg}
                />
            </DropdownMenuContent>
        </DropdownMenu>
    );
};

// Shared dropdown content
interface SwitcherContentProps {
    user: any;
    organizations: any[];
    currentOrg: any;
    isLoading: boolean;
    onSelectPersonal: () => void;
    onSelectOrg: (org: any) => void;
    onCreateOrg: () => void;
}

const SwitcherContent: React.FC<SwitcherContentProps> = ({
    user,
    organizations,
    currentOrg,
    isLoading,
    onSelectPersonal,
    onSelectOrg,
    onCreateOrg,
}) => {
    return (
        <>
            {/* Personal Account */}
            <DropdownMenuItem
                onClick={onSelectPersonal}
                className="flex items-center justify-between cursor-pointer"
            >
                <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <div>
                        <p className="text-sm font-medium">Personal Account</p>
                        <p className="text-xs text-muted-foreground">{user?.email}</p>
                    </div>
                </div>
                {!currentOrg && <Check className="h-4 w-4 text-primary" />}
            </DropdownMenuItem>

            {/* Organizations */}
            {organizations.length > 0 && (
                <>
                    <DropdownMenuSeparator />
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                        Organizations
                    </div>
                    {organizations.map((org) => (
                        <DropdownMenuItem
                            key={org.uuid}
                            onClick={() => onSelectOrg(org)}
                            className="flex items-center justify-between cursor-pointer"
                        >
                            <div className="flex items-center gap-2">
                                <Avatar className="h-6 w-6">
                                    {org.logo_url ? (
                                        <AvatarImage src={org.logo_url} alt={org.name} />
                                    ) : null}
                                    <AvatarFallback className="text-xs bg-primary/10 text-primary">
                                        {org.name[0]}
                                    </AvatarFallback>
                                </Avatar>
                                <div>
                                    <p className="text-sm font-medium">{org.name}</p>
                                    <p className="text-xs text-muted-foreground capitalize">{org.user_role}</p>
                                </div>
                            </div>
                            {currentOrg?.uuid === org.uuid && (
                                <Check className="h-4 w-4 text-primary" />
                            )}
                        </DropdownMenuItem>
                    ))}
                </>
            )}

            {/* Create Organization */}
            <DropdownMenuSeparator />
            <DropdownMenuItem
                onClick={onCreateOrg}
                className="cursor-pointer"
            >
                <Plus className="h-4 w-4 mr-2" />
                Create Organization
            </DropdownMenuItem>
        </>
    );
};

export default OrganizationSwitcher;
