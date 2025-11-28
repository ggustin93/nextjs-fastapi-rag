'use client';

import { useState, useEffect } from 'react';

/**
 * Custom hook to detect media query matches
 * Safely handles SSR by starting with false
 *
 * @param query - Media query string (e.g., '(min-width: 768px)')
 * @returns boolean indicating if media query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    // Initialize with media query check (SSR-safe with fallback)
    if (typeof window !== 'undefined') {
      return window.matchMedia(query).matches;
    }
    return false;
  });

  useEffect(() => {
    // Create media query list
    const mediaQuery = window.matchMedia(query);

    // Handler for changes
    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Add listener
    mediaQuery.addEventListener('change', handler);

    // Cleanup
    return () => {
      mediaQuery.removeEventListener('change', handler);
    };
  }, [query]);

  return matches;
}
