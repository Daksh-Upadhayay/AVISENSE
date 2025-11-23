import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, classification_report
import joblib

# 1. Generate Synthetic Data (for demonstration)
# In a real scenario, this would load from a CSV or Database
def generate_data(n_samples=1000):
    np.random.seed(42)
    data = {
        'temperature': np.random.normal(220, 30, n_samples),
        'rpm': np.random.normal(7000, 500, n_samples),
        'vibration': np.random.exponential(0.02, n_samples),
        'oil_pressure': np.random.normal(40, 5, n_samples),
        'egt': np.random.normal(850, 50, n_samples),
        'compressor_pressure': np.random.normal(2.0, 0.2, n_samples),
        'engine_hours': np.random.uniform(0, 1000, n_samples),
        'maintenance_code': np.random.choice(['OK', 'MINOR', 'MAJOR'], n_samples, p=[0.7, 0.2, 0.1]),
        'error_codes_count': np.random.poisson(0.5, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Define target variable logic (Ground Truth)
    # Failure prone if high temp, high vibration, or low oil pressure
    conditions = (
        (df['temperature'] > 260) | 
        (df['vibration'] > 0.06) | 
        (df['oil_pressure'] < 30) |
        (df['maintenance_code'] == 'MAJOR') |
        (df['error_codes_count'] > 1)
    )
    df['is_prone_to_failure'] = conditions.astype(int)
    
    return df

# 2. Feature Engineering
def preprocess_data(df):
    # One-hot encode categorical variables
    df_processed = pd.get_dummies(df, columns=['maintenance_code'], drop_first=True)
    return df_processed

# 3. Model Training
def train_model():
    print("Generating synthetic training data...")
    df = generate_data(2000)
    
    X = df.drop('is_prone_to_failure', axis=1)
    y = df['is_prone_to_failure']
    
    X = preprocess_data(X)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Gradient Boosting Classifier...")
    # Using Gradient Boosting as requested
    clf = GradientBoostingClassifier(
        n_estimators=100, 
        learning_rate=0.1,
        max_depth=3, 
        random_state=42
    )
    clf.fit(X_train, y_train)
    
    # 4. Evaluation
    y_pred = clf.predict(X_test)
    print("\nModel Evaluation:")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(f"Precision: {precision_score(y_test, y_pred):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # 5. Feature Importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': clf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\nTop 5 Important Features:")
    print(feature_importance.head(5))
    
    # Save model
    joblib.dump(clf, 'avisense_model.joblib')
    print("\nModel saved to avisense_model.joblib")

if __name__ == "__main__":
    train_model()
