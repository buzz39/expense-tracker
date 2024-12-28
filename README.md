# Expense Analytics Dashboard

A Streamlit dashboard that connects to Notion database to visualize and analyze expenses.

## Setup
1. Create a Notion integration and get the API token
2. Share your Notion database with the integration
3. Create `.streamlit/secrets.toml` with:
   ```toml
   NOTION_TOKEN = "your-notion-token"
   NOTION_DATABASE_ID = "your-database-id"
   ```

## Running Locally

bash
streamlit run streamlit_expenses.py

4. Deploy to Streamlit Cloud:
   1. Push your code to GitHub
   2. Go to [share.streamlit.io](https://share.streamlit.io)
   3. Sign in with GitHub
   4. Click "New app"
   5. Select your repository
   6. Add your secrets in the Streamlit Cloud dashboard:
      - Go to App settings > Secrets
      - Add your Notion token and database ID

The deployment steps would be:

bash
Initialize git repository
git init
Add files
git add streamlit_expenses.py requirements.txt README.md .gitignore
Commit
git commit -m "Initial commit"
Create a new repository on GitHub and push
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main

Important notes:
1. Make sure your `.streamlit/secrets.toml` is in `.gitignore` and not committed
2. The Notion token and database ID should be added as secrets in Streamlit Cloud
3. The app will be available at `https://<your-app-name>.streamlit.app`

Would you like me to provide more details about any of these steps?


