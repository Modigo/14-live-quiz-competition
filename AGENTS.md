# Repository Guidelines

## Project Structure & Module Organization

`frontend/` contains the Vite/React client; `backend/app/` contains the FastAPI application, SQLAlchemy models, and database setup. `README.md` provides local run instructions, `PLAN.md` tracks product scope and milestones, and `DESIGN.md` defines the visual direction. Keep client and API code separate, and colocate future tests with their service or under a dedicated `tests/` directory.

## Build, Test, and Development Commands

Run the API from `backend/` with `python -m uvicorn app.main:app --reload`. Run the client from `frontend/` with `npm install` followed by `npm run dev`. Configure `VITE_API_URL` when the API is not at `http://localhost:8000`. Build the client with `npm run build`. Add test commands when test tooling is introduced; see `README.md` for setup details.

## Coding Style & Naming Conventions

Follow the formatter and lint rules selected for each language when those tools are introduced. Keep modules focused around quiz creation, live sessions, scoring, and administration. Use descriptive names that reflect the domain (for example, `participant_session` or `QuestionTimer`) and avoid embedding secrets or environment-specific values in source. Keep product and interface decisions aligned with `PLAN.md` and `DESIGN.md`; update those documents when scope or behavior changes.

## Testing Guidelines

No test framework or coverage threshold is configured. Add tests with new behavior, especially for server-authoritative timers and scoring, participant reconnects, access control, and invalid or late submissions. Name tests after the behavior they verify and document the commands to run them in `README.md`. Cover the primary host-to-results flow and meaningful failure cases.

## Commit & Pull Request Guidelines

The existing history uses short, lowercase imperative summaries (for example, `add plan and design markdown`). Keep commits focused and use the same style. Pull requests should explain the user-visible or architectural change, link relevant issues when available, list validation performed, and include screenshots or a short recording for UI changes. Call out configuration or migration requirements.

## Security & Configuration

Keep credentials in environment variables and out of commits, logs, and participant-facing responses. Treat host-control and participant reconnect links as secrets. Validate inputs and enforce authorization on the server, consistent with the security requirements in `PLAN.md`.
