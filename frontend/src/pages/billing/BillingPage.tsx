import React, { useEffect, useState } from 'react';
import { getSubscription, getInvoices, getBillingPortal } from '@/api/billing';
import { Subscription, Invoice } from '@/api/billing/types';
import { Button } from '@/components/ui/button';
import { CreditCard, FileText, CheckCircle, AlertCircle } from 'lucide-react';

export const BillingPage = () => {
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Parallel fetch
                const [subData, invData] = await Promise.all([
                    getSubscription().catch(() => null), // Handle 404 if no sub
                    getInvoices().catch(() => [])
                ]);
                setSubscription(subData);
                setInvoices(invData);
            } catch (error) {
                console.error("Billing load error", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleManageSubscription = async () => {
        try {
            const { url } = await getBillingPortal();
            window.location.href = url;
        } catch (e) {
            console.error("Failed to get portal url", e);
        }
    };

    if (loading) return <div className="p-8">Loading billing info...</div>;

    return (
        <div className="space-y-8">
            <h1 className="text-3xl font-bold text-slate-900">Billing & Subscription</h1>

            {/* Subscription Card */}
            <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex justify-between items-start">
                    <div>
                        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                            Current Plan
                            {subscription?.status === 'active' && <CheckCircle size={18} className="text-green-500" />}
                        </h2>
                        <p className="text-slate-500 mt-1">
                            {subscription ? `You are on the ${subscription.plan} plan.` : 'You are currently on the Free plan.'}
                        </p>
                    </div>
                    <Button onClick={handleManageSubscription}>
                        {subscription ? 'Manage Subscription' : 'Upgrade Plan'}
                    </Button>
                </div>

                {subscription && (
                    <div className="mt-6 p-4 bg-slate-50 rounded-lg border flex gap-6">
                        <div>
                            <span className="text-xs font-semibold text-slate-400 uppercase">Status</span>
                            <div className="font-medium capitalize">{subscription.status}</div>
                        </div>
                        <div>
                            <span className="text-xs font-semibold text-slate-400 uppercase">Renews On</span>
                            <div className="font-medium">{new Date(subscription.current_period_end).toLocaleDateString()}</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Invoices List */}
            <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b bg-slate-50 font-semibold text-slate-700">Payment History</div>
                {invoices.length === 0 ? (
                    <div className="p-8 text-center text-slate-500">No invoices found.</div>
                ) : (
                    <table className="w-full text-left text-sm">
                        <thead className="border-b">
                            <tr>
                                <th className="px-6 py-3 font-medium text-slate-500">Date</th>
                                <th className="px-6 py-3 font-medium text-slate-500">Amount</th>
                                <th className="px-6 py-3 font-medium text-slate-500">Status</th>
                                <th className="px-6 py-3 font-medium text-slate-500">Invoice</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {invoices.map(inv => (
                                <tr key={inv.uuid}>
                                    <td className="px-6 py-4"> - </td>{/* Date not in minimal interface, assumne it exists in real obj */}
                                    <td className="px-6 py-4 font-medium">${inv.amount_due}</td>
                                    <td className="px-6 py-4 capitalize">{inv.status}</td>
                                    <td className="px-6 py-4">
                                        {inv.pdf_url && (
                                            <a href={inv.pdf_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline flex items-center gap-1">
                                                <FileText size={14} /> PDF
                                            </a>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};
