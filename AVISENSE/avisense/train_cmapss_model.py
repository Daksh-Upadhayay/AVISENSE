import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler

def load_cmapss_data():
    """
    Load NASA C-MAPSS dataset and prepare for binary classification
    """
    print("="*80)
    print("LOADING NASA C-MAPSS DATASET")
    print("="*80)
    
    # Column names for C-MAPSS dataset
    index_names = ['unit_id', 'time_cycles']
    setting_names = ['setting_1', 'setting_2', 'setting_3']
    sensor_names = [f'sensor_{i}' for i in range(1, 22)]
    col_names = index_names + setting_names + sensor_names
    
    # Load training data
    print("\n📂 Loading train_FD001.txt...")
    train_df = pd.read_csv('/Users/dakshupadhayay/Downloads/CMaps/train_FD001.txt', 
                           sep='\s+', header=None, names=col_names)
    
    print(f"   Shape: {train_df.shape}")
    print(f"   Engines: {train_df['unit_id'].nunique()}")
    print(f"   Total cycles: {len(train_df)}")
    
    # Create binary failure labels
    # Strategy: Last 30 cycles before failure = "Failure", earlier cycles = "Safe"
    print("\n🏷️  Creating labels...")
    
    def label_data(df, failure_window=30):
        """
        Label data: last N cycles = Failure (1), rest = Safe (0)
        """
        df = df.copy()
        df['RUL'] = 0  # Remaining Useful Life
        df['Binary_Failure'] = 0
        
        for unit_id in df['unit_id'].unique():
            unit_data = df[df['unit_id'] == unit_id]
            max_cycle = unit_data['time_cycles'].max()
            
            # Calculate RUL for each cycle
            df.loc[df['unit_id'] == unit_id, 'RUL'] = max_cycle - df.loc[df['unit_id'] == unit_id, 'time_cycles']
            
            # Label last N cycles as failure
            df.loc[(df['unit_id'] == unit_id) & (df['RUL'] <= failure_window), 'Binary_Failure'] = 1
        
        return df
    
    train_df = label_data(train_df, failure_window=30)
    
    # Check class distribution
    print(f"\n📊 Class Distribution:")
    print(f"   Safe (0): {(train_df['Binary_Failure']==0).sum()} ({(train_df['Binary_Failure']==0).mean():.1%})")
    print(f"   Failure (1): {(train_df['Binary_Failure']==1).sum()} ({(train_df['Binary_Failure']==1).mean():.1%})")
    
    # Select features
    # Remove constant or near-constant sensors
    feature_cols = setting_names + sensor_names
    
    # Remove sensors with very low variance
    variances = train_df[feature_cols].var()
    useful_features = variances[variances > 0.01].index.tolist()
    
    print(f"\n🔍 Selected {len(useful_features)} features (removed low-variance sensors)")
    
    return train_df, useful_features

def train_cmapss_model():
    """
    Train model on NASA C-MAPSS dataset
    """
    # Load data
    df, feature_cols = load_cmapss_data()
    
    # Prepare features and target
    X = df[feature_cols]
    y = df['Binary_Failure']
    
    # Train/test split
    print(f"\n✂️  Splitting data (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scaling
    print(f"\n📏 Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Random Forest with class balancing
    print(f"\n🤖 Training Random Forest Classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    print(f"\n{'='*80}")
    print("MODEL PERFORMANCE ON NASA C-MAPSS")
    print(f"{'='*80}")
    
    y_pred = model.predict(X_test_scaled)
    
    print(f"\n📈 Overall Metrics:")
    print(f"   Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
    print(f"   Precision: {precision_score(y_test, y_pred):.4f}")
    print(f"   Recall:    {recall_score(y_test, y_pred):.4f}")
    print(f"   F1 Score:  {f1_score(y_test, y_pred):.4f}")
    
    print(f"\n📊 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Safe', 'Failure']))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    safe_recall = cm[0,0] / (cm[0,0] + cm[0,1])
    fail_recall = cm[1,1] / (cm[1,0] + cm[1,1])
    
    print(f"\n🎯 Confusion Matrix:")
    print(f"                 Predicted")
    print(f"                 Safe  Failure")
    print(f"   Actual Safe   {cm[0,0]:<5} {cm[0,1]:<5}")
    print(f"   Actual Fail   {cm[1,0]:<5} {cm[1,1]:<5}")
    
    print(f"\n✅ Per-Class Recall:")
    print(f"   Safe Recall:    {safe_recall:.4f} ({safe_recall:.1%})")
    print(f"   Failure Recall: {fail_recall:.4f} ({fail_recall:.1%})")
    
    # Feature importance
    print(f"\n🔍 Top 10 Most Important Features:")
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    for i in range(min(10, len(feature_cols))):
        idx = indices[i]
        print(f"   {i+1}. {feature_cols[idx]:<20} {importances[idx]:.4f}")
    
    # Save model
    print(f"\n💾 Saving NASA C-MAPSS model...")
    joblib.dump(model, 'avisense_model_cmapss.joblib')
    joblib.dump(scaler, 'avisense_scaler_cmapss.joblib')
    
    feature_info = {
        'feature_names': feature_cols,
        'model_type': 'RandomForest_CMAPSS',
        'train_date': pd.Timestamp.now().isoformat(),
        'safe_recall': float(safe_recall),
        'failure_recall': float(fail_recall),
        'dataset': 'NASA_C-MAPSS_FD001'
    }
    joblib.dump(feature_info, 'avisense_model_cmapss_info.joblib')
    
    print(f"\n✅ Model saved as: avisense_model_cmapss.joblib")
    print(f"✅ Scaler saved as: avisense_scaler_cmapss.joblib")
    
    # Assessment
    print(f"\n{'='*80}")
    print("ASSESSMENT")
    print(f"{'='*80}\n")
    
    if safe_recall > 0.75 and fail_recall > 0.75:
        print("🎉 EXCELLENT! NASA C-MAPSS model achieves production-ready performance!")
        print(f"   Safe Recall: {safe_recall:.1%}")
        print(f"   Failure Recall: {fail_recall:.1%}")
        print("   ✅ Ready for deployment")
    elif safe_recall > 0.65 and fail_recall > 0.65:
        print("✅ GOOD! NASA C-MAPSS model shows strong performance.")
        print(f"   Safe Recall: {safe_recall:.1%}")
        print(f"   Failure Recall: {fail_recall:.1%}")
        print("   ✅ Acceptable for production use")
    else:
        print("⚠️  Model needs tuning.")
        print(f"   Safe Recall: {safe_recall:.1%}")
        print(f"   Failure Recall: {fail_recall:.1%}")
    
    return model, scaler

if __name__ == "__main__":
    train_cmapss_model()
