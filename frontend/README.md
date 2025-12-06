# Rate Limiter Frontend

React + Vite frontend for the AI Sliding Window Rate Limiter demo.

## Setup

```bash
npm install
npm run dev
```

## Testing

Run tests with Jest:

```bash
npm test
```

Watch mode:

```bash
npm run test:watch
```

Coverage report:

```bash
npm run test:coverage
```

## Test Structure

- **src/test/setup.js** — Global test setup and mocks
- **src/test/App.test.js** — Jest tests for App component

Tests cover:
- Component rendering
- Form input changes
- API integration
- Allowed/blocked responses
- Error handling
- Loading states
- Multiple sequential requests

## Build

```bash
npm run build
```
