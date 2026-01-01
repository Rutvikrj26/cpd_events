import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { EventDiscovery } from "../EventDiscovery";

// Mock the API call
vi.mock("@/api/events", () => ({
    getPublicEvents: vi.fn().mockResolvedValue([]),
}));

const renderEventDiscovery = () => {
    return render(
        <BrowserRouter>
            <EventDiscovery />
        </BrowserRouter>
    );
};

describe("EventDiscovery", () => {
    it("renders page header", () => {
        renderEventDiscovery();

        expect(screen.getByText("Browse Events")).toBeInTheDocument();
        expect(screen.getByText(/discover professional development/i)).toBeInTheDocument();
    });

    it("renders search input", () => {
        renderEventDiscovery();

        expect(screen.getByPlaceholderText(/search events/i)).toBeInTheDocument();
    });

    it("renders filter options", () => {
        renderEventDiscovery();

        expect(screen.getByText("Event Type")).toBeInTheDocument();
        expect(screen.getByText("Format")).toBeInTheDocument();
        expect(screen.getByText("Registration Fee")).toBeInTheDocument();
    });

    it("has event type filter checkboxes", () => {
        renderEventDiscovery();

        expect(screen.getByLabelText("Webinar")).toBeInTheDocument();
        expect(screen.getByLabelText("Workshop")).toBeInTheDocument();
        expect(screen.getByLabelText("Course")).toBeInTheDocument();
        expect(screen.getByLabelText("Conference")).toBeInTheDocument();
    });

    it("has format filter checkboxes", () => {
        renderEventDiscovery();

        expect(screen.getByLabelText("Online")).toBeInTheDocument();
        expect(screen.getByLabelText("In-Person")).toBeInTheDocument();
        expect(screen.getByLabelText("Hybrid")).toBeInTheDocument();
    });

    it("has sort dropdown", () => {
        renderEventDiscovery();

        expect(screen.getByText("Upcoming")).toBeInTheDocument();
    });

    it("renders reset filters button", () => {
        renderEventDiscovery();

        expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
    });

    it("shows empty state when no events loaded", async () => {
        renderEventDiscovery();

        // Wait for loading to finish and check for empty state
        await waitFor(() => {
            expect(screen.queryByText(/no events found/i)).toBeInTheDocument();
        });
    });
});
