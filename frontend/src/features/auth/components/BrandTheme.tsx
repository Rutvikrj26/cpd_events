import { useEffect } from 'react';
import { useDeployment } from '../hooks/useDeployment';
import { useManifest } from '../hooks/useManifest';
import { useAuthStore } from '../store/authStore';

/** Convert "#rrggbb" / "#rgb" → "H S% L%" string used by hsl(var(--x)). */
function hexToHslTriplet(hex: string): string | null {
    const cleaned = hex.trim().replace(/^#/, '');
    const full =
        cleaned.length === 3
            ? cleaned
                  .split('')
                  .map((c) => c + c)
                  .join('')
            : cleaned.length === 6
              ? cleaned
              : null;
    if (!full || !/^[0-9a-f]{6}$/i.test(full)) return null;
    const r = parseInt(full.slice(0, 2), 16) / 255;
    const g = parseInt(full.slice(2, 4), 16) / 255;
    const b = parseInt(full.slice(4, 6), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    let h = 0;
    let s = 0;
    if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
            case r:
                h = (g - b) / d + (g < b ? 6 : 0);
                break;
            case g:
                h = (b - r) / d + 2;
                break;
            case b:
                h = (r - g) / d + 4;
                break;
        }
        h *= 60;
    }
    return `${Math.round(h)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

/**
 * BrandTheme — reads deployment config from the auth feature and applies
 * institution-level branding (primary color, favicon, document title) as
 * side effects on the document.
 *
 * Mount once in the app shell. Replaces the brand-color block that used
 * to live inside AuthContext.
 */
export function BrandTheme() {
    const accessToken = useAuthStore((s) => s.accessToken);
    const deploymentQuery = useDeployment({ enabled: !accessToken });
    const manifestQuery = useManifest();
    const deployment = manifestQuery.data?.deployment ?? deploymentQuery.data ?? null;

    const primaryColor = deployment?.institution_primary_color;
    const faviconUrl = deployment?.institution_favicon_url;
    const institutionName = deployment?.institution_name;

    useEffect(() => {
        if (!primaryColor) return;
        const hsl = hexToHslTriplet(primaryColor);
        if (hsl) {
            document.documentElement.style.setProperty('--primary', hsl);
            const [, , l] = hsl.match(/(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%/) || [];
            const lightness = parseFloat(l || '0');
            document.documentElement.style.setProperty(
                '--primary-foreground',
                lightness > 55 ? '220 13% 18%' : '0 0% 100%',
            );
        }
        document.documentElement.style.setProperty('--brand-primary', primaryColor);
    }, [primaryColor]);

    useEffect(() => {
        if (!faviconUrl) return;
        let link = document.querySelector<HTMLLinkElement>("link[rel='icon']");
        if (!link) {
            link = document.createElement('link');
            link.rel = 'icon';
            document.head.appendChild(link);
        }
        link.href = faviconUrl;
    }, [faviconUrl]);

    useEffect(() => {
        if (!institutionName) return;
        if (!document.title.startsWith(institutionName)) {
            document.title = institutionName;
        }
    }, [institutionName]);

    return null;
}
