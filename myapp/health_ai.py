import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler


def prepare_dataset(records):
    """
    Convert HealthRecord queryset to a DataFrame and prepare features & targets.
    """
    if not records:
        return None, None

    df = pd.DataFrame(records)

    if df.empty:
        return None, None

    # Ensure date is datetime (helps with future trend work)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])

    # Sort by date — important for any trend-related logic later
    df = df.sort_values('date').reset_index(drop=True)

    # Create risk labels for ML models
    df["diabetes_risk"] = (df["sugar_level"] > 140).astype(int)
    df["hypertension_risk"] = (df["systolic_bp"] > 130).astype(int)

    features = df[[
        "weight",
        "systolic_bp",
        "diastolic_bp",
        "sugar_level",
        "sleep_hours",
        "exercise_minutes"
    ]]

    return df, features


def train_models(features, diabetes_target, hypertension_target):
    """
    Train Logistic Regression for diabetes and Decision Tree for hypertension.
    Returns models and fitted scaler.
    """
    if len(features) < 2:
        # Prevent training error with too few samples
        diabetes_model = LogisticRegression()
        hypertension_model = DecisionTreeClassifier()
        scaler = StandardScaler()
        # dummy fit to avoid attribute errors later
        scaler.fit(np.zeros((2, features.shape[1])))
        return diabetes_model, hypertension_model, scaler

    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    # Small improvement: add class_weight='balanced' (helps with imbalanced risk labels)
    diabetes_model = LogisticRegression(max_iter=1000, class_weight='balanced')
    diabetes_model.fit(X, diabetes_target)

    hypertension_model = DecisionTreeClassifier(max_depth=5, class_weight='balanced')
    hypertension_model.fit(X, hypertension_target)

    return diabetes_model, hypertension_model, scaler


def detect_anomalies(df):
    """
    Detect anomalies in health data for alerts.
    Modified to also consider sudden changes (better early warning)
    """
    anomalies = []

    if df.empty or len(df) < 2:
        return anomalies

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    # Extreme values (your original checks)
    if latest["systolic_bp"] > 160:
        anomalies.append("Very high blood pressure detected today")

    if latest["sugar_level"] > 200:
        anomalies.append("Dangerously high sugar level today")

    if latest["sleep_hours"] < 4:
        anomalies.append("Severely low sleep duration today")

    # Small addition: detect sudden worsening (helps fulfill early warning requirement)
    if latest["systolic_bp"] > previous["systolic_bp"] + 20:
        anomalies.append("Sudden increase in blood pressure detected")

    if latest["sugar_level"] > previous["sugar_level"] + 50:
        anomalies.append("Sudden increase in sugar level detected")

    return anomalies


def risk_level(value, low, high):
    """
    Assign Low, Medium, High risk based on thresholds.
    (unchanged — already good)
    """
    if value < low:
        return "Low"
    elif value < high:
        return "Medium"
    else:
        return "High"


def generate_recommendations(df):
    """
    Generate personalized recommendations based on latest record and averages.
    Ensures at least one recommendation is returned.
    Minor improvements: more trend awareness, slightly better wording
    """
    rec = []
    if df.empty:
        return ["No health data available yet — start adding records!"]

    latest = df.iloc[-1]

    # Sleep
    if latest["sleep_hours"] < 6:
        rec.append("Improve sleep — less than 6 hours today")
    elif df["sleep_hours"].mean() < 7:
        rec.append("Average sleep is low — aim for at least 7 hours daily")

    # Exercise
    if latest["exercise_minutes"] < 20:
        rec.append("Low activity today — try to increase daily movement")
    elif df["exercise_minutes"].mean() < 30:
        rec.append("Average exercise is below target — aim for 30+ min daily")

    # Sugar
    if latest["sugar_level"] > 140:
        rec.append("High blood sugar today — reduce simple sugars & refined carbs")
    elif df["sugar_level"].mean() > 130:
        rec.append("Average sugar level is elevated — monitor diet closely")

    # Blood pressure
    if latest["systolic_bp"] > 140:
        rec.append("Elevated blood pressure today — reduce salt, manage stress")
    elif df["systolic_bp"].mean() > 130:
        rec.append("Average BP is borderline high — regular monitoring advised")

    # Weight
    if latest["weight"] > 90:
        rec.append("Weight is high — consider balanced diet and regular activity")
    elif latest["weight"] < 50:
        rec.append("Weight is low — ensure adequate calorie & nutrient intake")

    # Generic fallback (slightly improved)
    if not rec:
        rec.append("Your recent readings look stable — keep up the good work and continue monitoring")

    return rec