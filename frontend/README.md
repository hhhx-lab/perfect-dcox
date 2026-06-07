# Frontend

React + TypeScript + Vite workbench for the Word Format Agent foundation.

## Install and Run

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The frontend uses `VITE_API_BASE_URL` when provided. Without it, the API client points to:

```text
http://127.0.0.1:8000/api
```

## Build

```bash
npm run build
```
