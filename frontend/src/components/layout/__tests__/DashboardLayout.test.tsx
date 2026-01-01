import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { DashboardLayout } from "../DashboardLayout";

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

const renderDashboardLayout = () => {
    return render(
        <BrowserRouter>
            <DashboardLayout>
                <div data-testid="dashboard-content">Dashboard Content</div>
            </DashboardLayout>
        </BrowserRouter>
    );
};

describe("DashboardLayout", () => {
    it("renders sidebar and main content area", () => {
        renderDashboardLayout();

        // Sidebar should be present
        expect(screen.getByText("CPD Events")).toBeInTheDocument();
        // Main content should be rendered
        expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
    });

    it("renders navigation links", () => {
        renderDashboardLayout();

        expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /events/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /profile/i })).toBeInTheDocument();
    });

    it("has sign out button", () => {
        renderDashboardLayout();

        expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
    });

    it("shows organizer-specific navigation items", () => {
        renderDashboardLayout();

        expect(screen.getByRole("link", { name: /certificates/i })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /billing/i })).toBeInTheDocument();
    });

    it("shows theme toggle", () => {
        renderDashboardLayout();

        expect(screen.getByText("Theme")).toBeInTheDocument();
    });
});
