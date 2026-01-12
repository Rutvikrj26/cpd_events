import React from "react";
import { Link } from "react-router-dom";
import {
    HelpCircle,
    Calendar,
    Video,
    Award,
    CreditCard,
    Users,
    Mail
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";

const faqCategories = [
    {
        id: "general",
        name: "General",
        icon: HelpCircle,
        questions: [
            {
                q: "What is Accredit?",
                a: "Accredit is a comprehensive platform for managing professional development events. It enables you to create events, track attendance automatically through Zoom integration, and issue verifiable certificates to attendees who meet your requirements."
            },
            {
                q: "Who is Accredit for?",
                a: "Accredit is designed for professional associations, training providers, corporate L&D teams, and any organization that hosts educational events and needs to track attendance and issue CPD certificates."
            },
            {
                q: "Is there a free plan?",
                a: "Yes! You can start using Accredit for free. The free plan includes basic event management, Zoom integration, and certificate issuance. Upgrade to a paid plan for additional features like custom branding and team management."
            },
            {
                q: "Do I need technical skills to use Accredit?",
                a: "No technical skills required. Our intuitive interface guides you through event creation, and attendance tracking is automatic when connected to Zoom. If you can use email and basic web applications, you can use Accredit."
            }
        ]
    },
    {
        id: "events",
        name: "Events",
        icon: Calendar,
        questions: [
            {
                q: "What event formats are supported?",
                a: "Accredit supports three formats: Online (virtual events via Zoom), In-Person (physical events with manual check-in), and Hybrid (combination of both). You can also create multi-session events for programs that span multiple days or sessions."
            },
            {
                q: "Can I create multi-session events?",
                a: "Yes! Multi-session events are perfect for training programs, conferences, or courses that span multiple days. Each session can have its own schedule, and attendance is tracked per session. Certificates can be issued based on overall attendance across all sessions."
            },
            {
                q: "How do I manage registrations?",
                a: "Registrations are managed through your event dashboard. You can set capacity limits, enable waitlists, require approval for registrations, and add custom fields to collect additional information from registrants."
            },
            {
                q: "Can I set CPD credits for my events?",
                a: "Absolutely. When creating an event, you can specify the number of CPD credits, the CPD credit type (e.g., CME, CLE, CPE), and any accreditation information. This information appears on certificates."
            }
        ]
    },
    {
        id: "zoom",
        name: "Zoom Integration",
        icon: Video,
        questions: [
            {
                q: "How do I connect my Zoom account?",
                a: "Navigate to Settings → Integrations in your dashboard and click 'Connect Zoom'. You'll be redirected to Zoom to authorize the connection. Once connected, Accredit can automatically create meetings and track attendance for your events."
            },
            {
                q: "How is attendance tracked?",
                a: "When connected to Zoom, attendance is tracked automatically via webhooks. The platform logs when each participant joins and leaves the meeting, calculates their attendance percentage, and determines eligibility for certificates based on your threshold."
            },
            {
                q: "What if someone joins late or leaves early?",
                a: "The system tracks the total time each participant spends in the meeting and calculates an attendance percentage. For example, if someone attends 45 minutes of a 60-minute session, their attendance would be 75%. You can set the minimum threshold for certificate eligibility."
            },
            {
                q: "Can I use my existing Zoom account?",
                a: "Yes! Accredit connects to your existing Zoom account via OAuth. We don't require a special Zoom plan - any Zoom account (including free accounts) can be connected. However, some features like automatic recording require a Zoom Pro plan or higher."
            },
            {
                q: "What about in-person events?",
                a: "For in-person events, attendance is tracked via manual check-in. Organizers can mark attendees as present from the event management dashboard, and you can also set attendance percentages manually if needed."
            }
        ]
    },
    {
        id: "certificates",
        name: "Certificates",
        icon: Award,
        questions: [
            {
                q: "How are certificates generated?",
                a: "Certificates are generated as PDF documents based on your certificate template. When an attendee meets your attendance threshold, you can issue a certificate with one click. The system automatically populates attendee details, event information, and CPD credits."
            },
            {
                q: "Can I customize certificate templates?",
                a: "Yes! You can upload custom certificate templates and position fields (name, date, event title, etc.) exactly where you want them. This allows you to maintain your organization's branding on all certificates."
            },
            {
                q: "How does certificate verification work?",
                a: "Every certificate includes a unique verification code. Anyone can verify a certificate's authenticity by visiting our public verification page and entering the code. This helps employers and professional bodies confirm credentials."
            },
            {
                q: "Can attendees download their certificates?",
                a: "Yes. Once a certificate is issued, attendees can download it as a PDF from their dashboard. They also receive an email notification with a download link."
            },
            {
                q: "Can I issue certificates in bulk?",
                a: "Yes! From your event management page, you can issue certificates to all eligible attendees at once. The system will generate and send certificates to everyone who met your attendance requirements."
            }
        ]
    },
    {
        id: "teams",
        name: "Teams & Organizations",
        icon: Users,
        questions: [
            {
                q: "What are organizations?",
                a: "Organizations allow you to manage events and courses as a team. You can invite team members, assign roles (Admin, Organizer, Course Manager, Instructor), and share resources like certificate templates across your organization."
            },
            {
                q: "What roles are available?",
                a: "There are four roles: Admin (org settings, members, templates), Organizer (events and contacts), Course Manager (courses and instructors), and Instructor (assigned courses). Each role has permissions tailored to their responsibilities."
            },
            {
                q: "Can I have multiple organizations?",
                a: "Yes, you can create multiple organizations or be a member of several organizations. This is useful if you work with different teams or manage events for multiple groups."
            }
        ]
    },
    {
        id: "billing",
        name: "Pricing & Billing",
        icon: CreditCard,
        questions: [
            {
                q: "What payment methods do you accept?",
                a: "We accept all major credit cards (Visa, Mastercard, American Express) via our secure payment processor. For enterprise plans, we can also arrange invoice billing."
            },
            {
                q: "Can I upgrade or downgrade my plan?",
                a: "Yes, you can change your plan at any time. Upgrades take effect immediately, and you'll be charged a prorated amount for the remainder of your billing period. Downgrades take effect at the start of your next billing period."
            },
            {
                q: "Is there a discount for annual billing?",
                a: "Yes! Annual billing includes a discount compared to monthly billing. The exact discount varies by plan - check our pricing page for current rates."
            },
            {
                q: "What happens if I exceed my plan limits?",
                a: "If you approach your plan limits, we'll notify you before you exceed them. You can either upgrade your plan or wait until your next billing cycle when limits reset."
            }
        ]
    }
];

export function FAQPage() {
    const [activeCategory, setActiveCategory] = React.useState("general");

    const currentCategory = faqCategories.find(cat => cat.id === activeCategory) || faqCategories[0];

    return (
        <div className="flex flex-col">
            {/* Hero Section */}
            <section className="py-16 lg:py-24 bg-background">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-3xl mx-auto text-center">
                        <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium">
                            Support
                        </Badge>
                        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground mb-6">
                            Frequently Asked Questions
                        </h1>
                        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                            Find answers to common questions about Accredit. Can't find what you're looking for? Contact our support team.
                        </p>
                    </div>
                </div>
            </section>

            {/* FAQ Content */}
            <section className="py-16 bg-secondary/30">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                        {/* Category Sidebar */}
                        <div className="lg:col-span-1">
                            <div className="sticky top-24 space-y-2">
                                <h3 className="text-sm font-semibold text-foreground mb-4 px-3">Categories</h3>
                                {faqCategories.map((category) => (
                                    <button
                                        key={category.id}
                                        onClick={() => setActiveCategory(category.id)}
                                        className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${activeCategory === category.id
                                            ? 'bg-primary text-primary-foreground'
                                            : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                                            }`}
                                    >
                                        <category.icon className="h-4 w-4" />
                                        {category.name}
                                        <span className={`ml-auto text-xs ${activeCategory === category.id ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                                            {category.questions.length}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Questions */}
                        <div className="lg:col-span-3">
                            <div className="bg-card rounded-2xl border border-border p-6 lg:p-8">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                                        <currentCategory.icon className="h-5 w-5" />
                                    </div>
                                    <h2 className="text-xl font-semibold text-foreground">{currentCategory.name}</h2>
                                </div>

                                <Accordion type="single" collapsible className="space-y-3">
                                    {currentCategory.questions.map((faq, index) => (
                                        <AccordionItem
                                            key={index}
                                            value={`item-${index}`}
                                            className="border border-border rounded-xl px-4 data-[state=open]:bg-secondary/30"
                                        >
                                            <AccordionTrigger className="text-left font-medium text-foreground hover:no-underline py-4">
                                                {faq.q}
                                            </AccordionTrigger>
                                            <AccordionContent className="text-muted-foreground pb-4 leading-relaxed">
                                                {faq.a}
                                            </AccordionContent>
                                        </AccordionItem>
                                    ))}
                                </Accordion>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Contact CTA */}
            <section className="py-16 bg-background">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-2xl mx-auto text-center">
                        <div className="h-14 w-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto mb-6">
                            <Mail className="h-7 w-7" />
                        </div>
                        <h2 className="text-2xl font-bold text-foreground mb-4">
                            Still have questions?
                        </h2>
                        <p className="text-muted-foreground mb-8">
                            Our support team is here to help. Reach out and we'll get back to you within 24 hours.
                        </p>
                        <Link to="/contact">
                            <Button size="lg" className="glow-primary">
                                Contact Support
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>
        </div>
    );
}
