import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { DashboardLayout } from "../DashboardLayout";

// Mock the auth feature. Sidebar derives nav visibility from
// `getRoleFlags(user)`, which reads `user.roles` + `user.primary_role`
// rather than the legacy `account_type`. Provide both so the role-gated
// links render.
vi.mock("@/features/auth", () => ({
    useAuth: () => ({
        user: {
            uuid: "test-uuid",
            account_type: "organizer",
            display_name: "Test User",
            full_name: "Test User",
            roles: ["organizer"],
            primary_role: "organizer",
            onboarding_completed: true,
        },
        logout: vi.fn(),
        hasRoute: () => true,
        hasFeature: () => true,
        manifest: { routes: [], features: {} },
    }),
}));

const renderDashboardLayout = async () => {
    return render(
        <BrowserRouter>
            <DashboardLayout>
                <div data-testid="dashboard-content">Dashboard Content</div>
            </DashboardLayout>
        </BrowserRouter>
    );
};

describe("DashboardLayout", () => {
    it("renders sidebar and main content area", async () => {
        await renderDashboardLayout();

        expect(screen.getByText("Accredit")).toBeInTheDocument();
        expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
    });

    it("renders navigation links", async () => {
        await renderDashboardLayout();

        expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
        // "Manage Events" — organizer-only nav item
        expect(screen.getByRole("link", { name: /manage events/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /profile/i })).toBeInTheDocument();
    });

    it("has sign out button", async () => {
        await renderDashboardLayout();

        expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
    });

    it("shows organizer-specific navigation items", async () => {
        await renderDashboardLayout();

        // Organizer-specific entries
        expect(screen.getByRole("link", { name: /contacts/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /promo codes/i })).toBeInTheDocument();
    });

    it("shows theme toggle", async () => {
        await renderDashboardLayout();

        expect(screen.getByText("Theme")).toBeInTheDocument();
    });
});
