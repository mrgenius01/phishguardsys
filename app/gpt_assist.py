import openai

openai.api_key = 'your-gpt-api-key'

def explain_result(email_text, prediction):
    prompt = f"""
You are a cybersecurity assistant. The user submitted the following email text:
"{email_text}"
Your model classified it as: {prediction}.
Explain why it might be {prediction} in simple terms.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful cyber security assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']
