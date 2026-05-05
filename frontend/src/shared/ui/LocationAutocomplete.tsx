import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Input } from '@/shared/ui/input';
import { MapPin, Loader2 } from 'lucide-react';

/* global google */

interface LocationAutocompleteProps {
    value: string;
    onChange: (value: string, placeDetails?: google.maps.places.PlaceResult) => void;
    placeholder?: string;
    disabled?: boolean;
    className?: string;
}

// Declare google as a global variable
declare global {
    interface Window {
        google: typeof google;
        initGoogleMapsCallback?: () => void;
        // Google calls this exact symbol on any Maps-JS auth failure
        // (InvalidKey, ExpiredKey, RefererNotAllowed, etc.). The component
        // listens to it via the `mapsAuthFailureListeners` set below.
        gm_authFailure?: () => void;
    }
}

let isScriptLoaded = false;
let isScriptLoading = false;
const callbacks: (() => void)[] = [];

// Each mounted LocationAutocomplete subscribes to auth-failure events
// here. Using a module-level set means a single global gm_authFailure
// hook fans out to every instance, which matches how Google's loader
// only respects the first registration of that symbol.
const mapsAuthFailureListeners = new Set<() => void>();
let gm_authFailureInstalled = false;
function installGmAuthFailureHook() {
    if (gm_authFailureInstalled) return;
    gm_authFailureInstalled = true;
    window.gm_authFailure = () => {
        for (const cb of mapsAuthFailureListeners) cb();
    };
}

function loadGoogleMapsScript(apiKey: string): Promise<void> {
    return new Promise((resolve, reject) => {
        // The auth-failure hook must be in place BEFORE the loader runs
        // — Google snapshots `window.gm_authFailure` at load time and
        // late registrations are ignored.
        installGmAuthFailureHook();

        if (isScriptLoaded) {
            resolve();
            return;
        }

        if (isScriptLoading) {
            callbacks.push(() => resolve());
            return;
        }

        isScriptLoading = true;

        window.initGoogleMapsCallback = () => {
            isScriptLoaded = true;
            isScriptLoading = false;
            resolve();
            callbacks.forEach(cb => cb());
            callbacks.length = 0;
        };

        const script = document.createElement('script');
        // `loading=async` is Google's recommended pattern for the JS API
        // loader (silences the perf warning and improves first-paint).
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&loading=async&callback=initGoogleMapsCallback`;
        script.async = true;
        script.defer = true;
        script.onerror = () => {
            isScriptLoading = false;
            reject(new Error('Failed to load Google Maps script'));
        };
        document.head.appendChild(script);
    });
}

export function LocationAutocomplete({
    value,
    onChange,
    placeholder = "Search for a location...",
    disabled = false,
    className = "",
}: LocationAutocompleteProps) {
    const inputRef = useRef<HTMLInputElement>(null);
    const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [authFailed, setAuthFailed] = useState(false);
    const [inputValue, setInputValue] = useState(value);

    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

    const initAutocomplete = useCallback(() => {
        if (!inputRef.current || !window.google?.maps?.places) return;

        autocompleteRef.current = new window.google.maps.places.Autocomplete(
            inputRef.current,
            {
                types: ['establishment', 'geocode'],
                fields: ['formatted_address', 'geometry', 'name', 'place_id'],
            }
        );

        autocompleteRef.current.addListener('place_changed', () => {
            const place = autocompleteRef.current?.getPlace();
            // When Maps-JS auth is broken, `getPlace()` can return a stub
            // with only the typed string and no `formatted_address` /
            // `geometry`. Treat that as a failed pick: surface the
            // free-text value to the parent and force the pac dropdown
            // closed so the UI doesn't appear stuck.
            if (!place || (!place.formatted_address && !place.geometry)) {
                const typed = inputRef.current?.value ?? '';
                setInputValue(typed);
                onChange(typed);
                document.querySelectorAll('.pac-container').forEach((el) => {
                    (el as HTMLElement).style.display = 'none';
                });
                return;
            }
            const address = place.formatted_address || place.name || '';
            setInputValue(address);
            onChange(address, place);
        });
    }, [onChange]);

    useEffect(() => {
        if (!apiKey) {
            setError('Google Maps API key not configured');
            setIsLoading(false);
            return;
        }

        const onAuthFailure = () => {
            // ExpiredKey / InvalidKey / RefererNotAllowed → the JS SDK is
            // unusable. Drop to the manual-entry fallback so the form
            // stays functional. The user can still save the address as
            // free text; the backend never required structured place
            // data.
            setAuthFailed(true);
            setIsLoading(false);
            setError('Map autocomplete is unavailable — using manual entry.');
            // Hide any pac dropdown that might have already rendered.
            document.querySelectorAll('.pac-container').forEach((el) => {
                (el as HTMLElement).style.display = 'none';
            });
        };
        mapsAuthFailureListeners.add(onAuthFailure);

        loadGoogleMapsScript(apiKey)
            .then(() => {
                setIsLoading(false);
                initAutocomplete();
            })
            .catch((err) => {
                setError(err.message);
                setIsLoading(false);
            });

        return () => {
            mapsAuthFailureListeners.delete(onAuthFailure);
        };
    }, [apiKey, initAutocomplete]);

    useEffect(() => {
        setInputValue(value);
    }, [value]);

    // Fallback to regular input when (a) no API key configured, or
    // (b) Google fired gm_authFailure (expired/invalid/restricted key).
    if (!apiKey || authFailed) {
        return (
            <div className={`relative ${className}`}>
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                    value={inputValue}
                    onChange={(e) => {
                        setInputValue(e.target.value);
                        onChange(e.target.value);
                    }}
                    placeholder={placeholder}
                    disabled={disabled}
                    className="pl-9"
                />
                {(error || authFailed) && (
                    <p className="text-xs text-muted-foreground mt-1">
                        Using manual entry (autocomplete unavailable)
                    </p>
                )}
            </div>
        );
    }

    return (
        <div className={`relative ${className}`}>
            {isLoading ? (
                <Loader2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground animate-spin" />
            ) : (
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            )}
            <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => {
                    setInputValue(e.target.value);
                    // Only update parent when user manually types (not on autocomplete select)
                    onChange(e.target.value);
                }}
                placeholder={isLoading ? "Loading..." : placeholder}
                disabled={disabled || isLoading}
                className="pl-9"
            />
            {error && (
                <p className="text-xs text-error mt-1">{error}</p>
            )}
        </div>
    );
}
