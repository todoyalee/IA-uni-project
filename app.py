import os
import json
import random
import re
import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS, cross_origin
import mysql.connector
from textblob import TextBlob
from dotenv import load_dotenv
import pyttsx3
import threading
import time
import wikipedia
from transformers import pipeline
import warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ========== TEXT-TO-SPEECH SETUP ==========
print("Initializing TTS engine...")
try:
    tts_engine = pyttsx3.init()
    voices = tts_engine.getProperty('voices')
    print(f"Found {len(voices)} voices")
    
    # Set voice properties
    tts_engine.setProperty('rate', 180)
    tts_engine.setProperty('volume', 1.0)
    
    # Try to find a good voice
    for voice in voices:
        if 'female' in voice.name.lower():
            tts_engine.setProperty('voice', voice.id)
            print(f"Using voice: {voice.name}")
            break
        elif 'zira' in voice.name.lower():
            tts_engine.setProperty('voice', voice.id)
            print(f"Using voice: {voice.name}")
            break
    else:
        if voices:
            tts_engine.setProperty('voice', voices[0].id)
            print(f"Using default voice: {voices[0].name}")
    
    # Test TTS
    print("Testing TTS...")
    tts_engine.say("TTS initialized successfully")
    tts_engine.runAndWait()
    print("TTS test passed!")
    
except Exception as e:
    print(f"TTS initialization failed: {e}")
    tts_engine = None

# ========== EMOTION DETECTION MODEL ==========
print("Loading emotion detection model...")
try:
    # Using a smaller, faster model
    emotion_model = pipeline(
        "text-classification", 
        model="bhadresh-savani/bert-base-uncased-emotion",
        return_all_scores=False
    )
    print("Emotion model loaded successfully!")
except Exception as e:
    print(f"Could not load emotion model: {e}")
    print("Falling back to keyword-based detection...")
    emotion_model = None

# ========== WIKIPEDIA SETUP ==========
wikipedia.set_lang("en")
wikipedia.set_rate_limiting(True)

# ========== DATABASE SETUP ==========
def get_db():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="mightguy"
        )
    except Exception as e:
        print(f"Database error: {e}")
        return None

# ========== EMOTION DETECTION FUNCTION ==========
def detect_emotion(text):
    """Detect emotion using model or fallback to keywords"""
    if emotion_model:
        try:
            result = emotion_model(text)[0]
            emotion = result['label'].lower()
            confidence = result['score']
            print(f"Model detected emotion: {emotion} (confidence: {confidence:.2f})")
            
            # Map model emotions to standard ones
            emotion_map = {
                'sadness': 'sadness',
                'joy': 'joy',
                'love': 'joy',
                'anger': 'anger',
                'fear': 'fear',
                'surprise': 'surprise'
            }
            
            return emotion_map.get(emotion, 'neutral')
        except Exception as e:
            print(f"Model error: {e}")
    
    # Fallback to keyword detection
    print("Using keyword-based emotion detection...")
    emotion_keywords = {
        'joy': ['happy', 'joy', 'excited', 'great', 'good', 'awesome', 'wonderful', 'love', 'like', 'excellent', 'fantastic', 'amazing', 'yay', 'yeah'],
        'sadness': ['sad', 'unhappy', 'depressed', 'cry', 'tears', 'bad', 'terrible', 'awful', 'miserable', 'hopeless', 'alone', 'lonely'],
        'anger': ['angry', 'mad', 'furious', 'hate', 'rage', 'annoyed', 'frustrated', 'irritated', 'pissed', 'upset'],
        'fear': ['scared', 'afraid', 'fear', 'worried', 'anxious', 'nervous', 'terrified', 'panic', 'anxiety'],
        'surprise': ['surprise', 'shocked', 'amazed', 'wow', 'oh', 'unbelievable', 'incredible', 'whoa']
    }
    
    text_lower = text.lower()
    emotion_scores = {emotion: 0 for emotion in emotion_keywords}
    
    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                emotion_scores[emotion] += 1
    
    # Check punctuation
    if '!' in text:
        emotion_scores['surprise'] += 1
    
    if '?' in text and ('why' in text_lower or 'how' in text_lower):
        emotion_scores['fear'] += 0.5
    
    detected_emotion = max(emotion_scores, key=emotion_scores.get)
    
    if emotion_scores[detected_emotion] == 0:
        detected_emotion = 'neutral'
    
    return detected_emotion

# ========== RESPONSE GENERATION ==========
def load_responses():
    responses = [
        {"user_input": ["hello", "hi", "hey"], "bot_response": "Hello! How are you today? 😊"},
        {"user_input": ["how are you", "how do you do"], "bot_response": "I'm doing great! Thanks for asking. How can I help you?"},
        {"user_input": ["bye", "goodbye", "exit"], "bot_response": "Goodbye! Have a wonderful day! 👋"},
        {"user_input": ["thank you", "thanks"], "bot_response": "You're welcome! I'm happy to help. 😊"},
        {"user_input": ["help", "support", "need help"], "bot_response": "I'm here to help! What do you need assistance with?"},
        {"user_input": ["name", "your name", "who are you"], "bot_response": "I'm Rais, your AI assistant! I can help with various tasks."},
        {"user_input": ["what can you do", "capabilities"], "bot_response": "I can chat with you, detect emotions, read text aloud, and help with questions!"},
        {"user_input": ["good", "fine", "okay"], "bot_response": "That's good to hear! How can I assist you today?"},
        {"user_input": ["bad", "not good", "terrible"], "bot_response": "I'm sorry to hear that. Would you like to talk about it?"},
        {"user_input": ["i love you"], "bot_response": "Aww, that's sweet! I'm here to help you anytime. 💖"},
        {"user_input": ["i hate you"], "bot_response": "I'm sorry you feel that way. How can I improve to help you better?"},
        {"user_input": ["scared", "afraid"], "bot_response": "It's okay to feel scared sometimes. I'm here to help you feel better. 💪"},
        {"user_input": ["happy", "excited"], "bot_response": "That's wonderful! I'm happy that you're happy! 🎉"},
        {"user_input": ["sad", "unhappy"], "bot_response": "I'm sorry you're feeling down. Remember, it's okay to feel sad sometimes. 💙"},
        {"user_input": ["angry", "mad"], "bot_response": "I understand you're upset. Take a deep breath. How can I help resolve this? 🧘"},
        {"user_input": ["what time", "current time"], "bot_response": f"The current time is {time.strftime('%I:%M %p')}."},
        {"user_input": ["today", "date"], "bot_response": f"Today is {time.strftime('%A, %B %d, %Y')}."},
        {"user_input": ["joke", "tell me a joke"], "bot_response": "Why don't scientists trust atoms? Because they make up everything! 😄"},
        {"user_input": ["weather"], "bot_response": "I don't have real-time weather data, but you can check weather.com for accurate forecasts! ☀️"},
        {"user_input": ["who created you", "who made you"], "bot_response": "I was created by a developer using Flask and Python to help users like you! 🤖"}
    ]
    return responses

responses = load_responses()
print(f"Loaded {len(responses)} responses")

# ========== WIKIPEDIA SEARCH ==========
def get_wikipedia_answer(question):
    """Search Wikipedia for answers"""
    try:
        # Clean the question
        question = question.lower().strip()
        
        # Remove common question words
        question_words = ["what is", "who is", "tell me about", "explain", "define", 
                         "what are", "who are", "what was", "who was", "what were"]
        
        search_term = question
        for word in question_words:
            if question.startswith(word):
                search_term = question[len(word):].strip()
                break
        
        # If search term is too short, use the whole question
        if len(search_term) < 3:
            search_term = question
        
        # Get summary
        print(f"Searching Wikipedia for: {search_term}")
        summary = wikipedia.summary(search_term, sentences=2)
        
        return f"According to Wikipedia: {summary}"
        
    except wikipedia.exceptions.DisambiguationError as e:
        options = e.options[:3]
        return f"Your question is ambiguous. Did you mean: {', '.join(options)}?"
    
    except wikipedia.exceptions.PageError:
        return None  # Return None so we can fall back to other responses
    
    except Exception as e:
        print(f"Wikipedia error: {e}")
        return None

# ========== SPEAK FUNCTION ==========
def speak(text):
    if tts_engine:
        try:
            def speak_thread():
                tts_engine.say(text)
                tts_engine.runAndWait()
            
            thread = threading.Thread(target=speak_thread)
            thread.start()
            return True
        except Exception as e:
            print(f"TTS error: {e}")
            return False
    return False

# ========== MAIN RESPONSE LOGIC ==========
def get_response(user_input, user_id):
    original_input = user_input
    user_input = user_input.strip().lower()
    
    # Detect emotion
    emotion = detect_emotion(original_input)
    print(f"Emotion detected: {emotion}")
    
    # Analyze sentiment
    try:
        blob = TextBlob(original_input)
        sentiment = blob.sentiment.polarity
    except:
        sentiment = 0.0
    
    # ===== 1. CHECK FOR WIKIPEDIA QUESTIONS =====
    wikipedia_keywords = ["what is", "who is", "tell me about", "explain", "define", 
                         "what are", "who are", "what was", "who was", "what were"]
    
    if any(keyword in user_input for keyword in wikipedia_keywords):
        wiki_answer = get_wikipedia_answer(original_input)
        if wiki_answer:
            bot_response = wiki_answer
            speak(bot_response)
            emotion = 'neutral'

            return bot_response, emotion, sentiment
    
    # ===== 2. CHECK FOR EXACT MATCHES =====
    for response in responses:
        for keyword in response["user_input"]:
            if keyword in user_input:
                bot_response = response["bot_response"]
                
                # Add emotion-based customization
                emotion_prefix = {
                    'joy': "😊 ",
                    'sadness': "😔 ",
                    'anger': "😠 ",
                    'fear': "😨 ",
                    'surprise': "😲 "
                }.get(emotion, "")
                
                bot_response = emotion_prefix + bot_response
                
                speak(bot_response)
                
                # Store in database
                db = get_db()
                if db:
                    try:
                        cursor = db.cursor()
                        cursor.execute(
                            "INSERT INTO questions (question, response, emotion, user_id, sentiment) VALUES (%s, %s, %s, %s, %s)",
                            (original_input, bot_response, emotion, user_id, sentiment)
                        )
                        db.commit()
                        cursor.close()
                    except Exception as e:
                        print(f"Database insert error: {e}")
                    finally:
                        db.close()
                
                return bot_response, emotion, sentiment
    
    # ===== 3. DEFAULT RESPONSES WITH EMOTION AWARENESS =====
    emotion_responses = {
        'joy': [
            f"I'm glad you're feeling happy! 😊 Tell me more about what's making you feel good.",
            f"Your joy is contagious! 😄 How can I help you today?",
            f"Great to see you in a good mood! What would you like to know?"
        ],
        'sadness': [
            f"I sense you're feeling down. 😔 Would you like to talk about it?",
            f"I'm here for you. 💙 It's okay to feel sad sometimes.",
            f"I understand you're feeling low. How can I help you feel better?"
        ],
        'anger': [
            f"I can tell you're upset. 😠 Let's work through this together.",
            f"I understand you're angry. Take a deep breath. 🧘 How can I help?",
            f"Let's talk about what's bothering you. I'm here to listen."
        ],
        'fear': [
            f"It's okay to feel scared sometimes. 😨 I'm here to help.",
            f"I sense some fear in your message. 💪 You're stronger than you think.",
            f"Don't worry, I'm here with you. What's making you anxious?"
        ],
        'surprise': [
            f"Wow! 😲 That sounds surprising! Tell me more.",
            f"I can sense your surprise! What happened?",
            f"That's unexpected! 😮 I'm curious to hear more."
        ],
        'neutral': [
            f"I'm here to help you! How can I assist?",
            f"That's interesting. Tell me more about it.",
            f"I understand. How can I help you with that?",
            f"Let me think about that..."
        ]
    }
    
    bot_response = random.choice(emotion_responses.get(emotion, emotion_responses['neutral']))
    
    # If it's a factual question but Wikipedia didn't find it
    question_words = ["what", "who", "when", "where", "why", "how", "which"]
    if any(word in user_input for word in question_words):
        bot_response = f"I'm not sure about that specific question. (I detected you're feeling {emotion}) Would you like me to search for more information?"
    
    speak(bot_response)
    
    return bot_response, emotion, sentiment

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get', methods=['POST'])
@cross_origin()
def chat():
    try:
        data = request.get_json()
        user_input = data.get('msg', '').strip()
        user_id = data.get('id', 'guest')
        
        if not user_input:
            return jsonify({
                "msg": "Please type something!",
                "emotion": "neutral",
                "sentiment": 0.0
            })
        
        print(f"Received: '{user_input}' from {user_id}")
        
        response, emotion, sentiment = get_response(user_input, user_id)
        
        return jsonify({
            "msg": response,
            "emotion": emotion,
            "sentiment": float(sentiment)
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            "msg": "Sorry, I encountered an error. Please try again.",
            "emotion": "neutral",
            "sentiment": 0.0
        })

@app.route('/test')
def test():
    return jsonify({
        "status": "active",
        "tts": "working" if tts_engine else "disabled",
        "emotion_model": "loaded" if emotion_model else "keyword_based",
        "wikipedia": "enabled"
    })

if __name__ == '__main__':
    print("=" * 50)
    print("CHATBOT STARTING")
    print(f"TTS Status: {'ACTIVE' if tts_engine else 'INACTIVE'}")
    print(f"Emotion Model: {'LOADED' if emotion_model else 'KEYWORD-BASED (fallback)'}")
    print(f"Wikipedia: ENABLED")
    print("=" * 50)
    
    # Test Wikipedia
    try:
        test_summary = wikipedia.summary("Python programming", sentences=1)
        print(f"Wikipedia test: {test_summary[:50]}...")
    except:
        print("Wikipedia connection test failed")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)