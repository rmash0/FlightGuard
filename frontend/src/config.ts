// App name lives here so the eventual rename is a one-line change (plus index.html <title>).
export const APP_NAME = "FlightGuard";

// Demo mode: serve recorded sample data (src/mocks/demo/) instead of calling the backend.
// On for the hosted demo (`npm run build:demo`) or when VITE_USE_MOCKS=true.
export const USE_SAMPLE_DATA = import.meta.env.VITE_USE_MOCKS === "true";
