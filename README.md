# Smart Microgrid

Historical renewable energy dashboard with saved model forecasts, CSV exports, and a deterministic dataset chatbot.

## Deploy on Vercel

Import `yasaswi0209/Microgrid` from GitHub and select the `main` branch.

- **Root Directory:** leave at the repository root (`./`).
- Build, install, and output settings are supplied by the root `vercel.json`.
- No environment variables, Python service, or API keys are needed for the hosted dataset edition.
- If an existing Vercel project uses `vercel-frontend` as its Root Directory, that configuration is also supported.
- Pushes to the connected production branch trigger Vercel deployments.

The hosted app uses `vercel-frontend`. Its historical data, forecasts, and 100-question assistant run in the browser. It does not ingest live sensor readings or train models in production.

## Local frontend

```sh
cd vercel-frontend
npm ci
npm run dev
```

## Python edition

`microgrid-updated` contains the full local Python project. Its server defaults to dataset-only mode, including security headers and disabled telemetry mutations. See its README for local setup; live/simulation experiments require explicitly setting `MICROGRID_DATASET_ONLY=0`.
