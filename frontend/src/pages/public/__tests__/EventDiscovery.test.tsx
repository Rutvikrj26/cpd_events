import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { EventDiscovery } from "../EventDiscovery";

// Mock the API call. The page expects the paginated `{results: []}`
// shape — returning a bare array crashes the `[...events]` spread on
// undefined inside `useMemo`.
vi.mock("@/api/events", () => ({
    getPublicEvents: vi
        .fn()
        .mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

const renderEventDiscovery = async () => {
    const view = render(
        <BrowserRouter>
            <EventDiscovery />
        </BrowserRouter>
    );
    await waitFor(() => {
        expect(screen.getByText(/no events found/i)).toBeInTheDocument();
    });
    return view;
};

describe("EventDiscovery", () => {
    it("renders page header", async () => {
        await renderEventDiscovery();

        expect(screen.getByText("Browse Events")).toBeInTheDocument();
        expect(screen.getByText(/discover professional development/i)).toBeInTheDocument();
    });

    it("renders search input", async () => {
        await renderEventDiscovery();

        expect(screen.getByPlaceholderText(/search events/i)).toBeInTheDocument();
    });

    it("renders filter options", async () => {
        await renderEventDiscovery();

        expect(screen.getByText("Event Type")).toBeInTheDocument();
        expect(screen.getByText("Format")).toBeInTheDocument();
        expect(screen.getByText("Registration Fee")).toBeInTheDocument();
    });

    it("has event type filter checkboxes", async () => {
        await renderEventDiscovery();

        // The current event-type filter ships only Webinar + Workshop.
        // Add new entries here when the EventDiscovery filter list grows.
        expect(screen.getByLabelText("Webinar")).toBeInTheDocument();
        expect(screen.getByLabelText("Workshop")).toBeInTheDocument();
    });

    it("has format filter checkboxes", async () => {
        await renderEventDiscovery();

        expect(screen.getByLabelText("Online")).toBeInTheDocument();
        expect(screen.getByLabelText("In-Person")).toBeInTheDocument();
        expect(screen.getByLabelText("Hybrid")).toBeInTheDocument();
    });

    it("has sort dropdown", async () => {
        await renderEventDiscovery();

        expect(screen.getByText("Upcoming")).toBeInTheDocument();
    });

    it("renders reset filters button", async () => {
        await renderEventDiscovery();

        expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
    });

    it("shows empty state when no events loaded", async () => {
        await renderEventDiscovery();

        expect(screen.getByText(/no events found/i)).toBeInTheDocument();
    });
});
