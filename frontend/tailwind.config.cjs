/** @type {import('tailwindcss').Config} */
module.exports = {
	darkMode: ["class"],
	content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
	theme: {
		container: {
			center: true,
			padding: '2rem',
			screens: {
				'2xl': '1400px'
			}
		},
		extend: {
			colors: {
				border: 'hsl(var(--border))',
				input: 'hsl(var(--input))',
				ring: 'hsl(var(--ring))',
				background: 'hsl(var(--background))',
				foreground: 'hsl(var(--foreground))',
				primary: {
					DEFAULT: 'hsl(var(--primary))',
					foreground: 'hsl(var(--primary-foreground))'
				},
				secondary: {
					DEFAULT: 'hsl(var(--secondary))',
					foreground: 'hsl(var(--secondary-foreground))'
				},
				destructive: {
					DEFAULT: 'hsl(var(--destructive))',
					foreground: 'hsl(var(--destructive-foreground))'
				},
				muted: {
					DEFAULT: 'hsl(var(--muted))',
					foreground: 'hsl(var(--muted-foreground))'
				},
				accent: {
					DEFAULT: 'hsl(var(--accent))',
					foreground: 'hsl(var(--accent-foreground))'
				},
				popover: {
					DEFAULT: 'hsl(var(--popover))',
					foreground: 'hsl(var(--popover-foreground))'
				},
				card: {
					DEFAULT: 'hsl(var(--card))',
					foreground: 'hsl(var(--card-foreground))'
				},
				success: {
					DEFAULT: 'hsl(var(--success))',
					foreground: 'hsl(var(--success-foreground))'
				},
				warning: {
					DEFAULT: 'hsl(var(--warning))',
					foreground: 'hsl(var(--warning-foreground))'
				},
				/* Status colors (D4) — narrative meaning, not just generic palette.
				   Use over raw amber/slate/red so meaning stays consistent across themes. */
				'status-progress': {
					DEFAULT: 'hsl(var(--status-progress))',
					foreground: 'hsl(var(--status-progress-foreground))'
				},
				'status-locked': {
					DEFAULT: 'hsl(var(--status-locked))',
					foreground: 'hsl(var(--status-locked-foreground))'
				},
				'status-overdue': {
					DEFAULT: 'hsl(var(--status-overdue))',
					foreground: 'hsl(var(--status-overdue-foreground))'
				},
				chart: {
					'1': 'hsl(var(--chart-1))',
					'2': 'hsl(var(--chart-2))',
					'3': 'hsl(var(--chart-3))',
					'4': 'hsl(var(--chart-4))',
					'5': 'hsl(var(--chart-5))'
				}
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)',
				xl: 'calc(var(--radius) + 4px)',
				'2xl': 'calc(var(--radius) + 8px)',
				'3xl': 'calc(var(--radius) + 16px)'
			},
			fontFamily: {
				sans: [
					'Inter',
					'system-ui',
					'sans-serif'
				],
				outfit: [
					'Outfit',
					'sans-serif'
				]
			},
			fontSize: {
				'2xs': ['0.625rem', { lineHeight: '0.875rem' }],
				/* Semantic type scale (D1 — visual design plan).
				   Use these in preference to ad-hoc text-sm / text-3xl. */
				'caption': ['0.75rem', { lineHeight: '1.125rem', letterSpacing: '0.01em' }],
				'body': ['0.875rem', { lineHeight: '1.375rem' }],
				'body-lg': ['1rem', { lineHeight: '1.5rem' }],
				'h3': ['1.125rem', { lineHeight: '1.625rem', fontWeight: '600', letterSpacing: '-0.005em' }],
				'h2': ['1.375rem', { lineHeight: '1.875rem', fontWeight: '600', letterSpacing: '-0.01em' }],
				'h1': ['1.75rem', { lineHeight: '2.25rem', fontWeight: '600', letterSpacing: '-0.015em' }],
				'display-lg': ['2rem', { lineHeight: '2.5rem', fontWeight: '600', letterSpacing: '-0.02em' }],
				'display-xl': ['2.5rem', { lineHeight: '3rem', fontWeight: '700', letterSpacing: '-0.025em' }],
			},
			spacing: {
				/* Semantic spacing (D2). Use over raw 4/6/8/12 for layout-level gaps. */
				'tight': '0.75rem',   /* 12px — between tightly-grouped elements */
				'card': '1.5rem',     /* 24px — internal card padding / inter-card gaps */
				'block': '2rem',      /* 32px — between content blocks within a section */
				'section': '3rem',    /* 48px — between top-level page sections */
			},
			boxShadow: {
				soft: '0 2px 8px -2px hsl(var(--shadow-color) / 0.08), 0 4px 16px -4px hsl(var(--shadow-color) / 0.06)',
				elevated: '0 4px 12px -2px hsl(var(--shadow-color) / 0.1), 0 8px 24px -4px hsl(var(--shadow-color) / 0.08), 0 12px 48px -8px hsl(var(--shadow-color) / 0.06)',
				/* Card elevation tiers (D3). Apply via Card `elevation` prop or directly. */
				'rest': '0 1px 2px 0 hsl(var(--shadow-color) / 0.04), 0 1px 3px -1px hsl(var(--shadow-color) / 0.04)',
				'hover': '0 4px 8px -2px hsl(var(--shadow-color) / 0.06), 0 8px 16px -4px hsl(var(--shadow-color) / 0.05)',
				'lifted': '0 8px 16px -4px hsl(var(--shadow-color) / 0.08), 0 16px 32px -8px hsl(var(--shadow-color) / 0.06), 0 24px 48px -12px hsl(var(--shadow-color) / 0.04)',
			},
			keyframes: {
				'accordion-down': {
					from: {
						height: 0
					},
					to: {
						height: 'var(--radix-accordion-content-height)'
					}
				},
				'accordion-up': {
					from: {
						height: 'var(--radix-accordion-content-height)'
					},
					to: {
						height: 0
					}
				},
				'fade-in-up': {
					from: {
						opacity: 0,
						transform: 'translateY(16px)'
					},
					to: {
						opacity: 1,
						transform: 'translateY(0)'
					}
				},
				'fade-in-down': {
					from: {
						opacity: 0,
						transform: 'translateY(-16px)'
					},
					to: {
						opacity: 1,
						transform: 'translateY(0)'
					}
				},
				'float': {
					'0%, 100%': {
						transform: 'translateY(0)'
					},
					'50%': {
						transform: 'translateY(-8px)'
					}
				}
			},
			animation: {
				'accordion-down': 'accordion-down 0.2s ease-out',
				'accordion-up': 'accordion-up 0.2s ease-out',
				'fade-in-up': 'fade-in-up 0.5s ease-out forwards',
				'fade-in-down': 'fade-in-down 0.5s ease-out forwards',
				'float': 'float 4s ease-in-out infinite'
			}
		}
	},
	plugins: [require("tailwindcss-animate")],
};
