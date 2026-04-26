import React, { useCallback, useEffect, useState } from "react";
import { getInitials } from "@/lib/initials";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    ArrowLeft,
    Loader2,
    Award,
    Calendar,
    GraduationCap,
    Shield,
    Activity,
    Mail,
    Building2,
    UserX,
    UserCheck,
} from "lucide-react";
import { formatRoleLabel } from "@/lib/role-utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
    AdminUserDetail,
    deactivateAdminUser,
    getAdminUserDetail,
    resendInvitation,
    updateAdminUser,
} from "@/api/accounts";

const ALL_ROLES = ["learner", "organizer", "instructor", "admin"];

export function AdminUserDetailPage() {
    const { uuid } = useParams<{ uuid: string }>();
    const navigate = useNavigate();
    const [detail, setDetail] = useState<AdminUserDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [changeRoleOpen, setChangeRoleOpen] = useState(false);
    const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);
    const [roleError, setRoleError] = useState<string | null>(null);

    const fetchDetail = useCallback(async () => {
        if (!uuid) return;
        setLoading(true);
        try {
            const data = await getAdminUserDetail(uuid);
            setDetail(data);
            setSelectedRoles(data.groups);
        } catch (err) {
            console.error(err);
            toast.error("Failed to load user detail");
        } finally {
            setLoading(false);
        }
    }, [uuid]);

    useEffect(() => {
        fetchDetail();
    }, [fetchDetail]);

    const handleToggleActive = async () => {
        if (!detail) return;
        try {
            await deactivateAdminUser(detail.profile.uuid);
            toast.success("User status updated");
            fetchDetail();
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            if (code === "LAST_ADMIN") {
                toast.error("Cannot deactivate the last active admin.");
            } else if (code === "SELF_DEACTIVATE") {
                toast.error("You can't deactivate your own account.");
            } else {
                toast.error("Failed to change user status");
            }
        }
    };

    const handleSaveRoles = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!detail) return;
        setRoleError(null);
        setSaving(true);
        try {
            await updateAdminUser(detail.profile.uuid, { roles: selectedRoles });
            toast.success("Roles updated");
            setChangeRoleOpen(false);
            fetchDetail();
        } catch (err: any) {
            const detailMsg =
                err?.response?.data?.error?.message ||
                err?.response?.data?.error?.details?.roles?.[0] ||
                "Failed to update roles";
            setRoleError(detailMsg);
        } finally {
            setSaving(false);
        }
    };

    const handleResendInvite = async () => {
        if (!detail?.pending_invitation) return;
        try {
            await resendInvitation(detail.pending_invitation.uuid);
            toast.success("Invitation re-sent");
            fetchDetail();
        } catch {
            toast.error("Failed to resend invitation");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-16">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!detail) {
        return (
            <div className="p-8 text-center text-muted-foreground">User not found.</div>
        );
    }

    const { profile, groups, course_staff, owned_events, owned_courses, certificates, recent_activity, pending_invitation } = detail;

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={() => navigate("/admin/users")}>
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to users
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Sidebar */}
                <div className="lg:col-span-1 space-y-6">
                    <Card>
                        <CardContent className="p-6 space-y-4 text-center">
                            <div className="mx-auto h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center text-2xl font-bold text-primary">
                                {getInitials(profile.full_name)}
                            </div>
                            <div>
                                <div className="text-lg font-semibold">{profile.full_name}</div>
                                <div className="text-sm text-muted-foreground">{profile.email}</div>
                            </div>
                            <div className="flex flex-col gap-2">
                                <Badge variant={profile.is_active ? "default" : "destructive"}>
                                    {profile.is_active ? "Active" : "Inactive"}
                                </Badge>
                                <Badge variant="secondary" className="capitalize">
                                    {profile.primary_role.replace("_", " ")}
                                </Badge>
                            </div>
                        </CardContent>
                    </Card>

                    {pending_invitation && (
                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-base flex items-center gap-2">
                                    <Mail className="h-4 w-4" />
                                    Pending invitation
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3 text-sm">
                                <div>Status: <Badge variant="outline">{pending_invitation.status}</Badge></div>
                                <div className="text-muted-foreground">
                                    Expires {new Date(pending_invitation.expires_at).toLocaleDateString()}
                                </div>
                                <Button variant="outline" size="sm" className="w-full" onClick={handleResendInvite}>
                                    Resend invitation
                                </Button>
                            </CardContent>
                        </Card>
                    )}
                </div>

                {/* Main column */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Profile */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Profile</CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                            <Field label="Full name" value={profile.full_name} />
                            <Field label="Email" value={profile.email} />
                            <Field label="Professional title" value={profile.professional_title || "—"} />
                            <Field label="Organization" value={profile.organization_name || "—"} />
                            <Field label="Created" value={new Date(profile.created_at).toLocaleDateString()} />
                            <Field label="Last login" value={profile.last_login_at ? new Date(profile.last_login_at).toLocaleString() : "Never"} />
                        </CardContent>
                    </Card>

                    {/* Access & Roles */}
                    <Card>
                        <CardHeader className="flex flex-row items-start justify-between gap-2">
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    <Shield className="h-5 w-5" />
                                    Access & Roles
                                </CardTitle>
                                <CardDescription>Institution roles and per-course assignments.</CardDescription>
                            </div>
                            <Button size="sm" variant="outline" onClick={() => setChangeRoleOpen(true)}>
                                Change roles
                            </Button>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <div className="text-xs font-medium text-muted-foreground uppercase mb-2">Groups</div>
                                <div className="flex flex-wrap gap-2">
                                    {groups.length === 0 ? (
                                        <span className="text-sm text-muted-foreground">None</span>
                                    ) : (
                                        groups.map((g) => (
                                            <Badge key={g} variant="secondary">
                                                {formatRoleLabel(g)}
                                            </Badge>
                                        ))
                                    )}
                                </div>
                            </div>
                            <div>
                                <div className="text-xs font-medium text-muted-foreground uppercase mb-2">Course staff</div>
                                {course_staff.length === 0 ? (
                                    <span className="text-sm text-muted-foreground">Not assigned to any courses.</span>
                                ) : (
                                    <div className="space-y-1 text-sm">
                                        {course_staff.map((row) => (
                                            <div key={row.uuid} className="flex items-center justify-between gap-2">
                                                <Link to={`/courses/manage/${row.course_slug || row.course_uuid}`} className="hover:underline truncate">
                                                    {row.course_title}
                                                </Link>
                                                <Badge variant="outline" className="text-xs capitalize">
                                                    {row.role.replace("_", " ")}
                                                </Badge>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Ownership */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Building2 className="h-5 w-5" />
                                Ownership
                            </CardTitle>
                            <CardDescription>Events and courses this user owns.</CardDescription>
                        </CardHeader>
                        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <div className="text-xs font-medium text-muted-foreground uppercase mb-2 flex items-center gap-1">
                                    <Calendar className="h-3 w-3" /> Events
                                </div>
                                {owned_events.length === 0 ? (
                                    <span className="text-sm text-muted-foreground">No owned events.</span>
                                ) : (
                                    <ul className="space-y-1 text-sm">
                                        {owned_events.map((e) => (
                                            <li key={e.uuid} className="flex items-center justify-between gap-2">
                                                <Link to={`/organizer/events/${e.uuid}/manage`} className="hover:underline truncate">
                                                    {e.title}
                                                </Link>
                                                <Badge variant="outline" className="text-xs">{e.status}</Badge>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                            <div>
                                <div className="text-xs font-medium text-muted-foreground uppercase mb-2 flex items-center gap-1">
                                    <GraduationCap className="h-3 w-3" /> Courses
                                </div>
                                {owned_courses.length === 0 ? (
                                    <span className="text-sm text-muted-foreground">No owned courses.</span>
                                ) : (
                                    <ul className="space-y-1 text-sm">
                                        {owned_courses.map((c) => (
                                            <li key={c.uuid} className="flex items-center justify-between gap-2">
                                                <Link to={`/courses/manage/${c.slug || c.uuid}`} className="hover:underline truncate">
                                                    {c.title}
                                                </Link>
                                                <Badge variant="outline" className="text-xs">{c.status}</Badge>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Certificates */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Award className="h-5 w-5" />
                                Certificates
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {certificates.length === 0 ? (
                                <div className="text-sm text-muted-foreground">No certificates issued.</div>
                            ) : (
                                <ul className="space-y-2 text-sm">
                                    {certificates.map((c) => (
                                        <li key={c.uuid} className="flex items-center justify-between gap-2">
                                            <span className="truncate">{c.title || "Untitled"}</span>
                                            <span className="text-xs text-muted-foreground">
                                                {c.issued_at ? new Date(c.issued_at).toLocaleDateString() : ""}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </CardContent>
                    </Card>

                    {/* Activity log */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Activity className="h-5 w-5" />
                                Activity log
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {recent_activity.length === 0 ? (
                                <div className="text-sm text-muted-foreground">No recorded activity.</div>
                            ) : (
                                <ul className="space-y-3 text-sm">
                                    {recent_activity.map((row, idx) => (
                                        <li key={`${row.type}-${row.at}-${idx}`} className="flex gap-3">
                                            <div className="h-2 w-2 rounded-full bg-primary mt-1.5 shrink-0" />
                                            <div className="flex-1">
                                                <div className="font-medium">{row.summary}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    {new Date(row.at).toLocaleString()}
                                                    {row.changed_by_name && <> · by {row.changed_by_name}</>}
                                                </div>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </CardContent>
                    </Card>

                    {/* Danger zone */}
                    <Card className="border-destructive/30">
                        <CardHeader>
                            <CardTitle className="text-destructive">Danger zone</CardTitle>
                            <CardDescription>Administrative actions on this account.</CardDescription>
                        </CardHeader>
                        <CardContent className="flex flex-wrap gap-3">
                            <Button
                                variant={profile.is_active ? "destructive" : "outline"}
                                onClick={handleToggleActive}
                            >
                                {profile.is_active ? (
                                    <>
                                        <UserX className="h-4 w-4 mr-2" />
                                        Deactivate account
                                    </>
                                ) : (
                                    <>
                                        <UserCheck className="h-4 w-4 mr-2" />
                                        Reactivate account
                                    </>
                                )}
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Change Role Dialog */}
            <Dialog open={changeRoleOpen} onOpenChange={setChangeRoleOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Change roles</DialogTitle>
                        <DialogDescription>
                            Select the institution roles for {profile.full_name}.
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleSaveRoles} className="space-y-4">
                        {roleError && (
                            <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                                {roleError}
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label>Roles</Label>
                            <div className="flex flex-wrap gap-2">
                                {ALL_ROLES.map((role) => (
                                    <Badge
                                        key={role}
                                        variant={selectedRoles.includes(role) ? "default" : "outline"}
                                        className="cursor-pointer select-none capitalize"
                                        onClick={() =>
                                            setSelectedRoles((prev) =>
                                                prev.includes(role)
                                                    ? prev.filter((r) => r !== role)
                                                    : [...prev, role]
                                            )
                                        }
                                    >
                                        {role.replace("_", " ")}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="submit" disabled={saving}>
                                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Save roles
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function Field({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <div className="text-xs font-medium text-muted-foreground uppercase">{label}</div>
            <div>{value}</div>
        </div>
    );
}

export default AdminUserDetailPage;
