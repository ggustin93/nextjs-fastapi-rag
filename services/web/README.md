# Docling RAG Agent - Frontend

A modern Next.js chat interface for the Docling RAG Agent, built with TypeScript, Tailwind CSS, and shadcn/ui components.

## Features

- 🎨 **Modern UI**: Clean, responsive design using shadcn/ui components
- 🔄 **Real-time Streaming**: SSE (Server-Sent Events) for token-by-token responses
- ⚡ **Fast**: Next.js 15 with Turbopack for optimal performance
- 🎯 **Type-Safe**: Full TypeScript support with proper types
- 📱 **Responsive**: Works seamlessly on desktop and mobile devices
- ♿ **Accessible**: WCAG-compliant components from shadcn/ui

## Prerequisites

- Node.js 18.x or higher
- npm or yarn
- Backend API running on `http://localhost:8000` (see `../backend/README.md`)

## Installation

The project was initialized using official Next.js and shadcn/ui CLIs:

```bash
# Next.js initialization
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --turbopack --import-alias "@/*"

# shadcn/ui initialization
npx shadcn@latest init

# Components installation
npx shadcn@latest add card button input scroll-area avatar
```

To install dependencies:

```bash
npm install
```

## Configuration

Create a `.env.local` file in the frontend directory:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## Project Structure

```
frontend/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── page.tsx             # Main chat page
│   │   └── globals.css          # Global styles with Tailwind
│   ├── components/
│   │   ├── chat/                # Chat-specific components
│   │   │   ├── ChatContainer.tsx  # Main chat layout
│   │   │   ├── ChatMessage.tsx    # Individual message bubble
│   │   │   └── ChatInput.tsx      # Input field with send button
│   │   └── ui/                  # shadcn/ui components
│   │       ├── card.tsx
│   │       ├── button.tsx
│   │       ├── input.tsx
│   │       ├── scroll-area.tsx
│   │       └── avatar.tsx
│   ├── hooks/
│   │   └── useChat.ts           # Chat state management hook
│   ├── lib/
│   │   ├── api-client.ts        # SSE streaming API client
│   │   └── utils.ts             # Utility functions (cn helper)
│   └── types/
│       └── chat.ts              # TypeScript interfaces
├── components.json              # shadcn/ui configuration
├── tailwind.config.ts           # Tailwind CSS config
├── tsconfig.json                # TypeScript config
└── package.json                 # Dependencies
```

## Components

### ChatContainer
Main container component that orchestrates the chat interface.

**Features:**
- Message list with auto-scroll
- Loading states
- Error handling
- Clear chat button

### ChatMessage
Individual message bubble component.

**Features:**
- User/assistant role differentiation
- Avatar icons
- Responsive layout
- Word wrapping for long messages

### ChatInput
Input field with send button.

**Features:**
- Enter key to send
- Disabled state during loading
- Send button with icon
- Placeholder text

### useChat Hook
Custom React hook for managing chat state.

**Features:**
- Message state management
- SSE streaming handling
- Error handling
- Loading states
- Clear messages function

## API Integration

The frontend communicates with the backend using Server-Sent Events (SSE) for real-time streaming:

**Endpoint:** `POST /api/v1/chat/stream`

**Request:**
```typescript
{
  message: string;
  session_id?: string;  // Optional, for future session support
}
```

**Response:** SSE stream with events:
```
event: token
data: {"content": "Hello"}

event: token
data: {"content": " world"}

event: done
data: {"content": ""}
```

## Styling

The project uses:
- **Tailwind CSS v4**: Utility-first CSS framework
- **shadcn/ui**: Pre-built, accessible components
- **CSS Variables**: For theming and customization
- **Dark Mode**: Full dark mode support

## Building for Production

```bash
npm run build
npm start
```

The production build will be optimized and ready for deployment.

## Troubleshooting

### Backend Connection Issues

If you see connection errors:

1. Ensure the backend is running: `cd ../backend && uvicorn app.main:app --reload`
2. Check the API URL in `.env.local`
3. Verify CORS is configured correctly in the backend

### Styling Issues

If components don't look right:

1. Ensure Tailwind is properly configured
2. Check that `globals.css` is imported in `layout.tsx`
3. Verify shadcn/ui components are installed correctly

### TypeScript Errors

Run type checking:

```bash
npm run lint
npx tsc --noEmit
```

## Future Enhancements

- Session history persistence
- Source citations display
- Document upload interface
- User authentication
- Multi-session management
- Export chat history

## License

Part of the Docling RAG Agent project.
