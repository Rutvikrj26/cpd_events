import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Mail, MapPin, Phone, Send, MessageSquare } from "lucide-react";
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
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "sonner";
import contactIllustration from "@/assets/images/contact-illustration.png";

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
        <div className="flex flex-col min-h-screen">
            <div className="container mx-auto px-4 py-12">
                <PageHeader
                    title="Contact Us"
                    description="Have questions? We'd love to hear from you."
                    className="mb-8"
                />

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
                    {/* Left Column: Contact Info */}
                    <div className="space-y-8">
                        <div className="relative rounded-2xl overflow-hidden bg-blue-50 border border-blue-100 p-8">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-100 rounded-bl-full -mr-8 -mt-8 opacity-50"></div>
                            <div className="relative z-10">
                                <h3 className="text-xl font-bold text-blue-900 mb-6 flex items-center gap-2">
                                    <MessageSquare className="h-5 w-5" /> Get in touch
                                </h3>
                                <div className="space-y-6">
                                    <div className="flex items-start gap-4">
                                        <div className="bg-card p-2 rounded-full shadow-sm text-blue-600">
                                            <MapPin className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground">Headquarters</p>
                                            <p className="text-slate-600">123 Innovation Drive,<br />Tech City, TC 90210</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-4">
                                        <div className="bg-card p-2 rounded-full shadow-sm text-blue-600">
                                            <Mail className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground">Email Us</p>
                                            <p className="text-slate-600">support@cpdevents.com</p>
                                            <p className="text-slate-600">sales@cpdevents.com</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-4">
                                        <div className="bg-card p-2 rounded-full shadow-sm text-blue-600">
                                            <Phone className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground">Call Us</p>
                                            <p className="text-slate-600">+1 (555) 123-4567</p>
                                            <p className="text-xs text-muted-foreground">Mon-Fri, 9am - 6pm EST</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-muted rounded-2xl overflow-hidden h-64 border border-border relative flex items-center justify-center">
                            <img
                                src={contactIllustration}
                                alt="Contact Support"
                                className="w-full h-full object-cover opacity-80"
                            />
                        </div>
                    </div>

                    {/* Right Column: Contact Form */}
                    <Card className="shadow-lg border-t-4 border-t-primary">
                        <CardContent className="p-8">
                            <h2 className="text-2xl font-bold mb-6 text-foreground">Send us a message</h2>
                            <Form {...form}>
                                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                                                        className="min-h-[150px]"
                                                        {...field}
                                                    />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
                                        {isSubmitting ? (
                                            <span className="flex items-center gap-2">
                                                <span className="animate-spin">⏳</span> Sending...
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
        </div>
    );
}
