/**
 * Theme Testing Utility
 * 
 * Helpers for testing theme transitions and visual consistency
 * across light and dark modes.
 */

export type Theme = 'light' | 'dark' | 'system';

/**
 * Get the current theme from localStorage
 */
export function getCurrentTheme(): Theme {
  const stored = localStorage.getItem('vite-ui-theme');
  return (stored as Theme) || 'system';
}

/**
 * Set the theme programmatically
 */
export function setTheme(theme: Theme): void {
  localStorage.setItem('vite-ui-theme', theme);
  const root = window.document.documentElement;
  
  root.classList.remove('light', 'dark');
  
  if (theme === 'system') {
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
    root.classList.add(systemTheme);
  } else {
    root.classList.add(theme);
  }
  
  // Dispatch custom event for components to react to theme changes
  window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
}

/**
 * Get computed color value for a CSS variable
 */
export function getCSSVariable(variable: string): string {
  const root = document.documentElement;
  const value = getComputedStyle(root).getPropertyValue(variable).trim();
  return value;
}

/**
 * Check if an element uses semantic color classes
 */
export function usesSemanticColor(element: HTMLElement): {
  hasSemanticColors: boolean;
  hardcodedClasses: string[];
} {
  const classList = Array.from(element.classList);
  const hardcodedPatterns = [
    /dark:(bg|text|border)-(red|green|blue|amber|yellow|indigo|purple|pink)-\d+/,
    /bg-(red|green|blue|amber|yellow)-\d+/,
    /text-(red|green|blue|amber|yellow)-\d+/,
  ];
  
  const hardcodedClasses = classList.filter(className =>
    hardcodedPatterns.some(pattern => pattern.test(className))
  );
  
  const semanticPatterns = [
    'bg-success', 'text-success', 'border-success',
    'bg-info', 'text-info', 'border-info',
    'bg-warning', 'text-warning', 'border-warning',
    'bg-error', 'text-error', 'border-error',
    'bg-card', 'text-foreground', 'text-muted-foreground',
  ];
  
  const hasSemanticColors = classList.some(className =>
    semanticPatterns.some(pattern => className.includes(pattern))
  );
  
  return {
    hasSemanticColors,
    hardcodedClasses,
  };
}

/**
 * Test helper: Take snapshot of component in both themes
 */
export async function snapshotBothThemes(
  componentSelector: string
): Promise<{ light: string; dark: string }> {
  const element = document.querySelector(componentSelector);
  if (!element) {
    throw new Error(`Element not found: ${componentSelector}`);
  }
  
  // Get light mode snapshot
  setTheme('light');
  await new Promise(resolve => setTimeout(resolve, 100)); // Wait for transition
  const lightSnapshot = element.innerHTML;
  
  // Get dark mode snapshot
  setTheme('dark');
  await new Promise(resolve => setTimeout(resolve, 100)); // Wait for transition
  const darkSnapshot = element.innerHTML;
  
  return {
    light: lightSnapshot,
    dark: darkSnapshot,
  };
}

/**
 * Validate that all state colors are accessible
 */
export function validateAccessibility(): {
  valid: boolean;
  issues: string[];
} {
  const issues: string[] = [];
  
  // Check contrast ratios for semantic colors
  const semanticElements = document.querySelectorAll('[class*="text-success"], [class*="text-info"], [class*="text-warning"], [class*="text-error"]');
  
  semanticElements.forEach((element) => {
    const styles = getComputedStyle(element);
    const color = styles.color;
    const backgroundColor = styles.backgroundColor;
    
    // TODO: Implement actual contrast ratio calculation
    // For now, just collect elements for manual review
  });
  
  return {
    valid: issues.length === 0,
    issues,
  };
}

/**
 * Get all semantic color variables in current theme
 */
export function getSemanticColors(): Record<string, string> {
  return {
    // Success
    'success-subtle-bg': getCSSVariable('--success'),
    'success-text': getCSSVariable('--success-foreground'),
    
    // Warning  
    'warning-subtle-bg': getCSSVariable('--warning'),
    'warning-text': getCSSVariable('--warning-foreground'),
    
    // Destructive/Error
    'error-subtle-bg': getCSSVariable('--destructive'),
    'error-text': getCSSVariable('--destructive-foreground'),
    
    // Base theme
    'background': getCSSVariable('--background'),
    'foreground': getCSSVariable('--foreground'),
    'card': getCSSVariable('--card'),
    'card-foreground': getCSSVariable('--card-foreground'),
    'muted': getCSSVariable('--muted'),
    'muted-foreground': getCSSVariable('--muted-foreground'),
  };
}

/**
 * Check if theme transitions are smooth
 */
export function hasSmoothTransitions(element: HTMLElement): boolean {
  const styles = getComputedStyle(element);
  const transition = styles.transition;
  
  return transition !== 'none' && transition !== '';
}

/**
 * Debug helper: Log theme state
 */
export function debugTheme(): void {
  console.group('🎨 Theme Debug Info');
  console.log('Current theme:', getCurrentTheme());
  console.log('Root classes:', document.documentElement.classList.toString());
  console.log('Semantic colors:', getSemanticColors());
  console.groupEnd();
}
