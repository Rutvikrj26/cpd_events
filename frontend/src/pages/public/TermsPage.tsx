import React from "react";


export function TermsPage() {
    return (
        <div className="container mx-auto px-4 py-12 max-w-4xl">
            <h1 className="text-4xl font-bold mb-8">Terms of Service</h1>
            <p className="text-muted-foreground mb-8">Last Updated: December 28, 2025</p>

            <div className="prose prose-slate dark:prose-invert max-w-none">
                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">1. Acceptance of Terms</h2>
                    <p>
                        By accessing or using the Accredit platform ("Service"), you agree to be bound by these Terms of Service ("Terms"). If you disagree with any part of the terms, you may not access the Service.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">2. Description of Service</h2>
                    <p>
                        Accredit is a Continuing Professional Development (CPD) management platform that allows organizers to create events, issue certificates, and track attendance, and allows attendees to register for events and manage their CPD records.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">3. User Accounts</h2>
                    <p>
                        When you create an account with us, you must provide us with information that is accurate, complete, and current at all times. Failure to do so constitutes a breach of the Terms, which may result in immediate termination of your account on our Service.
                    </p>
                    <p className="mt-4">
                        You are responsible for safeguarding the password that you use to access the Service and for any activities or actions under your password.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">4. Content</h2>
                    <p>
                        Our Service allows you to post, link, store, share and otherwise make available certain information, text, graphics, videos, or other material ("Content"). You are responsible for the Content that you post to the Service, including its legality, reliability, and appropriateness.
                    </p>
                    <p className="mt-4">
                        By posting Content to the Service, you grant us the right and license to use, modify, publicly perform, publicly display, reproduce, and distribute such Content on and through the Service. You retain any and all of your rights to any Content you submit, post or display on or through the Service and you are responsible for protecting those rights.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">5. Payments and Subscriptions</h2>
                    <ul className="list-disc pl-6 space-y-2">
                        <li><strong>Billing:</strong> Some parts of the Service are billed on a subscription basis ("Subscription(s)"). You will be billed in advance on a recurring and periodic basis ("Billing Cycle").</li>
                        <li><strong>Payment Methods:</strong> You must provide a valid payment method. By providing such information, you authorize us to charge all Subscription fees to that payment method.</li>
                        <li><strong>Cancellations:</strong> You may cancel your Subscription at any time. Your cancellation will take effect at the end of the current Billing Cycle. There are no refunds for partial Subscription periods.</li>
                        <li><strong>Fee Changes:</strong> Accredit, in its sole discretion and at any time, may modify the Subscription fees. Any Subscription fee change will become effective at the end of the then-current Billing Cycle.</li>
                    </ul>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">6. Intellectual Property</h2>
                    <p>
                        The Service and its original content (excluding Content provided by users), features and functionality are and will remain the exclusive property of Accredit and its licensors. The Service is protected by copyright, trademark, and other laws of both Canada and foreign countries.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">7. Termination</h2>
                    <p>
                        We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms. Upon termination, your right to use the Service will immediately cease.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">8. Limitation of Liability</h2>
                    <p>
                        In no event shall Accredit, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from (i) your access to or use of or inability to access or use the Service; (ii) any conduct or content of any third party on the Service; (iii) any content obtained from the Service; and (iv) unauthorized access, use or alteration of your transmissions or content.
                    </p>
                    <p className="mt-4">
                        Accredit operates solely as a marketplace and technology platform. We do not issue, validate, or endorse the content of any certificates generated through our Service. These certificates are issued directly by event organizers and content creators using our platform. Consequently, Accredit assumes no liability for the legitimacy, accuracy, or acceptance of such certificates.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">9. Governing Law</h2>
                    <p>
                        These Terms shall be governed and construed in accordance with the laws of Ontario, Canada, without regard to its conflict of law provisions.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">10. Changes</h2>
                    <p>
                        We reserve the right, at our sole discretion, to modify or replace these Terms at any time. If a revision is material we will try to provide at least 30 days notice prior to any new terms taking effect. What constitutes a material change will be determined at our sole discretion.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">11. Contact Us</h2>
                    <p>
                        If you have any questions about these Terms, please contact us at support@accredit.com.
                    </p>
                </section>
            </div>
        </div>
    );
}
