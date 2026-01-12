import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import TeamManagementPage from "../TeamManagementPage";
import * as orgApi from "@/api/organizations";
import * as courseApi from "@/api/courses";

const mockUser = {
    uuid: "test-user-uuid",
    account_type: "organizer",
    display_name: "Test User",
};

vi.mock("@/contexts/AuthContext", () => ({
    useAuth: () => ({
        user: mockUser,
    }),
}));

vi.mock("@/contexts/OrganizationContext", () => ({
    useOrganization: () => ({
        hasRole: () => true,
        currentOrg: { user_role: "admin" },
    }),
}));

vi.mock("@/api/organizations", () => ({
    getOrganizations: vi.fn(),
    getOrganization: vi.fn(),
    getOrganizationMembers: vi.fn(),
    getOrganizationPlans: vi.fn(),
    inviteMember: vi.fn(),
    updateMember: vi.fn(),
    removeMember: vi.fn(),
    addOrganizationSeats: vi.fn(),
    lookupUser: vi.fn(),
    createOrganizationPortalSession: vi.fn(),
}));

vi.mock("@/api/courses", () => ({
    getOrganizationCourses: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
    const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
    return {
        ...actual,
        useParams: () => ({ slug: "test-org" }),
        useNavigate: () => vi.fn(),
        useLocation: () => ({ search: "" }),
    };
});

const mockOrg = {
    uuid: "org-uuid",
    name: "Test Org",
    slug: "test-org",
    user_role: "admin",
    subscription: {
        plan: "organization",
        status: "active",
        included_seats: 2,
        additional_seats: 1,
    },
};

const mockMembers = [
    {
        uuid: "member-1",
        user_uuid: "user-1",
        user_name: "Alex Organizer",
        user_email: "alex@example.com",
        role: "organizer",
        linked_from_individual: false,
        title: "Event Lead",
    },
    {
        uuid: "member-2",
        user_uuid: "user-2",
        user_name: "Casey Instructor",
        user_email: "casey@example.com",
        role: "instructor",
        linked_from_individual: true,
        title: "Instructor",
    },
];

const mockPlans = {
    organization: { name: "Organization", seat_price_cents: 12900, price_cents: 19900 },
};

const renderPage = () => {
    return render(
        <BrowserRouter>
            <TeamManagementPage />
        </BrowserRouter>
    );
};

describe("TeamManagementPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (orgApi.getOrganizations as any).mockResolvedValue([
            { uuid: "org-uuid", name: "Test Org", slug: "test-org" },
        ]);
        (orgApi.getOrganization as any).mockResolvedValue(mockOrg);
        (orgApi.getOrganizationMembers as any).mockResolvedValue(mockMembers);
        (orgApi.getOrganizationPlans as any).mockResolvedValue(mockPlans);
        (courseApi.getOrganizationCourses as any).mockResolvedValue([]);
    });

    it("renders team management header and org name", async () => {
        renderPage();

        await waitFor(() => {
            expect(screen.getByText("Team Management")).toBeInTheDocument();
        });
        expect(screen.getByText("Test Org")).toBeInTheDocument();
    });

    it("renders subscription usage and member list", async () => {
        renderPage();

        await waitFor(() => {
            expect(screen.getByText("Subscription Usage")).toBeInTheDocument();
        });
        expect(screen.getByText("Included Seats")).toBeInTheDocument();
        expect(screen.getAllByText(/Team Members/i).length).toBeGreaterThan(0);
        expect(screen.getByText("Alex Organizer")).toBeInTheDocument();
        expect(screen.getByText("Casey Instructor")).toBeInTheDocument();
    });

    it("shows manage billing action", async () => {
        renderPage();

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /manage billing/i })).toBeInTheDocument();
        });
    });
});
