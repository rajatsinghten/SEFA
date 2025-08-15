# RunDown - Smart Task Management System

## 📋 Overview

RunDown is an AI-powered task management system that seamlessly integrates with your **Microsoft Account (Outlook Mail and Calendar)** to automatically extract important tasks and events from your emails. The application uses AI to intelligently identify actionable items in your inbox and presents them as suggested tasks that can be easily added to your to-do list and calendar with a single click.

---

## ✨ Features

- **Smart Email Processing**: Automatically scans your Outlook inbox for potential tasks and events.
- **AI-Powered Task Extraction**: Uses AI to identify actionable items in emails.
- **Interest-Based Filtering**: Customizable preferences to only show task suggestions relevant to your interests.
- **Two-Way Calendar Sync**: Tasks are automatically synced with your Outlook Calendar.
- **Natural Language Task Entry**: Add tasks using natural language with automatic date extraction.
- **Intelligent Chatbot Assistant**: Use simple commands (`@add`, `@remove`, `@list`, `@check`, `@suggest`) to manage your schedule directly through chat.
- **Smart Duplicate Prevention**: Avoids creating duplicate tasks by tracking email IDs and comparing event details.
- **Secure Authentication**: OAuth 2.0 integration with Microsoft for secure access to your data.

---

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Authentication**: Microsoft OAuth (via Microsoft Identity Platform)
- **Data Storage**: File-based storage (JSON)
- **AI Integration**: Azure OpenAI Service or another LLM provider
- **Microsoft API Integration**: Outlook Mail API, Outlook Calendar API (via Microsoft Graph API)

---

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- A Microsoft Azure AD app registration with Mail.Read, Mail.ReadWrite, Calendars.Read, and Calendars.ReadWrite permissions
- Microsoft OAuth credentials (`client_id`, `client_secret`, `tenant_id`)
- AI API key (Azure OpenAI or similar)

### Setup

1. **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/rundown.git
    cd rundown
    ```

2. **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up configuration files**:
    - Create a `.env` file and add:
      ```
      CLIENT_ID=your_microsoft_app_client_id
      CLIENT_SECRET=your_microsoft_app_client_secret
      TENANT_ID=your_microsoft_tenant_id
      AI_API_KEY=your_ai_service_api_key
      ```

5. **Create required directories**:
    ```bash
    mkdir -p tokens
    ```

6. **Run the application**:
    ```bash
    python app.py
    ```

7. **Access the application**:
    Open your browser and navigate to `http://127.0.0.1:5000`.

---

## ⚙️ Configuration

### Microsoft Azure App Registration Setup

1. Go to the [Azure Portal](https://portal.azure.com/).
2. Navigate to **Azure Active Directory** → **App registrations**.
3. Click **New registration**, give it a name, and set the redirect URI to:
    ```
    http://localhost:5000/oauth/callback
    ```
4. **API Permissions** → Add the following Microsoft Graph delegated permissions:
    - `Mail.Read`
    - `Mail.ReadWrite`
    - `Calendars.Read`
    - `Calendars.ReadWrite`
5. Click **Grant admin consent** for the permissions.
6. Go to **Certificates & secrets**, create a new client secret, and save it along with the **Application (client) ID** and **Directory (tenant) ID**.

---

## 🧩 Project Structure

RunDown/
├── app.py # Main application file
├── config.py # Configuration settings
├── requirements.txt # Python dependencies
├── .env # Environment variables
├── static/
│ ├── css/
│ └── js/
├── templates/
│ ├── chat.html
│ ├── login.html
│ └── preferences.html
├── routes/
│ ├── auth_routes.py
│ ├── calendar_routes.py
│ ├── chat_routes.py
│ └── outlook_routes.py
└── utils/
├── auth.py
├── calendar.py
├── outlook.py
└── models.py


---

## 📱 Usage Guide

1. **Authentication**: Visit the app and click "Continue with Microsoft" to grant the required permissions.
2. **Set Preferences**: On your first login, select interests (e.g., Internships, Hackathons) to filter email suggestions.
3. **View Suggestions**: The "Tasks" button shows AI-generated task suggestions from your emails.
4. **Manage Tasks**: Add suggestions to your list, create tasks manually, set deadlines, and track their status. Tasks are automatically synced to your Outlook Calendar.
5. **Use AI Assistant**: The "Chats" button opens the AI assistant. Use commands like `@add Meeting tomorrow at 3pm` to manage your schedule with natural language.

---

## 🔍 Advanced Features

### AI Chatbot Commands

- **`@add [event details]`**: Creates a new calendar event. It understands natural language dates like "tomorrow" or "next Friday."
- **`@remove [event name]`**: Deletes an event from your calendar.
- **`@list`**: Shows your upcoming calendar events in chronological order.
- **`@check [date]`**: Checks your availability on a specific date and lists booked events and free slots.
- **`@suggest [event details]`**: Suggests optimal times for scheduling events based on your existing calendar.
- **`@help`**: Provides information and usage examples for all available commands.

### Smart Duplicate Prevention

RunDown prevents duplicate tasks by tracking processed email IDs, comparing calendar event details, and matching task text.

### Email Processing

The system scans your Outlook inbox via Microsoft Graph API, analyzes content for actionable items, extracts key details (dates, times, locations), and flags processed emails to avoid re-scanning.

---

## 🔧 Troubleshooting

- **Authentication Issues**: If you encounter a 401/403 error, clear your browser cookies and verify that your app registration and redirect URI in Azure match the `.env` configuration.
- **Missing Suggestions**: Adjust your interest preferences to match the content of your recent emails.
- **Incorrect Event Times**: Manually adjust events in Outlook Calendar if the AI misinterprets dates.

---

## 📈 Future Enhancements

- Mobile application support
- Integration with other email providers
- Team collaboration features
- Deployment to a cloud platform
- Migration from file-based storage to a database

---

## 📜 License

This project is licensed under the MIT License.

---

© 2025 RunDown. All rights reserved.
