import { Link } from "react-router-dom";
import {
    ArrowRight,
    Award,
    BookOpen,
    Calendar,
    GraduationCap,
    PlayCircle,
    Sparkles,
} from "lucide-react";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/empty-state";
import { CardRow, AvatarTile } from "@/shared/components";
import { useAuth } from "@/features/auth";
import {
    HeroBand,
    MiniStat,
    SectionHeader,
    DashboardSkeleton,
    useAttendeeDashboard,
    type ResumeCandidate,
} from "@/features/dashboard";
import { RegistrationRow } from "@/features/events";

const TITLE_PREFIXES = new Set([
    'dr', 'dr.', 'mr', 'mr.', 'mrs', 'mrs.', 'ms', 'ms.',
    'prof', 'prof.', 'professor', 'sir', 'madam', 'rev', 'rev.',
]);

function friendlyFirstName(fullName?: string | null): string {
    if (!fullName) return '';
    const parts = fullName.trim().split(/\s+/);
    const first = parts.find((p) => !TITLE_PREFIXES.has(p.toLowerCase()) && p.length > 1);
    return (first || parts[0] || '').replace(/,$/, '');
}

export function AttendeeDashboard() {
    const { user } = useAuth();
    const dashboard = useAttendeeDashboard();
    const firstName = friendlyFirstName(user?.full_name) || 'there';

    if (dashboard.isLoading) {
        return <DashboardSkeleton />;
    }

    const { resumeTarget, stats, upcomingRegistrations, recentCertificates } = dashboard;

    return (
        <div className="space-y-block animate-in fade-in slide-in-from-bottom-4 duration-500">
            {resumeTarget ? (
                <HeroBand
                    eyebrow={`Welcome back, ${firstName}`}
                    title="Continue where you left off"
                    description={resumeTarget.courseTitle}
                    progressPercent={resumeTarget.progressPercent}
                    actions={[
                        {
                            label: <><PlayCircle className="mr-2 h-5 w-5" /> Resume course</>,
                            to: `/learn/${resumeTarget.courseUuid}`,
                            primary: true,
                        },
                        {
                            label: <>My learning <ArrowRight className="ml-1 h-4 w-4" /></>,
                            to: '/registrations',
                        },
                    ]}
                />
            ) : (
                <HeroBand
                    eyebrow={`Hello, ${firstName}`}
                    title="Ready to learn something new?"
                    description="Explore the course catalog or browse upcoming events to start earning CPD credits."
                    actions={[
                        { label: 'Browse courses', to: '/courses', primary: true },
                        {
                            label: <>Find an event <ArrowRight className="ml-1 h-4 w-4" /></>,
                            to: '/events',
                        },
                    ]}
                />
            )}

            <div className="grid grid-cols-2 gap-tight lg:grid-cols-4">
                <MiniStat label="Active courses" value={stats.activeCourses} icon={BookOpen} tone="primary" />
                <MiniStat label="Upcoming events" value={stats.upcomingEvents} icon={Calendar} tone="warning" />
                <MiniStat label="Certificates" value={stats.certificates} icon={GraduationCap} tone="success" />
                <MiniStat label="CPD credits" value={stats.totalCredits} icon={Award} tone="muted" />
            </div>

            <div className="grid grid-cols-1 gap-card lg:grid-cols-3">
                <div className="space-y-card lg:col-span-2">
                    <SectionHeader
                        title="Up next this week"
                        link={
                            upcomingRegistrations.length > 0
                                ? { to: '/registrations', label: 'View all' }
                                : undefined
                        }
                    />
                    {upcomingRegistrations.length === 0 ? (
                        <EmptyState
                            tone="dashed"
                            icon={Calendar}
                            title="No upcoming events"
                            description="Browse the catalog to find your next learning opportunity."
                            action={
                                <Button asChild>
                                    <Link to="/events">Browse events</Link>
                                </Button>
                            }
                        />
                    ) : (
                        <div className="space-y-tight">
                            {upcomingRegistrations.slice(0, 4).map((reg) => (
                                <RegistrationRow key={reg.uuid} reg={reg} />
                            ))}
                        </div>
                    )}
                </div>

                <div className="space-y-card">
                    <SectionHeader
                        title="Recently earned"
                        link={
                            recentCertificates.length > 0
                                ? { to: '/certificates', label: 'See all' }
                                : undefined
                        }
                    />
                    {recentCertificates.length === 0 ? (
                        <EmptyState
                            tone="muted"
                            icon={Sparkles}
                            title="No certificates yet"
                            description="Complete a course or attend an event to earn your first certificate."
                            className="min-h-[14rem]"
                        />
                    ) : (
                        <div className="space-y-tight">
                            {recentCertificates.map((cert: any) => (
                                <RecentCertificateRow key={cert.uuid || cert.id} cert={cert} />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Page-local row composers — bind to certificate shape. If they      */
/* recur, promote to features/dashboard/components/.                   */
/* ------------------------------------------------------------------ */

function RecentCertificateRow({ cert }: { cert: any }) {
    const issued = cert.issued_at || cert.created_at;
    const issuedLabel = issued
        ? new Date(issued).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
          })
        : 'Recently';
    const title = cert.title || cert.event_title || cert.course_title || 'Certificate';
    return (
        <CardRow
            density="compact"
            leading={<AvatarTile icon={GraduationCap} tone="success" />}
            title={title}
            subtitle={`Issued ${issuedLabel}`}
            trailing={
                <Button size="sm" variant="ghost" asChild>
                    <Link to={`/certificates/${cert.uuid || cert.id}`} aria-label={`View ${title}`}>
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </Button>
            }
        />
    );
}

// Suppress "unused" warning kept here for the type re-export.
export type { ResumeCandidate };
