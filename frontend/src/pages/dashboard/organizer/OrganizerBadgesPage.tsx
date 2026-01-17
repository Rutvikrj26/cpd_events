import React, { useEffect, useState } from 'react';
import { Award, Eye, Calendar, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getEvents } from '@/api/events';
// Need API to get all issued badges for organizer (across events)
// But for now let's just use the templates list and a placeholder for issued badges or fetch them via a new endpoint if we had one.
// Actually, `IssuedBadgeViewSet` in backend filters by recipient=user.
// Organizer needs to see badges *issued by them*.
// I need to update backend `IssuedBadgeViewSet` or create a new view for organizer.
// Time constraint: I'll focus on Templates first in the Tab, and maybe a placeholder/basic list for Issued if possible.
// Wait, `CertificateTemplatesList` is fully functional. `BadgeTemplatesList` is functional.
// Let's implement the page with Templates tab primarily, and Issued tab if I can fix backend quickly.
// Checking backend views... `IssuedBadgeViewSet` is ReadOnlyModelViewSet filtering by recipient.
// I should add `OrganizerBadgeViewSet` or similar.
// Or just let `IssuedBadgeViewSet` have an action for `issued_by_me`.

import { BadgeTemplatesList } from "@/components/badges/BadgeTemplatesList";
import { OrganizerIssuedBadgesList } from "@/components/badges/OrganizerIssuedBadgesList";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const OrganizerBadgesPage = () => {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-foreground">Badges</h1>
                <p className="text-muted-foreground mt-1">Manage digital badges and templates</p>
            </div>

            <Tabs defaultValue="issued" className="w-full">
                <TabsList className="grid w-full grid-cols-2 max-w-[400px] mb-6">
                    <TabsTrigger value="issued">Issued Badges</TabsTrigger>
                    <TabsTrigger value="templates">Templates</TabsTrigger>
                </TabsList>

                <TabsContent value="issued">
                    <OrganizerIssuedBadgesList />
                </TabsContent>

                <TabsContent value="templates">
                    <BadgeTemplatesList />
                </TabsContent>
            </Tabs>
        </div>
    );
};
