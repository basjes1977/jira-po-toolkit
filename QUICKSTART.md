## 🚀 Quick Start Guide

Get the Jira Presentation Tool running in 3 easy steps!

### Prerequisites

- Python 3.7 or higher
- A Jira Cloud account with API access

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Jira (Choose One Method)

#### Option A: Web Setup Wizard (Recommended)

1. Start the Flask app:
   ```bash
   python webapp/app.py
   ```

2. Open your browser to: http://localhost:5000

3. You'll automatically be redirected to the setup wizard

4. Fill in your Jira details:
   - Jira URL (e.g., https://yourcompany.atlassian.net)
   - Your Atlassian email
   - API token ([create one here](https://id.atlassian.com/manage-profile/security/api-tokens))
   - Select your Jira board
   - Click "Test Connection" to verify
   - Click "Save Configuration"

5. Done! The app will reload and you're ready to go.

#### Option B: CLI Setup Wizard

```bash
python setup_wizard.py
```

Follow the interactive prompts to configure your Jira environment.

#### Option C: Manual Configuration

Create a file named `.jira_environment` with:

```bash
JT_JIRA_URL=https://yourcompany.atlassian.net
JT_JIRA_USERNAME=your.email@company.com
JT_JIRA_PASSWORD=your_api_token_here
JT_JIRA_BOARD=1234

# Optional custom field IDs (these are common defaults)
JT_JIRA_FIELD_STORY_POINTS=customfield_10024
JT_JIRA_FIELD_EPIC_LINK=customfield_10031
JT_JIRA_FIELD_ACCEPTANCE_CRITERIA=customfield_10140

# SSL verification
JT_SSL_VERIFY=true
```

### Step 3: Run the Application

#### Web UI (Recommended)

```bash
python webapp/app.py
```

Visit: http://localhost:5000

#### CLI Tools

```bash
# PowerPoint generation
python cli/powerpoint_cli.py

# Sprint forecast
python cli/forecast_cli.py

# Story overviews
python cli/overviews_cli.py
```

---

## ✨ Features

- **📊 PowerPoint Generation**: Create sprint review presentations
- **📈 Sprint Forecast**: Generate capacity forecasts with team availability
- **✅ Sanity Checks**: Validate stories for missing labels and acceptance criteria
- **🚫 Overviews**: View blocked and on-hold stories

---

## 🔒 Security Notes

- The `.jira_environment` file contains sensitive credentials
- **Never commit this file to version control** (it's in `.gitignore`)
- File permissions are automatically set to read/write for owner only
- Keep your API token secure

---

## 🆘 Troubleshooting

**Connection fails?**
- Verify your Jira URL is correct (include `https://`)
- Check your API token is valid
- Ensure your account has access to the Jira board

**Board not found?**
- Make sure you're using the **Board ID** (number), not the board name
- Check you have permission to access the board

**Custom fields not working?**
- Field IDs vary by Jira instance
- Check your Jira admin settings to find the correct custom field IDs

---

## 📝 Next Steps

Once configured, visit the web UI to:
1. Generate your first PowerPoint presentation
2. Create a sprint forecast
3. Run sanity checks on your stories
4. View blocked and on-hold items

For more details, see the full [README.md](README.md)
