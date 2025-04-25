from flask import Flask, render_template_string, jsonify, request
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
import re
import asyncio

app = Flask(__name__)

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

user_sessions = {}

def normalize_answer(answer):
    answer = answer.lower().strip()
    answer = re.sub(r'[^\w\s]', '', answer)
    answer = re.sub(r'\b(a|an|the|my|your|our)\b', '', answer)
    return ' '.join(answer.split())

def is_answer_correct(correct_answer, user_answer, riddle_text=None):
    norm_correct = normalize_answer(correct_answer)
    norm_user = normalize_answer(user_answer)
    
    if norm_user == norm_correct:
        return True
    
    special_cases = {
        "keys but no locks space but no room": ["keyboard", "qwerty"],
        "keyboard": ["keys but no locks", "space but no room", "qwerty"]
    }
    
    if riddle_text:
        norm_riddle = normalize_answer(riddle_text)
        for pattern, answers in special_cases.items():
            if pattern in norm_riddle and norm_user in [normalize_answer(a) for a in answers]:
                return True
            if norm_correct in [normalize_answer(a) for a in answers] and norm_user in [normalize_answer(a) for a in answers]:
                return True
    
    if norm_correct in norm_user or norm_user in norm_correct:
        return True
        
    return False

async def verify_answer_with_ai(riddle_question, correct_answer, user_answer):
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "Riddle Bot",
                },
                model="deepseek/deepseek-chat-v3-0324:free",
                messages=[
                    {
                        "role": "system",
                        "content": """Check if the user's answer matches the correct answer for the riddle.
                        Respond only with 'true' or 'false'."""
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Riddle: {riddle_question}
                        Correct Answer: {correct_answer}
                        User Answer: {user_answer}
                        
                        Is this correct? Respond only with 'true' or 'false'.
                        """
                    }
                ],
                max_tokens=10,
                temperature=0.1
            ),
            timeout=3.0
        )
        verification = response.choices[0].message.content.strip().lower()
        return verification == 'true'
    except:
        return False

def generate_riddle(difficulty="medium"):
    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Riddle Bot",
            },
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate a {difficulty} riddle with:
                    Riddle: [question]
                    Answer: [answer]
                    Hint: [hint]
                    Hints: [hint2] | [hint3] | [hint4]"""
                },
                {
                    "role": "user",
                    "content": f"Create a {difficulty} riddle about technology or general knowledge."
                }
            ]
        )
        
        content = response.choices[0].message.content
        
        riddle_data = {
            "question": "",
            "answer": "",
            "hint": "",
            "hints": [],
            "difficulty": difficulty
        }
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith("Riddle:"):
                riddle_data["question"] = line.replace("Riddle:", "").strip()
            elif line.startswith("Answer:"):
                riddle_data["answer"] = line.replace("Answer:", "").strip()
            elif line.startswith("Hint:"):
                riddle_data["hint"] = line.replace("Hint:", "").strip()
            elif line.startswith("Hints:"):
                hints = line.replace("Hints:", "").strip().split('|')
                riddle_data["hints"] = [h.strip() for h in hints if h.strip()]
        
        riddle_data["id"] = abs(hash(riddle_data["question"] + riddle_data["answer"]))
        return riddle_data
    except Exception as e:
        print(f"Error generating riddle: {e}")
        return None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_riddle', methods=['GET'])
def get_riddle():
    difficulty = request.args.get('difficulty', 'medium')
    session_id = request.args.get('session_id', 'default')
    
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            'answered': [],
            'score': 0,
            'start_time': {},
            'current_riddles': {}
        }
    
    riddle = generate_riddle(difficulty)
    if not riddle:
        return jsonify({"error": "Failed to generate riddle"}), 500
    
    user_sessions[session_id]['current_riddles'][riddle['id']] = riddle
    user_sessions[session_id]['start_time'][riddle['id']] = time.time()
    
    return jsonify({
        "id": riddle["id"],
        "question": riddle["question"],
        "hint": riddle["hint"],
        "hints": riddle.get("hints", []),
        "difficulty": riddle["difficulty"]
    })

@app.route('/check_answer', methods=['POST'])
def check_answer():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    riddle_id = data.get('id')
    user_answer = data.get('answer', '').strip()
    session_id = data.get('session_id', 'default')

    if not riddle_id or not user_answer:
        return jsonify({"error": "Missing required fields"}), 400

    if session_id not in user_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    riddle = user_sessions[session_id]['current_riddles'].get(riddle_id)
    if not riddle:
        return jsonify({"error": "Riddle not found"}), 404

    is_correct = is_answer_correct(
        riddle['answer'],
        user_answer,
        riddle['question']
    )
    
    if not is_correct:
        try:
            is_correct = asyncio.run(
                asyncio.wait_for(
                    verify_answer_with_ai(
                        riddle['question'],
                        riddle['answer'],
                        user_answer
                    ),
                    timeout=3.0
                )
            )
        except:
            is_correct = False
    
    time_taken = 0
    if riddle_id in user_sessions[session_id]['start_time']:
        start_time = user_sessions[session_id]['start_time'].pop(riddle_id)
        time_taken = time.time() - start_time
    
    points = 0
    if is_correct and riddle_id not in user_sessions[session_id]['answered']:
        user_sessions[session_id]['answered'].append(riddle_id)
        hints_used = data.get('hints_used', 0)
        time_bonus = max(0, 10 - min(time_taken, 10))
        hint_penalty = hints_used * 2
        points = max(5 + time_bonus - hint_penalty, 1)
        user_sessions[session_id]['score'] += points
    elif not is_correct:
        points = -5
        user_sessions[session_id]['score'] = max(0, user_sessions[session_id]['score'] + points)
    
    return jsonify({
        "correct": is_correct,
        "answer": riddle['answer'] if not is_correct else None,
        "score": user_sessions[session_id]['score'],
        "time_taken": round(time_taken, 1),
        "points_earned": points,
        "show_achievement": user_sessions[session_id]['score'] >= 100 and is_correct and not user_sessions[session_id].get('achievement_shown', False)
    })

# ======================== HTML/CSS/JS TEMPLATE ========================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Riddle Bot 🤖</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">
    <style>
        /* Full CSS from your original script */
        /* ... (include all the CSS from your original script) ... */
    </style>
</head>
<body>
    <!-- Full HTML from your original script -->
    <!-- ... (include all the HTML from your original script) ... -->
    
    <script>
        // Full JavaScript from your original script
        // ... (include all the JS from your original script) ...
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)
