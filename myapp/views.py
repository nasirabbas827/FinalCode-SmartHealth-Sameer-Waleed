from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .models import UserRegister, HealthRecord
from .forms import RegisterForm, HealthRecordForm, DateRangeForm  # ← make sure DateRangeForm exists
from .health_ai import (
    prepare_dataset,
    train_models,
    detect_anomalies,
    risk_level,
    generate_recommendations
)


# ────────────────────────────────────────────────
#  Register
# ────────────────────────────────────────────────
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password_hash = form.cleaned_data['password_hash']
            user.save()
            messages.success(request, "Registration successful! Please login.")
            return redirect("login")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})


# ────────────────────────────────────────────────
#  Login
# ────────────────────────────────────────────────
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = UserRegister.objects.get(username=username)
            if check_password(password, user.password_hash):
                request.session["user_id"] = user.user_id
                request.session["username"] = user.username
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid password.")
        except UserRegister.DoesNotExist:
            messages.error(request, "User not found.")
    return render(request, "login.html")


# ────────────────────────────────────────────────
#  Logout
# ────────────────────────────────────────────────
def logout_view(request):
    request.session.flush()
    return redirect("login")


# ────────────────────────────────────────────────
#  Index / Home
# ────────────────────────────────────────────────
def index_view(request):
    return render(request, "index.html", {})


# ────────────────────────────────────────────────
#  Dashboard  
# ────────────────────────────────────────────────
def dashboard_view(request):
    if not request.session.get("user_id"):
        return redirect("index")

    user_id = request.session["user_id"]
    records = HealthRecord.objects.filter(user_id=user_id).values()
    records = list(records)

    if not records:
        return render(request, "dashboard.html", {
            "username": request.session.get("username"),
            "message": "No health data available"
        })

    df, features = prepare_dataset(records)
    diabetes_model, hypertension_model, scaler = train_models(
        features, df["diabetes_risk"], df["hypertension_risk"]
    )

    latest = df.iloc[-1]
    latest_features = pd.DataFrame([{
        "weight": latest["weight"],
        "systolic_bp": latest["systolic_bp"],
        "diastolic_bp": latest["diastolic_bp"],
        "sugar_level": latest["sugar_level"],
        "sleep_hours": latest["sleep_hours"],
        "exercise_minutes": latest["exercise_minutes"]
    }])

    X_latest = scaler.transform(latest_features)

    diabetes_prediction = diabetes_model.predict(X_latest)[0]
    hypertension_prediction = hypertension_model.predict(X_latest)[0]

    anomalies = detect_anomalies(df)
    recommendations = generate_recommendations(df)

    weight_risk = risk_level(latest["weight"], 60, 90)
    sugar_risk = risk_level(latest["sugar_level"], 120, 160)
    bp_risk = risk_level(latest["systolic_bp"], 120, 140)

    fig = px.line(
        df,
        x="date",
        y=["sugar_level", "systolic_bp"],
        title="Health Trends"
    )
    chart = fig.to_html()

    return render(request, "dashboard.html", {
        "username": request.session.get("username"),
        "diabetes_prediction": diabetes_prediction,
        "hypertension_prediction": hypertension_prediction,
        "anomalies": anomalies,
        "recommendations": recommendations,
        "weight_risk": weight_risk,
        "sugar_risk": sugar_risk,
        "bp_risk": bp_risk,
        "chart": chart
    })

# ────────────────────────────────────────────────
#  Helper: Get filtered records + date form
# ────────────────────────────────────────────────
def get_filtered_records(request, user):
    records = HealthRecord.objects.filter(user=user).order_by("date")

    form = DateRangeForm(request.GET or None)
    start_date = None
    end_date = None

    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        if start_date:
            records = records.filter(date__gte=start_date)
        if end_date:
            records = records.filter(date__lte=end_date)

    return records, form, start_date, end_date


# ────────────────────────────────────────────────
#  Health Records (list + chart + insights + date filter)
# ────────────────────────────────────────────────
def health_records_view(request):
    if not request.session.get("user_id"):
        return redirect("login")

    user = get_object_or_404(UserRegister, user_id=request.session["user_id"])
    records_qs, date_form, _, _ = get_filtered_records(request, user)

    records_list = list(records_qs.values())
    insights = {}
    chart_html = None

    if records_list:
        df, _ = prepare_dataset(records_list)

        if not df.empty:
            latest = df.iloc[-1]

            insights["weight_risk"] = risk_level(latest["weight"], 60, 90)
            insights["sugar_risk"] = risk_level(latest["sugar_level"], 120, 160)
            insights["bp_risk"] = risk_level(latest["systolic_bp"], 120, 140)
            insights["anomalies"] = detect_anomalies(df)
            insights["recommendations"] = generate_recommendations(df)

            # Better chart with more metrics
            fig = px.line(
                df,
                x="date",
                y=["weight", "sugar_level", "systolic_bp", "diastolic_bp"],
                title="Health Trends (selected period)",
                labels={"value": "Value", "variable": "Metric"},
                template="plotly_white"
            )
            fig.update_layout(legend_title_text="Health Metrics")
            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    context = {
        "records": records_qs,
        "date_form": date_form,
        "insights": insights,
        "chart": chart_html,
        "username": user.username,
    }
    return render(request, "health_records.html", context)


# ────────────────────────────────────────────────
#  Add Health Record
# ────────────────────────────────────────────────
def add_health_record(request):
    if not request.session.get("user_id"):
        return redirect("login")

    user = get_object_or_404(UserRegister, user_id=request.session["user_id"])

    if request.method == "POST":
        form = HealthRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.user = user
            record.save()
            messages.success(request, "Health record added successfully")
            return redirect("health_records")
    else:
        form = HealthRecordForm()

    return render(request, "health_form.html", {"form": form})


# ────────────────────────────────────────────────
#  Edit Health Record
# ────────────────────────────────────────────────
def edit_health_record(request, id):
    if not request.session.get("user_id"):
        return redirect("login")

    record = get_object_or_404(HealthRecord, id=id, user__user_id=request.session["user_id"])

    if request.method == "POST":
        form = HealthRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Record updated.")
            return redirect("health_records")
    else:
        form = HealthRecordForm(instance=record)

    return render(request, "health_form.html", {"form": form})


# ────────────────────────────────────────────────
#  Delete Health Record
# ────────────────────────────────────────────────
def delete_health_record(request, id):
    if not request.session.get("user_id"):
        return redirect("login")

    record = get_object_or_404(HealthRecord, id=id, user__user_id=request.session["user_id"])
    record.delete()
    messages.success(request, "Record deleted.")
    return redirect("health_records")


# ────────────────────────────────────────────────
#  Upload CSV/Excel
# ────────────────────────────────────────────────
def upload_health_data(request):
    if not request.session.get("user_id"):
        return redirect("login")

    if request.method == "POST":
        if "file" not in request.FILES:
            messages.error(request, "No file uploaded.")
            return redirect("upload_data")

        file = request.FILES["file"]

        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith((".xls", ".xlsx")):
                df = pd.read_excel(file)
            else:
                messages.error(request, "Only CSV or Excel files are allowed.")
                return redirect("upload_data")
        except Exception:
            messages.error(request, "Error reading file.")
            return redirect("upload_data")

        required = ["date", "weight", "systolic_bp", "diastolic_bp",
                    "sugar_level", "sleep_hours", "exercise_minutes", "mood"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            messages.error(request, f"Missing columns: {', '.join(missing)}")
            return redirect("upload_data")

        df = df.dropna(subset=required)
        numeric_cols = ["weight", "systolic_bp", "diastolic_bp", "sugar_level",
                        "sleep_hours", "exercise_minutes"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=numeric_cols)

        # Basic range validation
        df = df[
            (df["weight"].between(20, 500)) &
            (df["systolic_bp"].between(50, 250)) &
            (df["diastolic_bp"].between(30, 150)) &
            (df["sugar_level"].between(40, 500)) &
            (df["sleep_hours"].between(0, 24)) &
            (df["exercise_minutes"].between(0, 1440))
        ]

        user = get_object_or_404(UserRegister, user_id=request.session["user_id"])
        inserted = 0

        for _, row in df.iterrows():
            date_val = parse_date(str(row["date"]))
            if not date_val:
                continue

            HealthRecord.objects.update_or_create(
                user=user,
                date=date_val,
                defaults={
                    "weight": row["weight"],
                    "systolic_bp": row["systolic_bp"],
                    "diastolic_bp": row["diastolic_bp"],
                    "sugar_level": row["sugar_level"],
                    "sleep_hours": row["sleep_hours"],
                    "exercise_minutes": row["exercise_minutes"],
                    "mood": row["mood"],
                }
            )
            inserted += 1

        messages.success(request, f"{inserted} records processed/added.")
        return redirect("health_records")

    return render(request, "upload_data.html")


# ────────────────────────────────────────────────
#  Export CSV (with date filter support)
# ────────────────────────────────────────────────
def export_csv(request):
    if not request.session.get("user_id"):
        return redirect("login")

    user = get_object_or_404(UserRegister, user_id=request.session["user_id"])
    records_qs, _, _, _ = get_filtered_records(request, user)

    if not records_qs.exists():
        messages.warning(request, "No records found for selected period.")
        return redirect("health_records")

    df = pd.DataFrame(list(records_qs.values()))

    response = HttpResponse(content_type="text/csv")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="health_records_{ts}.csv"'
    df.to_csv(response, index=False)
    return response


# ────────────────────────────────────────────────
#  Export Excel (with date filter support)
# ────────────────────────────────────────────────
def export_excel(request):
    if not request.session.get("user_id"):
        return redirect("login")

    user = get_object_or_404(UserRegister, user_id=request.session["user_id"])
    records_qs, _, _, _ = get_filtered_records(request, user)

    if not records_qs.exists():
        messages.warning(request, "No records found for selected period.")
        return redirect("health_records")

    df = pd.DataFrame(list(records_qs.values()))

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="health_records_{ts}.xlsx"'
    df.to_excel(response, index=False, engine="openpyxl")
    return response


# ────────────────────────────────────────────────
#  Download PDF Report (daily / weekly / monthly / custom)
# ────────────────────────────────────────────────
def download_health_report(request, period="custom"):
    if not request.session.get("user_id"):
        return redirect("login")

    user = get_object_or_404(UserRegister, user_id=request.session["user_id"])

         # custom range from GET params
    records_qs, form, start, end = get_filtered_records(request, user)
    if not form.is_valid() or not (start and end):
        messages.error(request, "Please select a valid date range.")
        return redirect("health_records")
    report_title = "Custom Period Report"

    if not records_qs.exists():
        messages.error(request, "No data available for the selected period.")
        return redirect("health_records")

    df = pd.DataFrame(list(records_qs.values(
        "date", "weight", "systolic_bp", "diastolic_bp",
        "sugar_level", "sleep_hours", "exercise_minutes", "mood"
    )))
    df["date"] = pd.to_datetime(df["date"])

    # Chart
    fig = px.line(
        df.sort_values("date"),
        x="date",
        y=["weight", "sugar_level", "systolic_bp"],
        title=f"{report_title} – Health Trends",
        template="plotly_white"
    )
    img_bytes = fig.to_image(format="png", width=900, height=500)

    # PDF generation
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    w, h = letter

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, h - 60, f"{user.full_name or user.username} – {report_title}")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, h - 85, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Chart
    img = ImageReader(io.BytesIO(img_bytes))
    pdf.drawImage(img, 50, h - 420, width=500, height=300, preserveAspectRatio=True)

    # Latest values
    if not df.empty:
        latest = df.iloc[-1]
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, h - 440, "Latest / End of Period:")
        pdf.setFont("Helvetica", 11)

        y = h - 460
        metrics = [
            ("Date", latest["date"].strftime("%Y-%m-%d")),
            ("Weight", f"{latest['weight']:.1f} kg"),
            ("BP", f"{latest['systolic_bp']}/{latest['diastolic_bp']} mmHg"),
            ("Sugar", f"{latest['sugar_level']} mg/dL"),
            ("Sleep", f"{latest['sleep_hours']} hrs"),
            ("Exercise", f"{latest['exercise_minutes']} min"),
        ]
        for label, value in metrics:
            pdf.drawString(70, y, f"{label}: {value}")
            y -= 20

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"health_report_{period}_{ts}.pdf"
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response