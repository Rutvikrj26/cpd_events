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

        expect(screen.getByText(/professional development/i)).toBeInTheDocument();
        expect(screen.getByText(/for learners/i)).toBeInTheDocument();
        expect(screen.getByText(/for providers/i)).toBeInTheDocument();
    });

    it("has Browse Training CTA button for learners", () => {
        renderLandingPage();

        const browseLinks = screen.getAllByRole("link", { name: /browse training/i });
        expect(browseLinks.length).toBeGreaterThan(0);
        expect(browseLinks[0]).toHaveAttribute("href", "/events/browse");
    });

    it("has Start Creating CTA button for providers", () => {
        renderLandingPage();

        const startLinks = screen.getAllByRole("link", { name: /start creating/i });
        expect(startLinks.length).toBeGreaterThan(0);
        expect(startLinks[0]).toHaveAttribute("href", "/pricing");
    });

    it("renders Why Learners Choose Accredit section", () => {
        renderLandingPage();

        expect(screen.getByText("Why learners choose Accredit")).toBeInTheDocument();
        expect(screen.getByText("CPD Wallet")).toBeInTheDocument();
        expect(screen.getByText("Verified Credentials")).toBeInTheDocument();
    });

    it("renders Why Providers Choose Accredit section", () => {
        renderLandingPage();

        expect(screen.getByText("Why providers choose Accredit")).toBeInTheDocument();
        expect(screen.getByText("Enterprise Reliability")).toBeInTheDocument();
        expect(screen.getByText("Automated Workflows")).toBeInTheDocument();
    });

    it("renders CTA section at the bottom", () => {
        renderLandingPage();

        expect(screen.getByText(/ready to get started/i)).toBeInTheDocument();
    });
});
