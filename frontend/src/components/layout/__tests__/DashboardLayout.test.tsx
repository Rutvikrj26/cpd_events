import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { DashboardLayout } from "../DashboardLayout";
import * as billingApi from "@/api/billing";

vi.mock("@/api/billing", () => ({
    getSubscription: vi.fn().mockResolvedValue({
        plan: "organizer",
        status: "active",
        is_trialing: false,
    }),
}));

// Mock AuthContext
vi.mock("@/contexts/AuthContext", () => ({
    useAuth: () => ({
        user: { uuid: "test-uuid", account_type: "organizer", display_name: "Test User" },
        logout: vi.fn(),
        hasRoute: () => true,
        hasFeature: () => true,
        manifest: { routes: [], features: {} },
    }),
}));

// Mock OrganizationContext
vi.mock("@/contexts/OrganizationContext", () => ({
    useOrganization: () => ({
        currentOrg: null,
        organizations: [],
    }),
}));

const renderDashboardLayout = async () => {
    const view = render(
        <BrowserRouter>
            <DashboardLayout>
                <div data-testid="dashboard-content">Dashboard Content</div>
            </DashboardLayout>
        </BrowserRouter>
    );
    await waitFor(() => {
        expect(billingApi.getSubscription).toHaveBeenCalled();
    });
    return view;
};

describe("DashboardLayout", () => {
    it("renders sidebar and main content area", async () => {
        await renderDashboardLayout();

        // Sidebar should be present
        expect(screen.getByText("Accredit")).toBeInTheDocument();
        // Main content should be rendered
        expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
    });

    it("renders navigation links", async () => {
        await renderDashboardLayout();

        expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /events/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /profile/i })).toBeInTheDocument();
    });

    it("has sign out button", async () => {
        await renderDashboardLayout();

        expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
    });

    it("shows organizer-specific navigation items", async () => {
        await renderDashboardLayout();

        expect(screen.getByRole("link", { name: /certificates/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /billing/i })).toBeInTheDocument();
    });

    it("shows theme toggle", async () => {
        await renderDashboardLayout();

        expect(screen.getByText("Theme")).toBeInTheDocument();
    });
});
