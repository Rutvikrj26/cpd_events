import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Mail, MapPin, Phone, Send, MessageSquare, Clock, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

const contactSchema = z.object({
    name: z.string().min(2, "Name must be at least 2 characters"),
    email: z.string().email("Invalid email address"),
    subject: z.string().min(5, "Subject must be at least 5 characters"),
    message: z.string().min(10, "Message must be at least 10 characters"),
});

export function ContactPage() {
    const [isSubmitting, setIsSubmitting] = useState(false);

    const form = useForm<z.infer<typeof contactSchema>>({
        resolver: zodResolver(contactSchema),
        defaultValues: {
            name: "",
            email: "",
            subject: "",
            message: "",
        },
    });

    function onSubmit(values: z.infer<typeof contactSchema>) {
        setIsSubmitting(true);
        // Simulate API call
        setTimeout(() => {
            console.log(values);
            toast.success("Message sent successfully! We'll get back to you soon.");
            form.reset();
            setIsSubmitting(false);
        }, 1500);
    }

    return (
        <div className="flex flex-col">
            {/* Hero Section */}
            <section className="py-16 lg:py-24 bg-background relative overflow-hidden">
                <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-gradient-to-bl from-primary/5 to-transparent rounded-full blur-3xl -z-10" />

                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-3xl mx-auto text-center">
                        <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium">
                            Contact Us
                        </Badge>
                        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground mb-6">
                            Get in Touch
                        </h1>
                        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                            Have questions about CPD Events? We'd love to hear from you. Send us a message and we'll respond within 24 hours.
                        </p>
                    </div>
                </div>
            </section>

            {/* Contact Cards */}
            <section className="py-12 bg-secondary/30">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
                        <ContactCard
                            icon={Mail}
                            title="Email Us"
                            description="support@cpdevents.com"
                            subtext="We'll respond within 24 hours"
                        />
                        <ContactCard
                            icon={Phone}
                            title="Call Us"
                            description="+1 (555) 123-4567"
                            subtext="Mon-Fri, 9am - 6pm EST"
                        />
                        <ContactCard
                            icon={Clock}
                            title="Response Time"
                            description="< 24 hours"
                            subtext="Average response time"
                        />
                    </div>
                </div>
            </section>

            {/* Contact Form Section */}
            <section className="py-16 bg-background">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid lg:grid-cols-2 gap-12 max-w-6xl mx-auto">
                        {/* Left Column: Info */}
                        <div className="space-y-8">
                            <div>
                                <h2 className="text-2xl font-bold text-foreground mb-4">
                                    How can we help?
                                </h2>
                                <p className="text-muted-foreground">
                                    Whether you have questions about features, pricing, need a demo, or anything else, our team is ready to answer all your questions.
                                </p>
                            </div>

                            <div className="bg-card rounded-2xl border border-border p-6 space-y-6">
                                <h3 className="font-semibold text-foreground flex items-center gap-2">
                                    <MessageSquare className="h-5 w-5 text-primary" />
                                    Common Topics
                                </h3>
                                <div className="space-y-4">
                                    <TopicLink label="Getting started with events" />
                                    <TopicLink label="Zoom integration setup" />
                                    <TopicLink label="Certificate customization" />
                                    <TopicLink label="Pricing and billing" />
                                    <TopicLink label="Team management" />
                                </div>
                                <div className="pt-4 border-t border-border">
                                    <p className="text-sm text-muted-foreground mb-3">
                                        Check our FAQ for quick answers
                                    </p>
                                    <Link to="/faq">
                                        <Button variant="outline" size="sm">
                                            Visit FAQ
                                            <ArrowRight className="ml-2 h-4 w-4" />
                                        </Button>
                                    </Link>
                                </div>
                            </div>

                            <div className="bg-gradient-to-br from-primary/10 to-accent/10 rounded-2xl p-6 border border-primary/20">
                                <h3 className="font-semibold text-foreground mb-2">
                                    Looking for a demo?
                                </h3>
                                <p className="text-sm text-muted-foreground mb-4">
                                    We'd love to show you around. Schedule a personalized demo with our team.
                                </p>
                                <Button className="glow-primary" size="sm">
                                    Schedule Demo
                                </Button>
                            </div>
                        </div>

                        {/* Right Column: Form */}
                        <Card className="shadow-elevated border-0 bg-card">
                            <CardContent className="p-8">
                                <h2 className="text-xl font-bold mb-6 text-foreground">Send us a message</h2>
                                <Form {...form}>
                                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                            <FormField
                                                control={form.control}
                                                name="name"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel>Your Name</FormLabel>
                                                        <FormControl>
                                                            <Input placeholder="John Doe" {...field} />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                            <FormField
                                                control={form.control}
                                                name="email"
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel>Email Address</FormLabel>
                                                        <FormControl>
                                                            <Input placeholder="john@example.com" {...field} />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        </div>

                                        <FormField
                                            control={form.control}
                                            name="subject"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Subject</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="How can we help?" {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        <FormField
                                            control={form.control}
                                            name="message"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Message</FormLabel>
                                                    <FormControl>
                                                        <Textarea
                                                            placeholder="Tell us more about your inquiry..."
                                                            className="min-h-[150px] resize-none"
                                                            {...field}
                                                        />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        <Button type="submit" className="w-full glow-primary" size="lg" disabled={isSubmitting}>
                                            {isSubmitting ? (
                                                <span className="flex items-center gap-2">
                                                    <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                    Sending...
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-2">
                                                    Send Message <Send className="h-4 w-4" />
                                                </span>
                                            )}
                                        </Button>
                                    </form>
                                </Form>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </section>
        </div>
    );
}

function ContactCard({ icon: Icon, title, description, subtext }: {
    icon: any;
    title: string;
    description: string;
    subtext: string;
}) {
    return (
        <div className="bg-card rounded-2xl border border-border p-6 text-center hover:shadow-soft transition-all duration-300">
            <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mx-auto mb-4">
                <Icon className="h-6 w-6" />
            </div>
            <h3 className="font-semibold text-foreground mb-1">{title}</h3>
            <p className="text-primary font-medium mb-1">{description}</p>
            <p className="text-xs text-muted-foreground">{subtext}</p>
        </div>
    );
}

function TopicLink({ label }: { label: string }) {
    return (
        <div className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
            <div className="h-1.5 w-1.5 rounded-full bg-primary/50" />
            {label}
        </div>
    );
}
