import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { LandingPage } from "../LandingPage";

const renderLandingPage = () => {
    return render(
        <BrowserRouter>
            <LandingPage />
        </BrowserRouter>
    );
};

describe("LandingPage", () => {
    it("renders hero section with main headline", () => {
        renderLandingPage();

        // Hero contains "Host Events." and multiple instances of "Issue Certificates"
        expect(screen.getByText(/host events/i)).toBeInTheDocument();
        // Use getAllBy since there are multiple matches
        const certificatesText = screen.getAllByText(/issue certificates/i);
        expect(certificatesText.length).toBeGreaterThan(0);
    });

    it("has Start for Free CTA button linking to signup", () => {
        renderLandingPage();

        const ctaButton = screen.getByRole("link", { name: /start for free/i });
        expect(ctaButton).toHaveAttribute("href", "/signup?role=organizer");
    });

    it("has Contact Us button linking to contact", () => {
        renderLandingPage();

        const contactButton = screen.getByRole("link", { name: /contact us/i });
        expect(contactButton).toHaveAttribute("href", "/contact");
    });

    it("renders How It Works section", () => {
        renderLandingPage();

        expect(screen.getByText("How It Works")).toBeInTheDocument();
        expect(screen.getByText("Create Your Event")).toBeInTheDocument();
    });

    it("renders Core Features section", () => {
        renderLandingPage();

        expect(screen.getByText("Zoom Integration")).toBeInTheDocument();
        expect(screen.getByText("Automated Certificates")).toBeInTheDocument();
        expect(screen.getByText("Attendance Tracking")).toBeInTheDocument();
    });

    it("renders Use Cases section", () => {
        renderLandingPage();

        expect(screen.getByText("Professional Associations")).toBeInTheDocument();
        expect(screen.getByText("Training Providers")).toBeInTheDocument();
    });

    it("renders CTA section at the bottom", () => {
        renderLandingPage();

        expect(screen.getByText(/ready to streamline/i)).toBeInTheDocument();
    });
});
