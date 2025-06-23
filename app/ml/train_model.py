# app/ml/train_model.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import joblib

# Utility to inspect large CSV files

def inspect_large_csv(file_path, nrows=3):
    """Read and print the header and first nrows of a large CSV file."""
    try:
        chunk_iter = pd.read_csv(file_path, chunksize=nrows)
        first_chunk = next(chunk_iter)
        print(f"Header columns: {list(first_chunk.columns)}")
        print(f"First {nrows} rows:")
        print(first_chunk)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

# Utility to load large CSV files in chunks and concatenate

def load_large_csv(file_path, text_col, label_col, nrows=None):
    """Load a large CSV file in chunks and return a DataFrame with text and label columns."""
    dfs = []
    try:
        for chunk in pd.read_csv(file_path, usecols=[text_col, label_col], chunksize=10000):
            dfs.append(chunk)
            if nrows and sum(len(df) for df in dfs) >= nrows:
                break
        df = pd.concat(dfs, ignore_index=True)
        if nrows:
            df = df.iloc[:nrows]
        return df
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return pd.DataFrame(columns=[text_col, label_col])

# Choose which file to process
DATA_FILE = 'app/ml/phishing_emails/phishing_email.csv'  # Change to your desired file
TEXT_COL = 'text_combined'  # Adjust as needed
LABEL_COL = 'label'

# Inspect the large CSV file (prints header and sample rows)
inspect_large_csv(DATA_FILE, nrows=3)

# Load data for training
print(f"Loading data from {DATA_FILE}...")
df = load_large_csv(DATA_FILE, TEXT_COL, LABEL_COL, nrows=50000)  # Adjust nrows as needed

if df.empty:
    print(f"Error: {DATA_FILE} is empty or could not be loaded. Please check the file path and format.")
    exit(1)

# Drop rows with missing label or text
print(f"Loaded {len(df)} rows. Columns: {df.columns.tolist()}")
df = df.dropna(subset=[LABEL_COL, TEXT_COL])

# Map labels to binary if needed (adjust mapping as appropriate)
if df[LABEL_COL].dtype != int:
    df[LABEL_COL] = df[LABEL_COL].map({'spam': 1, 'phishing': 1, 'ham': 0, 'legit': 0, 'legitimate': 0, 1: 1, 0: 0})
    df = df.dropna(subset=[LABEL_COL])

df[LABEL_COL] = df[LABEL_COL].astype(int)

X = df[TEXT_COL].astype(str)
y = df[LABEL_COL]

print(f"Final dataset: {len(X)} samples. X shape: {X.shape}, y shape: {y.shape}")

if X.empty or y.empty:
    print("Error: Features (X) or labels (y) are empty after processing. Check your data file and preprocessing steps.")
    exit(1)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Define pipeline
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(stop_words='english', max_features=8000)),
    ('clf', RandomForestClassifier(n_estimators=150, random_state=42))
])

# Train
pipeline.fit(X_train, y_train)

# Evaluate
y_pred = pipeline.predict(X_test)
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(pipeline, 'app/ml/phishing_model.pkl')
print("✅ Model trained and saved successfully.")

# Example: Load and train on the simple custom dataset
SIMPLE_DATA_FILE = 'app/ml/simple_spam_dataset.csv'
SIMPLE_TEXT_COLS = ['subject', 'body']
SIMPLE_FEATURE_COLS = ['domain_age', 'grammar_score', 'spelling_score', 'link_score', 'gpt_score']
SIMPLE_LABEL_COL = 'label'

def load_simple_dataset(file_path):
    df = pd.read_csv(file_path)
    # Combine subject and body for text features if needed
    df['text'] = df['subject'].fillna('') + ' ' + df['body'].fillna('')
    X = df[SIMPLE_FEATURE_COLS]
    y = df[SIMPLE_LABEL_COL]
    return X, y

# Enable training and saving of the simple model
X, y = load_simple_dataset(SIMPLE_DATA_FILE)
print(f"Loaded simple dataset: {X.shape[0]} samples, features: {X.shape[1]}")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=50, random_state=42)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
joblib.dump(model, 'app/ml/simple_spam_model.pkl')
print("✅ Simple model trained and saved as simple_spam_model.pkl")
