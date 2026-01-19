# Frontend Development

## Stack
- React Native with Expo (iPad + web)
- Expo Router for navigation
- TypeScript

## Port Configuration
- **Development (`npm run dev`)**: Port 3000 - used for local development and E2E tests
- **Systemd service**: Port 8081 - background service with `--host lan` for network access

## Running E2E Tests

Playwright is configured to use port 3000 (matching `npm run dev`):
```bash
cd frontend
npx playwright test              # Runs all E2E tests
npx playwright test --headed     # Watch tests run in browser
```

Config: `frontend/playwright.config.ts`
- Automatically starts `npm run dev` if no server is running
- Requires `APP_PIN` environment variable (from `../.env`)

## Systemd Service

A user systemd service runs the Expo server for persistent network access:
```bash
systemctl --user status expo-frontend    # Check status
systemctl --user restart expo-frontend   # Restart
journalctl --user -u expo-frontend -f    # View logs
```

Config location: `~/.config/systemd/user/expo-frontend.service`

Note: The systemd service (port 8081) is separate from the dev server (port 3000). E2E tests use the dev server.
