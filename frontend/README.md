# CPD Events Platform - Frontend

React-based frontend application for the CPD Events platform, providing interfaces for event management, registration, certificate generation, and learning management.

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── assets/         # Images, icons, fonts
│   ├── components/     # Reusable UI components
│   │   ├── common/    # Shared components (buttons, forms, etc.)
│   │   ├── events/    # Event-related components
│   │   ├── courses/   # Course/learning components
│   │   ├── certificates/ # Certificate components
│   │   └── ...
│   ├── pages/         # Page-level components
│   │   ├── auth/      # Login, signup, password reset
│   │   ├── events/    # Event listing, details, management
│   │   ├── courses/   # Course catalog, enrollment
│   │   ├── dashboard/ # User dashboard
│   │   └── ...
│   ├── contexts/      # React context providers
│   ├── hooks/         # Custom React hooks
│   ├── services/      # API service layer
│   ├── utils/         # Utility functions
│   ├── types/         # TypeScript type definitions
│   ├── App.tsx        # Main app component
│   └── main.tsx       # Application entry point
├── APP_ICONS_TODO.md  # Active task list for icons
├── Attributions.md    # Third-party attribution credits
└── package.json
```

## Component Architecture

### Page Components
Top-level route components that compose smaller components to create full pages.

### Feature Components
Domain-specific components organized by feature area (events, courses, certificates, etc.).

### Common Components
Reusable UI components used across the application:
- Forms and inputs
- Buttons and actions
- Layout components
- Navigation elements
- Modals and dialogs

### Context Providers
- `AuthContext` - User authentication state
- `ThemeContext` - UI theme preferences
- Others as needed for global state

## Development Setup

### Prerequisites
- Node.js 18+ and npm
- Backend API running (see `/backend/README.md`)

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
VITE_ENVIRONMENT=development
```

## Build and Deployment

### Development Build
```bash
npm run dev
```
Runs the development server with hot module replacement.

### Production Build
```bash
npm run build
```
Creates an optimized production build in the `dist/` directory.

### Deployment
The frontend is deployed to Google Cloud Storage with Cloud CDN for global content delivery.

```bash
# Using the accredit CLI
accredit cloud frontend deploy --env dev

# Manual deployment
cd ../infra/gcp/scripts
./deploy-frontend.sh dev
```

See `/docs/deployment/` for detailed deployment instructions.

## Testing Approach

### Unit Tests
Test individual components and utility functions in isolation.

### Integration Tests
Test component interactions and data flow.

### E2E Tests
Test complete user workflows across the application.

## Key Features

### Authentication
- User login/signup
- Password reset
- Multi-factor authentication support
- Organization switching

### Event Management
- Event browsing and search
- Event registration and payment
- Attendance tracking
- Certificate generation

### Learning Management
- Course catalog
- Course enrollment
- Progress tracking
- Hybrid courses (online + in-person)

### Certificate System
- Automated certificate generation
- Certificate verification
- PDF download
- Badge integration

### User Dashboard
- Registration history
- Certificate collection
- Learning progress
- Profile management

## API Integration

The frontend communicates with the Django REST API backend. All API calls are handled through service modules in `src/services/`.

### Service Layer
- `authService.ts` - Authentication
- `eventService.ts` - Events
- `courseService.ts` - Courses
- `certificateService.ts` - Certificates
- `registrationService.ts` - Registrations

## Styling

- CSS Modules for component-scoped styles
- Tailwind CSS for utility classes
- Custom theme variables for brand consistency

## State Management

- React Context for global state
- React hooks for local component state
- Custom hooks for shared logic

## Documentation

### Related Documentation
- [User Workflows](../docs/workflows/frontend-user-flows.md) - Complete user flow documentation
- [Workflow Gap Analysis](../docs/gaps/frontend-workflow-gaps.md) - Known gaps and improvements
- [Implementation Audit](../docs/history/frontend-audit-2026-01.md) - Recent audit findings
- [UI/UX Improvements](../docs/history/ui-ux-improvements-2026-01.md) - UI enhancement history

### Tasks
- [APP_ICONS_TODO.md](./APP_ICONS_TODO.md) - Outstanding icon/asset tasks

### Attributions
- [Attributions.md](./Attributions.md) - Third-party credits and licenses

## Contributing

When adding new features:
1. Follow the existing component structure
2. Add TypeScript types for new data structures
3. Create reusable components when appropriate
4. Update relevant documentation
5. Test across different screen sizes

## Technology Stack

- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS + CSS Modules
- **Routing**: React Router
- **HTTP Client**: Axios
- **Form Handling**: React Hook Form
- **State Management**: React Context + Hooks

See [TECHNOLOGY_STACK.md](../TECHNOLOGY_STACK.md) for complete technology overview.
