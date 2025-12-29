import React from "react";

export function CookiePolicyPage() {
    return (
        <div className="container mx-auto px-4 py-12 max-w-4xl">
            <h1 className="text-4xl font-bold mb-8">Cookie Policy</h1>
            <p className="text-muted-foreground mb-8">Last Updated: December 28, 2025</p>

            <div className="prose prose-slate dark:prose-invert max-w-none">
                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">1. What Are Cookies</h2>
                    <p>
                        As is common practice with almost all professional websites, this site uses cookies, which are tiny files that are downloaded to your computer, to improve your experience. This page describes what information they gather, how we use it, and why we sometimes need to store these cookies. We will also share how you can prevent these cookies from being stored, however, this may downgrade or 'break' certain elements of the site's functionality.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">2. How We Use Cookies</h2>
                    <p>
                        We use cookies for a variety of reasons detailed below. Unfortunately, in most cases, there are no industry standard options for disabling cookies without completely disabling the functionality and features they add to this site. It is recommended that you leave on all cookies if you are not sure whether you need them or not in case they are used to provide a service that you use.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">3. The Cookies We Set</h2>
                    <ul className="list-disc pl-6 space-y-2 mt-2">
                        <li>
                            <strong>Account related cookies:</strong> If you create an account with us, then we will use cookies for the management of the signup process and general administration. These will usually be deleted when you log out however in some cases they may remain afterwards to remember your site preferences when logged out.
                        </li>
                        <li>
                            <strong>Login related cookies:</strong> We use cookies when you are logged in so that we can remember this fact. This prevents you from having to log in every single time you visit a new page. These cookies are typically removed or cleared when you log out to ensure that you can only access restricted features and areas when logged in.
                        </li>
                    </ul>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">4. Third Party Cookies</h2>
                    <p>
                        In some special cases, we also use cookies provided by trusted third parties. The following section details which third party cookies you might encounter through this site.
                    </p>
                    <ul className="list-disc pl-6 space-y-2 mt-2">
                        <li>
                            <strong>Stripe:</strong> We use Stripe for payment processing. Stripe may set cookies to help detect and prevent fraud and to ensure the secure processing of your payment.
                        </li>
                        <li>
                            <strong>Zoom:</strong> We integrate with Zoom to provide video conferencing features. Zoom may use cookies to enable these features and to analyze service usage.
                        </li>
                        <li>
                            <strong>Analytics:</strong> This site may use analytics solutions to understand how you use the site and ways that we can improve your experience. These cookies may track things such as how long you spend on the site and the pages that you visit so we can continue to produce engaging content.
                        </li>
                    </ul>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">5. Disabling Cookies</h2>
                    <p>
                        You can prevent the setting of cookies by adjusting the settings on your browser (see your browser Help for how to do this). Be aware that disabling cookies will affect the functionality of this and many other websites that you visit. Disabling cookies will usually result in also disabling certain functionality and features of this site. Therefore, it is recommended that you do not disable cookies.
                    </p>
                </section>

                <section className="mb-8">
                    <h2 className="text-2xl font-semibold mb-4">6. More Information</h2>
                    <p>
                        Hopefully, that has clarified things for you. If there is something that you aren't sure whether you need or not, it's usually safer to leave cookies enabled in case it does interact with one of the features you use on our site.
                    </p>
                    <p className="mt-4">
                        For more general information on cookies, please read a "What Are Cookies" article.
                    </p>
                    <p className="mt-4">
                        However, if you are still looking for more information, you can contact us via email at: privacy@accredit.com.
                    </p>
                </section>
            </div>
        </div>
    );
}
