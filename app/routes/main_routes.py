from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
import joblib
import numpy as np
import whois
import re
import datetime
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
import imaplib
import email as pyemail
from functools import wraps
import hashlib
import threading

main = Blueprint('main', __name__)
# Load the simple model trained on custom features
simple_model = joblib.load('app/ml/simple_spam_model.pkl')

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

CONFIG_PATH = 'user_config.json'
IT_REVIEW_FILE = 'it_reviewed_emails.json'
IT_REVIEW_LOCK = threading.Lock()

# Simple user store (for demo; use a DB in production)
IT_USERS = {
    'admin': hashlib.sha256('adminpass'.encode()).hexdigest(),
}

# Store analyzed emails (in-memory for now, can use DB/file)
ANALYZED_EMAILS = []

def load_user_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def save_user_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f)

def load_it_reviewed():
    try:
        with open(IT_REVIEW_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_it_reviewed(emails):
    with IT_REVIEW_LOCK:
        with open(IT_REVIEW_FILE, 'w') as f:
            json.dump(emails, f)

# --- Feature extraction functions ---
# In-memory cache for domain ages
_domain_age_cache = {}

def extract_domain_age(email):
    sender = email.get('sender', '')
    domain = ''
    if sender and '@' in sender:
        domain = sender.split('@')[-1].strip().lower()
        # Remove leading/trailing characters like > or spaces
        domain = domain.lstrip('> ').rstrip(' .')
    else:
        match = re.search(r'[\w\.-]+@[\w\.-]+', email.get('body', '') + ' ' + email.get('subject', ''))
        if match:
            domain = match.group().split('@')[-1].strip().lower().lstrip('> ').rstrip(' .')
    if not domain:
        return -1  # Unknown
    if domain in _domain_age_cache:
        return _domain_age_cache[domain]
    try:
        w = whois.whois(domain)
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            # Pick the earliest valid date
            creation_date = min([d for d in creation_date if isinstance(d, datetime.datetime)], default=None)
        if isinstance(creation_date, datetime.datetime):
            age = (datetime.datetime.now() - creation_date).days / 365.25
            age = max(age, 0.01)
            _domain_age_cache[domain] = age
            return age
    except Exception:
        pass
    _domain_age_cache[domain] = -1
    return -1  # Unknown

def grammar_score(text):
    """
    Use Gemini (Google Generative AI) to rate the grammar quality of the text.
    Returns a float between 0 (poor grammar) and 1 (excellent grammar).
    """
    if not GEMINI_API_KEY:
        return 0.7  # fallback if no key
    prompt = (
        "You are an expert English language assistant. Rate the grammar quality of the following text on a scale from 0 (very poor grammar) to 1 (perfect grammar). Only return a number between 0 and 1.\n\n"
        f"Text:\n{text}\n\nGrammar Score:"
    )
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        score_str = response.text.strip().split()[0]
        score = float(score_str)
        return min(max(score, 0.0), 1.0)
    except Exception as e:
        print(f"Error in grammar_score: {e}")
        return 0.7

def spelling_score(text):
    """
    Use Gemini (Google Generative AI) to rate the spelling quality of the text.
    Returns a float between 0 (many spelling errors) and 1 (no spelling errors).
    """
    if not GEMINI_API_KEY:
        return 0.7  # fallback if no key
    prompt = (
        "You are an expert English language assistant. Rate the spelling quality of the following text on a scale from 0 (many spelling errors) to 1 (no spelling errors). Only return a number between 0 and 1.\n\n"
        f"Text:\n{text}\n\nSpelling Score:"
    )
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        score_str = response.text.strip().split()[0]
        score = float(score_str)
        return min(max(score, 0.0), 1.0)
    except Exception as e:
        print(f"Error in spelling_score: {e}")
        return 0.7

def link_score(text):
    links = re.findall(r'http[s]?://\S+', text)
    if not links:
        return 0.0
    # Simple heuristic: more links = higher risk
    score = min(1.0, 0.3 + 0.2 * len(links))
    return round(score, 2)

def gpt_score(text):
    """
    Use Gemini (Google Generative AI) to rate the likelihood of the email being spam/phishing.
    Returns a float between 0 (not spam) and 1 (very likely spam).
    """
    if not GEMINI_API_KEY:
        return 0.7  # fallback if no key
    prompt = (
        "You are an email security assistant. Rate the following email on a scale from 0 (not spam) to 1 (very likely spam/phishing). "
        "Only return a number between 0 and 1.\n\n"
        f"Email:\n{text}\n\nSpam Score:"
    )
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        score_str = response.text.strip().split()[0]
        score = float(score_str)
        return min(max(score, 0.0), 1.0)
    except Exception as e:
        print(f"Error {e}")
        return 0.7

def generate_explanation(features, prediction):
    reasons = []
    if features['link_score'] > 0.7:
        reasons.append("This email contains suspicious links.")
    if features['domain_age'] < 1:
        reasons.append("The sender's domain is very new.")
    if features['grammar_score'] < 0.5:
        reasons.append("The email has poor grammar.")
    if features['spelling_score'] < 0.5:
        reasons.append("The email has spelling mistakes.")
    if features['gpt_score'] > 0.8:
        reasons.append("AI analysis suggests this email is likely spam.")
    if not reasons:
        reasons.append("No major red flags detected, but always be cautious.")
    if prediction == 1:
        verdict = "⚠️ This email is likely spam or phishing."
    else:
        verdict = "✅ This email appears safe."
    return verdict + "\n" + " ".join(reasons)

@main.route('/analyze', methods=['POST'])
def analyze_email():
    data = request.json
    subject = data.get('subject', '')
    body = data.get('body', '')
    features = {
        'domain_age': data.get('domain_age', extract_domain_age(data)),
        'grammar_score': grammar_score(subject + ' ' + body),
        'spelling_score': spelling_score(subject + ' ' + body),
        'link_score': link_score(subject + ' ' + body),
        'gpt_score': gpt_score(subject + ' ' + body)
    }
    X = np.array([[features['domain_age'], features['grammar_score'], features['spelling_score'], features['link_score'], features['gpt_score']]])
    prediction = int(simple_model.predict(X)[0])
    explanation = generate_explanation(features, prediction)
    # Store the analyzed email (for IT dashboard)
    ANALYZED_EMAILS.append({
        'subject': subject,
        'sender': data.get('sender', ''),
        'received': data.get('received', ''),
        'analysis': {
            'prediction': prediction,
            'explanation': explanation,
            'features': features
        }
    })
    return jsonify({
        'prediction': prediction,
        'explanation': explanation,
        'features': features
    })

@main.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        cfg = request.json
        save_user_config(cfg)
        return jsonify({'status': 'ok'})
    else:
        cfg = load_user_config()
        return jsonify(cfg or {})

@main.route('/fetch_emails', methods=['GET'])
def fetch_emails():
    cfg = load_user_config()
    if not cfg or not cfg.get('email') or not cfg.get('imap_server') or not cfg.get('password'):
        return jsonify({'error': 'IMAP not configured'}), 400
    try:
        mail = imaplib.IMAP4_SSL(cfg['imap_server'], int(cfg.get('imap_port', 993)))
        mail.login(cfg['email'], cfg['password'])
        mail.select('inbox')
        typ, data = mail.search(None, 'ALL')
        email_ids = data[0].split()[-20:]  # last 20 emails
        emails = []
        for eid in reversed(email_ids):
            typ, msg_data = mail.fetch(eid, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = pyemail.message_from_bytes(response_part[1])
                    subject = pyemail.header.decode_header(msg['Subject'])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(errors='ignore')
                    sender = msg['From']
                    date = msg['Date']
                    body = ''
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == 'text/plain' and part.get_payload(decode=True):
                                body = part.get_payload(decode=True).decode(errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True)
                        if body:
                            body = body.decode(errors='ignore')
                        else:
                            body = ''
                    emails.append({
                        'subject': subject,
                        'sender': sender,
                        'body': body,
                        'received': date
                    })
        mail.logout()
        return jsonify({'emails': emails})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('it_logged_in'):
            return redirect(url_for('main.it_login'))
        return f(*args, **kwargs)
    return decorated

@main.route('/it-login', methods=['GET', 'POST'])
def it_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in IT_USERS and IT_USERS[username] == hashlib.sha256(password.encode()).hexdigest():
            session['it_logged_in'] = True
            return redirect(url_for('main.it_dashboard'))
        return render_template('it_login.html', error='Invalid credentials')
    return render_template('it_login.html')

@main.route('/it-logout')
def it_logout():
    session.pop('it_logged_in', None)
    return redirect(url_for('main.it_login'))

@main.route('/it-dashboard')
@login_required
def it_dashboard():
    return render_template('it_dashboard.html')

@main.route('/submit_it_review', methods=['POST'])
def submit_it_review():
    email = request.json
    emails = load_it_reviewed()
    emails.append(email)
    save_it_reviewed(emails)
    return jsonify({'status': 'ok'})

@main.route('/api/flagged-emails')
@login_required
def api_flagged_emails():
    emails = load_it_reviewed()
    flagged = [e for e in emails if e.get('analysis', {}).get('prediction') == 1]
    return jsonify(flagged)

@main.route('/api/email-stats')
@login_required
def api_email_stats():
    emails = load_it_reviewed()
    from collections import Counter
    import math
    label_counts = Counter(e.get('analysis', {}).get('prediction', 'unknown') for e in emails)
    domain_ages = [e.get('analysis', {}).get('features', {}).get('domain_age') for e in emails if e.get('analysis')]
    domain_ages = [a for a in domain_ages if isinstance(a, (int, float)) and a >= 0]
    flagged_domains = [e.get('sender', '').split('@')[-1] for e in emails if e.get('analysis', {}).get('prediction') == 1]
    top_domains = Counter(flagged_domains).most_common(5)
    return jsonify({
        'label_counts': dict(label_counts),
        'domain_ages': domain_ages,
        'top_domains': top_domains
    })

@main.route('/user_gpt_explain', methods=['POST'])
def user_gpt_explain():
    data = request.json
    analysis = data.get('analysis', {})
    email = data.get('email', {})
    prompt = (
        "You are a helpful email assistant. Given the following analysis JSON for an email, explain to a non-technical user in a friendly, clear way why this email might be safe or suspicious. "
        "Highlight the most important factors and give practical advice.\n\n"
        f"Email subject: {email.get('subject', '')}\n"
        f"Sender: {email.get('sender', '')}\n"
        f"Analysis JSON: {json.dumps(analysis.get('features', {}))}\n"
        f"Spam prediction: {analysis.get('prediction', '')}\n"
        "\nFriendly explanation:"
    )
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        friendly = response.text.strip()
        return jsonify({'friendly_explanation': friendly})
    except Exception as e:
        return jsonify({'friendly_explanation': 'Could not generate explanation.'}), 500
