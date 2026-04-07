import React, { useState, useEffect } from "react";
import { Loader2, Monitor, Smartphone, Tablet, Globe, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
   Card,
   CardContent,
   CardDescription,
   CardHeader,
   CardTitle,
} from "@/components/ui/card";
import { DataTable, DataTableColumn } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { getUserSessions, revokeSession, logoutAllSessions } from "@/api/accounts";
import { UserSession } from "@/api/accounts/types";
import { toast } from "sonner";

function DeviceIcon({ deviceType }: { deviceType: string }) {
   switch (deviceType.toLowerCase()) {
      case "mobile":
         return <Smartphone className="h-4 w-4" />;
      case "tablet":
         return <Tablet className="h-4 w-4" />;
      case "desktop":
         return <Monitor className="h-4 w-4" />;
      default:
         return <Globe className="h-4 w-4" />;
   }
}

export function ActiveSessionsTab() {
   const [sessions, setSessions] = useState<UserSession[]>([]);
   const [loading, setLoading] = useState(true);
   const [revokingId, setRevokingId] = useState<string | null>(null);
   const [showRevokeDialog, setShowRevokeDialog] = useState(false);
   const [sessionToRevoke, setSessionToRevoke] = useState<string | null>(null);
   const [showLogoutAllDialog, setShowLogoutAllDialog] = useState(false);
   const [loggingOutAll, setLoggingOutAll] = useState(false);

   const loadSessions = async () => {
      setLoading(true);
      try {
         const data = await getUserSessions();
         setSessions(data);
      } catch (error) {
         console.error("Failed to load sessions:", error);
         toast.error("Failed to load sessions");
      } finally {
         setLoading(false);
      }
   };

   useEffect(() => {
      loadSessions();
   }, []);

   const handleRevoke = async () => {
      if (!sessionToRevoke) return;
      setRevokingId(sessionToRevoke);
      try {
         await revokeSession(sessionToRevoke);
         setSessions((prev) => prev.filter((s) => s.uuid !== sessionToRevoke));
         toast.success("Session revoked");
      } catch (error: any) {
         toast.error(error.message || "Failed to revoke session");
      } finally {
         setRevokingId(null);
         setSessionToRevoke(null);
         setShowRevokeDialog(false);
      }
   };

   const handleLogoutAll = async () => {
      setLoggingOutAll(true);
      try {
         await logoutAllSessions();
         toast.success("All other sessions have been logged out");
         await loadSessions();
      } catch (error: any) {
         toast.error(error.message || "Failed to log out all sessions");
      } finally {
         setLoggingOutAll(false);
         setShowLogoutAllDialog(false);
      }
   };

   const columns: DataTableColumn<UserSession>[] = [
      {
         key: "device",
         header: "Device",
         cell: (row) => (
            <div className="flex items-center gap-2">
               <DeviceIcon deviceType={row.device_type} />
               <span className="capitalize">{row.device_type}</span>
            </div>
         ),
      },
      {
         key: "ip_address",
         header: "IP Address",
         cell: (row) => <span className="font-mono text-sm">{row.ip_address}</span>,
      },
      {
         key: "user_agent",
         header: "Browser / Client",
         cell: (row) => (
            <span className="text-sm text-muted-foreground max-w-[200px] truncate block" title={row.user_agent}>
               {row.user_agent}
            </span>
         ),
      },
      {
         key: "last_activity",
         header: "Last Activity",
         cell: (row) => (
            <span className="text-sm">
               {new Date(row.last_activity_at).toLocaleString()}
            </span>
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
         cell: (row) => (
            <Button
               variant="ghost"
               size="sm"
               className="text-destructive hover:text-destructive hover:bg-destructive/10"
               disabled={revokingId === row.uuid}
               onClick={() => {
                  setSessionToRevoke(row.uuid);
                  setShowRevokeDialog(true);
               }}
            >
               {revokingId === row.uuid ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
               ) : (
                  "Revoke"
               )}
            </Button>
         ),
         headerClassName: "w-[80px]",
      },
   ];

   return (
      <Card>
         <CardHeader>
            <div className="flex items-center justify-between">
               <div>
                  <CardTitle>Active Sessions</CardTitle>
                  <CardDescription>
                     Manage your active sessions across devices. Revoke any session you don't recognize.
                  </CardDescription>
               </div>
               <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowLogoutAllDialog(true)}
                  disabled={sessions.length === 0}
               >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log Out All Devices
               </Button>
            </div>
         </CardHeader>
         <CardContent>
            <DataTable
               columns={columns}
               data={sessions}
               isLoading={loading}
               skeletonRows={3}
               rowKey={(row) => row.uuid}
               emptyState={{
                  icon: Monitor,
                  title: "No active sessions",
                  description: "No active sessions found for your account.",
               }}
            />
         </CardContent>

         {/* Revoke single session dialog */}
         <ConfirmDialog
            open={showRevokeDialog}
            onOpenChange={setShowRevokeDialog}
            title="Revoke Session"
            description="Are you sure you want to revoke this session? The device will be signed out immediately."
            confirmLabel="Revoke"
            variant="destructive"
            isLoading={revokingId !== null}
            onConfirm={handleRevoke}
         />

         {/* Log out all devices dialog */}
         <ConfirmDialog
            open={showLogoutAllDialog}
            onOpenChange={setShowLogoutAllDialog}
            title="Log Out All Devices"
            description="This will sign out all other sessions except your current one. You will need to sign in again on those devices."
            confirmLabel="Log Out All"
            variant="destructive"
            isLoading={loggingOutAll}
            onConfirm={handleLogoutAll}
         />
      </Card>
   );
}
