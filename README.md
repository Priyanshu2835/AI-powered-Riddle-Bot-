# AI-powered-Riddle-Bot-
# Riddle Bot 🤖

A Flask-based interactive riddle game with AI integration using OpenRouter API.

![Riddle Bot Screenshot](screenshot.png) <!-- Add a screenshot later -->

## Features
- AI-generated riddles with varying difficulty levels
- Smart answer verification with multiple methods
- Scoring system with time bonuses and hint penalties
- Session management for multiple players
- Responsive and animated UI

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/riddle-bot.git
   cd riddle-bot
   ```

2. **Set up virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   - Create a `.env` file
   - Add your OpenRouter API key:
     ```
     OPENROUTER_API_KEY=your_api_key_here
     ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Open in browser**:
   Visit `http://localhost:5000`

## Configuration Options

- Change the default AI model in `app.py`:
  ```python
  model="deepseek/deepseek-chat-v3-0324:free"
  ```
- Adjust scoring parameters in the `check_answer` route

## Deployment

### Heroku
1. Create a `Procfile` with:
   ```
   web: python app.py
   ```
2. Push to Heroku

### Docker
1. Create a `Dockerfile`:
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY . .
   RUN pip install -r requirements.txt
   CMD ["python", "app.py"]
   ```

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## License
[MIT](https://choosealicense.com/licenses/mit/)
