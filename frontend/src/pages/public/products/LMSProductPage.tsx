
import {
    BookOpen,
    Users,
    Award,
    CheckCircle2,
    ArrowRight,
    BarChart3,
    FileCheck,
    BrainCircuit,
    Layers,
    Clock,
    Unlock
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// --- Visual Components ---

function HeroCourseMockup() {
    return (
        <div className="relative animate-fade-in-up">
            {/* Main Course Card */}
            <div className="bg-card rounded-2xl border border-border shadow-elevated overflow-hidden">
                {/* Header Bar */}
                <div className="bg-accent/5 border-b border-border px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center">
                            <BookOpen className="h-4 w-4 text-accent-foreground" />
                        </div>
                        <div>
                            <p className="font-semibold text-foreground text-sm">Course Manager</p>
                            <p className="text-xs text-muted-foreground">Accredit LMS</p>
                        </div>
                    </div>
                    <Badge variant="secondary" className="text-xs bg-accent/10 text-accent border-accent/20">Active</Badge>
                </div>

                {/* Dashboard Content */}
                <div className="p-6 space-y-4">
                    <div className="grid grid-cols-3 gap-3">
                        <div className="bg-secondary/50 rounded-xl p-4 text-center">
                            <div className="flex items-center justify-center mb-2">
                                <Users className="h-5 w-5 text-accent" />
                            </div>
                            <p className="text-lg font-bold text-foreground">156</p>
                            <p className="text-xs text-muted-foreground">Students</p>
                        </div>
                        <div className="bg-secondary/50 rounded-xl p-4 text-center">
                            <div className="flex items-center justify-center mb-2">
                                <BarChart3 className="h-5 w-5 text-foreground" />
                            </div>
                            <p className="text-lg font-bold text-foreground">82%</p>
                            <p className="text-xs text-muted-foreground">Engagement</p>
                        </div>
                        <div className="bg-secondary/50 rounded-xl p-4 text-center">
                            <div className="flex items-center justify-center mb-2">
                                <Award className="h-5 w-5 text-accent" />
                            </div>
                            <p className="text-lg font-bold text-foreground">94</p>
                            <p className="text-xs text-muted-foreground">Graduated</p>
                        </div>
                    </div>

                    <div className="bg-secondary/30 rounded-xl p-4">
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-lg bg-accent/10 flex items-center justify-center">
                                    <FileCheck className="h-5 w-5 text-accent" />
                                </div>
                                <div>
                                    <p className="font-medium text-foreground text-sm">Ethics & Compliance</p>
                                    <p className="text-xs text-muted-foreground">8 Modules • 3 Quizzes</p>
                                </div>
                            </div>
                            <Badge className="bg-accent/10 text-accent border-0 text-xs">Self-Paced</Badge>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-2">
                            <div className="bg-accent h-2 rounded-full" style={{ width: '45%' }}></div>
                        </div>
                    </div>

                    <Button className="w-full bg-accent hover:bg-accent/90" size="sm">
                        <BookOpen className="h-4 w-4 mr-2" />
                        Manage Content
                    </Button>
                </div>
            </div>

            <div className="absolute -right-4 top-16 bg-card p-3 rounded-xl shadow-elevated border border-border hidden md:flex items-center gap-3 animate-float">
                <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center text-accent">
                    <CheckCircle2 className="h-4 w-4" />
                </div>
                <div>
                    <p className="text-xs font-medium text-foreground">Quiz Passed</p>
                    <p className="text-[10px] text-muted-foreground">Score: 95%</p>
                </div>
            </div>
        </div>
    );
}

// --- Main Page Component ---

export default function LMSProductPage() {
    return (
        <div className="flex flex-col min-h-screen bg-background">
            {/* Hero Section */}
            <section className="relative pt-32 pb-20 overflow-hidden">
                <div className="container px-4 mx-auto relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="text-left animate-fade-in-up">
                            <Badge className="mb-4 bg-accent/10 text-accent hover:bg-accent/20 transition-colors border-0">
                                For Course Creators & Educators
                            </Badge>
                            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6">
                                Build & Sell <span className="text-accent">Online Courses</span>
                            </h1>
                            <p className="text-xl text-muted-foreground mb-8 text-balance">
                                Create engaging self-paced learning experiences or support your live cohorts with a robust LMS.
                                Quizzes, certificates, and drip content included.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Link to="/signup?role=course_manager&plan=lms">
                                    <Button size="lg" className="h-12 px-8 text-base shadow-lg shadow-accent/20 bg-accent hover:bg-accent/90 w-full sm:w-auto">
                                        Create Course
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Button>
                                </Link>
                                <Link to="/contact">
                                    <Button variant="outline" size="lg" className="h-12 px-8 text-base w-full sm:w-auto">
                                        See Examples
                                    </Button>
                                </Link>
                            </div>
                        </div>
                        <div className="relative mx-auto w-full max-w-[500px] lg:max-w-none">
                            <div className="absolute inset-0 bg-accent/20 blur-[100px] rounded-full opacity-20 animate-pulse-slow" />
                            <HeroCourseMockup />
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Grid */}
            <section className="py-20 bg-secondary/20">
                <div className="container px-4 mx-auto">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Powerful tools for modern learning</h2>
                        <p className="text-lg text-muted-foreground">Whether you're teaching one student or ten thousand, our LMS scales with you.</p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={Layers}
                            title="Drag & Drop Builder"
                            description="Upload videos, PDFs, and rich text. Organize content into modules and lessons with a simple intuitive interface."
                        />
                        <FeatureCard
                            icon={BrainCircuit}
                            title="Quizzes & Assignments"
                            description="Test knowledge with auto-graded quizzes or detailed assignments complete with instructor feedback and rubrics."
                        />
                        <FeatureCard
                            icon={Clock}
                            title="Drip Content"
                            description="Release content on a schedule. Unlock modules based on start date, days after enrollment, or prerequisite completion."
                        />
                        <FeatureCard
                            icon={Unlock}
                            title="Progress Tracking"
                            description="Detailed progress reporting for both students and instructors. See exactly where learners are getting stuck."
                        />
                        <FeatureCard
                            icon={Users}
                            title="Cohort Management"
                            description="Perfect for virtual cohorts. Combine self-paced content with live session schedules in one unified view."
                        />
                        <FeatureCard
                            icon={Award}
                            title="Certification"
                            description="Automatically award CPD certificates upon course completion. customizable templates included."
                        />
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-24 bg-card border-y border-border">
                <div className="container px-4 mx-auto text-center">
                    <h2 className="text-3xl font-bold tracking-tight text-foreground mb-6">Start sharing your knowledge</h2>
                    <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
                        Turn your expertise into a scalable revenue stream with Accredit LMS.
                    </p>
                    <Link to="/signup?role=course_manager&plan=lms">
                        <Button size="lg" className="h-14 px-10 text-lg shadow-xl shadow-accent/20 bg-accent hover:bg-accent/90">
                            Start Building for Free
                        </Button>
                    </Link>
                </div>
            </section>
        </div>
    );
}

function FeatureCard({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
    return (
        <div className="group bg-card p-8 rounded-2xl border border-border shadow-soft hover:shadow-elevated transition-all duration-300 hover:-translate-y-1">
            <div className="h-12 w-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center mb-6 group-hover:bg-accent/20 transition-colors duration-300">
                <Icon className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-3">{title}</h3>
            <p className="text-muted-foreground leading-relaxed">{description}</p>
        </div>
    );
}
