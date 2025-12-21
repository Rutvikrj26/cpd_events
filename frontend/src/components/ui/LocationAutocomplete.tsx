import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { MapPin, Loader2 } from 'lucide-react';

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
    }
}

let isScriptLoaded = false;
let isScriptLoading = false;
const callbacks: (() => void)[] = [];

function loadGoogleMapsScript(apiKey: string): Promise<void> {
    return new Promise((resolve, reject) => {
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
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=initGoogleMapsCallback`;
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
            if (place) {
                const address = place.formatted_address || place.name || '';
                setInputValue(address);
                onChange(address, place);
            }
        });
    }, [onChange]);

    useEffect(() => {
        if (!apiKey) {
            setError('Google Maps API key not configured');
            setIsLoading(false);
            return;
        }

        loadGoogleMapsScript(apiKey)
            .then(() => {
                setIsLoading(false);
                initAutocomplete();
            })
            .catch((err) => {
                setError(err.message);
                setIsLoading(false);
            });
    }, [apiKey, initAutocomplete]);

    useEffect(() => {
        setInputValue(value);
    }, [value]);

    // Fallback to regular input if no API key
    if (!apiKey) {
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
                {error && (
                    <p className="text-xs text-amber-600 mt-1">
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
                <p className="text-xs text-red-500 mt-1">{error}</p>
            )}
        </div>
    );
}
