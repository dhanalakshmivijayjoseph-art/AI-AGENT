# HETA AI
Your Intelligence. Your Assistant. Your HETA AI.

A ChatGPT-style chatbot: HTML/CSS/JS frontend, Flask backend, SQLite database, Gemini API.

## Setup
1. `cd HETA-AI/backend`
2. `python -m venv venv` then activate it
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. `pip install -r requirements.txt`
4. Open `.env` (project root) and set `GEMINI_API_KEY=your Google AI Studio key`
   - The default model is `gemini-3.5-flash-lite` (`AI_MODEL` in `.env`)
5. `python app.py`
6. Open http://127.0.0.1:5000

The database file `heta.db` is created automatically on first run.

## Deploy to Vercel
1. Connect the GitHub repository and deploy the `gemini-api-fix` branch (or merge it into the production branch).
2. Set the Vercel project root directory to the repository root.
3. Add `GEMINI_API_KEY` in the Vercel project's Environment Variables for Preview and Production, then redeploy.

Vercel serves the frontend from `public/` and runs the Flask app through the root `app.py` entrypoint. The SQLite database uses Vercel's temporary `/tmp` storage, so chat history can reset when a function instance is replaced. Use a managed database for persistent chat history.
