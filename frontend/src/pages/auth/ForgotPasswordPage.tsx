import React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Link } from "react-router-dom";
import { Mail, ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { resetPassword } from "@/api/accounts";

const forgotPasswordSchema = z.object({
    email: z.string().email("Please enter a valid email address"),
});

export function ForgotPasswordPage() {
    const [isSubmitting, setIsSubmitting] = React.useState(false);
    const [isSent, setIsSent] = React.useState(false);

    const form = useForm<z.infer<typeof forgotPasswordSchema>>({
        resolver: zodResolver(forgotPasswordSchema),
        defaultValues: {
            email: "",
        },
    });

    async function onSubmit(values: z.infer<typeof forgotPasswordSchema>) {
        setIsSubmitting(true);
        try {
            await resetPassword({ email: values.email });
            setIsSent(true);
            toast.success("Password reset link sent to your email.");
        } catch (error) {
            // Even if the email doesn't exist, we show success for security
            // The API should handle this gracefully
            setIsSent(true);
            toast.success("If an account exists with this email, you'll receive a reset link.");
        } finally {
            setIsSubmitting(false);
        }
    }

    if (isSent) {
        return (
            <Card className="w-full max-w-md mx-auto shadow-lg">
                <CardHeader className="text-center">
                    <div className="mx-auto w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mb-4">
                        <Mail className="h-6 w-6 text-green-600" />
                    </div>
                    <CardTitle className="text-xl">Check your email</CardTitle>
                    <CardDescription>
                        We've sent a password reset link to <span className="font-semibold text-foreground">{form.getValues().email}</span>
                    </CardDescription>
                </CardHeader>
                <CardContent className="text-center space-y-4">
                    <p className="text-sm text-muted-foreground">
                        Didn't receive the email? Check your spam folder or try again.
                    </p>
                    <Button variant="outline" onClick={() => setIsSent(false)} className="w-full">
                        Try a different email
                    </Button>
                </CardContent>
                <CardFooter className="justify-center">
                    <Button variant="link" asChild>
                        <Link to="/login" className="flex items-center text-muted-foreground">
                            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Login
                        </Link>
                    </Button>
                </CardFooter>
            </Card>
        );
    }

    return (
        <Card className="w-full max-w-md mx-auto shadow-lg">
            <CardHeader className="text-center">
                <CardTitle className="text-2xl font-bold">Forgot Password?</CardTitle>
                <CardDescription>
                    Enter your email address and we'll send you a link to reset your password.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="email"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Email Address</FormLabel>
                                    <FormControl>
                                        <div className="relative">
                                            <Mail className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                                            <Input placeholder="name@example.com" className="pl-10" {...field} />
                                        </div>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <Button type="submit" className="w-full" disabled={isSubmitting}>
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Sending Link...
                                </>
                            ) : "Send Reset Link"}
                        </Button>
                    </form>
                </Form>
            </CardContent>
            <CardFooter className="justify-center">
                <Button variant="link" asChild>
                    <Link to="/login" className="flex items-center text-muted-foreground hover:text-foreground">
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back to Login
                    </Link>
                </Button>
            </CardFooter>
        </Card>
    );
}
