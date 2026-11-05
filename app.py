from functools import lru_cache
from pathlib import Path
import math

import joblib
import numpy as np
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "Datasets" / "Jio" / "Jio_Customer_Data.csv"
MODEL_PATH = BASE_DIR / "models" / "jio_churn_model.pkl"
FEATURES = [
    "Gender", "Age", "Married", "State", "Number_of_Referrals",
    "Tenure_in_Months", "Value_Deal", "Phone_Service", "Multiple_Lines",
    "Internet_Service", "Internet_Type", "Online_Security", "Online_Backup",
    "Device_Protection_Plan", "Premium_Support", "Streaming_TV",
    "Streaming_Movies", "Streaming_Music", "Unlimited_Data", "Contract",
    "Paperless_Billing", "Payment_Method", "Monthly_Charge", "Total_Charges",
    "Total_Refunds", "Total_Extra_Data_Charges", "Total_Long_Distance_Charges",
    "Total_Revenue",
]
NUMERIC_FEATURES = {
    "Age", "Number_of_Referrals", "Tenure_in_Months", "Monthly_Charge",
    "Total_Charges", "Total_Refunds", "Total_Extra_Data_Charges",
    "Total_Long_Distance_Charges", "Total_Revenue",
}
STATUS_ORDER = ["Stayed", "Churned"]


def require_submitted_features(submitted, feature_names):
    missing = [name for name in feature_names if name not in submitted]
    if missing:
        raise ValueError("Missing required form fields: " + ", ".join(missing) + ".")


def parse_numeric_value(raw, name):
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a valid number.") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    return value


def validate_numeric_step(value, name, field):
    if field.get("step") == "1" and not value.is_integer():
        raise ValueError(f"{name} must be a whole number.")


@lru_cache(maxsize=1)
def load_jio_assets():
    data = pd.read_csv(DATA_PATH, low_memory=False)
    model = joblib.load(MODEL_PATH)
    if list(model.feature_names_in_) != FEATURES:
        raise RuntimeError("The Jio model feature order does not match the dashboard form.")
    if list(model.classes_) != [0, 1]:
        raise RuntimeError("Expected Jio model output classes [0, 1].")
    return data, model


def make_charts(data):
    binary = data[data["Customer_Status"].isin(STATUS_ORDER)].copy()
    status = data["Customer_Status"].value_counts().reindex(["Churned", "Stayed", "Joined"], fill_value=0)
    contract = pd.crosstab(binary["Contract"], binary["Customer_Status"]).reindex(columns=STATUS_ORDER, fill_value=0)
    tenure_bins = [0, 6, 12, 18, 24, 30, 36]
    tenure_labels = ["1–6", "7–12", "13–18", "19–24", "25–30", "31–36"]
    binary["Tenure group"] = pd.cut(binary["Tenure_in_Months"], bins=tenure_bins, labels=tenure_labels, include_lowest=True)
    tenure = binary.groupby("Tenure group", observed=False)["Customer_Status"].agg(
        customers="size", churned=lambda s: (s == "Churned").sum()
    ).reindex(tenure_labels, fill_value=0)
    tenure_rates = [round((row.churned / row.customers * 100), 2) if row.customers else 0 for row in tenure.itertuples()]
    states = data["State"].value_counts().sort_values()
    service_cols = ["Phone_Service", "Multiple_Lines", "Internet_Service", "Online_Security", "Online_Backup", "Device_Protection_Plan", "Premium_Support", "Streaming_TV", "Streaming_Movies", "Streaming_Music", "Unlimited_Data"]
    service_names, service_rates = [], []
    for col in service_cols:
        observed = data[col].dropna()
        denom = int(observed.isin(["Yes", "No"]).sum())
        yes = int((observed == "Yes").sum())
        if denom:
            service_names.append(col.replace("_", " ").title())
            service_rates.append(round(yes / denom * 100, 1))
    revenue = data.groupby("Customer_Status")["Total_Revenue"].mean().reindex(["Stayed", "Churned", "Joined"])
    return {
        "status": {"labels": status.index.tolist(), "values": [int(x) for x in status.values]},
        "contract": {"labels": contract.index.tolist(), "stayed": [int(x) for x in contract["Stayed"]], "churned": [int(x) for x in contract["Churned"]]},
        "tenure": {"labels": tenure_labels, "rates": tenure_rates, "counts": [int(x) for x in tenure["customers"]]},
        "states": {"labels": states.index.tolist(), "values": [int(x) for x in states.values]},
        "services": {"labels": service_names, "rates": service_rates},
        "revenue": {"labels": revenue.index.tolist(), "values": [round(float(x), 2) if pd.notna(x) else 0 for x in revenue.values]},
    }


def make_form_fields(data, submitted=None):
    submitted = submitted or {}
    fields = {}
    for name in FEATURES:
        if name in NUMERIC_FEATURES:
            series = pd.to_numeric(data[name], errors="coerce").dropna()
            fields[name] = {"kind": "number", "value": submitted.get(name, str(float(series.median()))),
                            "min": float(series.min()), "max": float(series.max()),
                            "step": "1" if name in {"Age", "Number_of_Referrals", "Tenure_in_Months"} else "any"}
        else:
            values = sorted(data[name].dropna().astype(str).unique().tolist())
            if data[name].isna().any() and "Unknown" not in values:
                values.append("Unknown")
            fields[name] = {"kind": "select", "options": values, "value": submitted.get(name, "")}
    return fields


def dashboard_context(data):
    counts = data["Customer_Status"].value_counts()
    churned, stayed = int(counts.get("Churned", 0)), int(counts.get("Stayed", 0))
    joined, total = int(counts.get("Joined", 0)), int(len(data))
    binary_total = churned + stayed
    return {
        "kpis": {"total": total, "churned": churned, "stayed": stayed, "joined": joined,
                 "churn_rate": round(churned / binary_total * 100, 2) if binary_total else 0,
                 "binary_total": binary_total},
        "charts": make_charts(data),
        "fields": make_form_fields(data),
    }


@app.get("/")
def homepage():
    return render_template("index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}, 200


@app.route("/jio", methods=["GET", "POST"])
def jio_dashboard():
    data, model = load_jio_assets()
    context = dashboard_context(data)
    result = None
    error = None
    if request.method == "POST":
        submitted = request.form.to_dict()
        row = {}
        try:
            require_submitted_features(submitted, FEATURES)
            for name in FEATURES:
                raw = submitted.get(name, "").strip()
                if name in NUMERIC_FEATURES:
                    if not raw:
                        row[name] = np.nan
                    else:
                        value = parse_numeric_value(raw, name)
                        bounds = context["fields"][name]
                        validate_numeric_step(value, name, bounds)
                        if value < bounds["min"] or value > bounds["max"]:
                            raise ValueError(f"{name} must be between {bounds['min']:g} and {bounds['max']:g}, matching observed Jio data ranges.")
                        row[name] = value
                elif not raw:
                    row[name] = np.nan
                else:
                    allowed = context["fields"][name]["options"]
                    if raw not in allowed:
                        raise ValueError(f"Choose a listed value for {name}.")
                    row[name] = raw
            sample = pd.DataFrame([row], columns=FEATURES)
            predicted_class = int(model.predict(sample)[0])
            classes = list(model.classes_)
            churn_probability = float(model.predict_proba(sample)[0][classes.index(1)])
            result = {"class": predicted_class, "label": "Churned" if predicted_class == 1 else "Stayed",
                      "probability": round(churn_probability * 100, 2)}
            context["fields"] = make_form_fields(data, submitted)
        except (ValueError, TypeError) as exc:
            error = str(exc)
            context["fields"] = make_form_fields(data, submitted)
    return render_template("jio.html", **context, result=result, error=error)


AIRTEL_DATA_PATH = BASE_DIR / "Datasets" / "Airtel" / "Main_churn_data_for_tableau.csv"
AIRTEL_MODEL_PATH = BASE_DIR / "models" / "airtel_churn_model.pkl"
AIRTEL_FEATURES = [
    "gender", "age", "married", "state", "number_of_referrals",
    "tenure_in_months", "value_deal", "phone_service", "multiple_lines",
    "internet_service", "internet_type", "online_security", "online_backup",
    "device_protection_plan", "premium_support", "streaming_tv",
    "streaming_movies", "streaming_music", "unlimited_data", "contract",
    "paperless_billing", "payment_method", "monthly_charge",
]
AIRTEL_NUMERIC_FEATURES = {"age", "number_of_referrals", "tenure_in_months", "monthly_charge"}


@lru_cache(maxsize=1)
def load_airtel_assets():
    data = pd.read_csv(AIRTEL_DATA_PATH, low_memory=False)
    model = joblib.load(AIRTEL_MODEL_PATH)
    if list(model.feature_names_in_) != AIRTEL_FEATURES:
        raise RuntimeError("The Airtel model feature order does not match the dashboard form.")
    if list(model.classes_) != [0, 1]:
        raise RuntimeError("Expected Airtel model output classes [0, 1].")
    return data, model


def make_airtel_charts(data):
    status_order = ["Stayed", "Churned"]
    status = data["customer_status"].value_counts().reindex(["Churned", "Stayed", "Joined"], fill_value=0)
    binary = data[data["customer_status"].isin(status_order)].copy()
    contract = pd.crosstab(binary["contract"], binary["customer_status"]).reindex(columns=status_order, fill_value=0)
    tenure_labels = ["1–6", "7–12", "13–18", "19–24", "25–30", "31–36"]
    binary["Tenure group"] = pd.cut(binary["tenure_in_months"], bins=[0, 6, 12, 18, 24, 30, 36], labels=tenure_labels, include_lowest=True)
    tenure = binary.groupby("Tenure group", observed=False)["customer_status"].agg(
        customers="size", churned=lambda values: (values == "Churned").sum()
    ).reindex(tenure_labels, fill_value=0)
    tenure_rates = [round(row.churned / row.customers * 100, 2) if row.customers else 0 for row in tenure.itertuples()]
    states = data["state"].value_counts().sort_values()
    def service_group(row):
        if row["internet_service"] == "No":
            return "No internet service"
        if pd.isna(row["internet_type"]):
            return "Internet type missing"
        return str(row["internet_type"])
    binary["Internet group"] = binary.apply(service_group, axis=1)
    internet = pd.crosstab(binary["Internet group"], binary["customer_status"]).reindex(columns=status_order, fill_value=0)
    charges = data.groupby("customer_status")["monthly_charge"].mean().reindex(["Stayed", "Churned", "Joined"])
    revenue = data.groupby("customer_status")["total_revenue"].mean().reindex(["Stayed", "Churned", "Joined"])
    def values(series):
        return [round(float(value), 2) if pd.notna(value) else 0 for value in series.values]
    return {
        "status": {"labels": status.index.tolist(), "values": [int(value) for value in status.values]},
        "contract": {"labels": contract.index.tolist(), "stayed": [int(value) for value in contract["Stayed"]], "churned": [int(value) for value in contract["Churned"]]},
        "tenure": {"labels": tenure_labels, "rates": tenure_rates, "counts": [int(value) for value in tenure["customers"]]},
        "states": {"labels": states.index.tolist(), "values": [int(value) for value in states.values]},
        "internet": {"labels": internet.index.tolist(), "stayed": [int(value) for value in internet["Stayed"]], "churned": [int(value) for value in internet["Churned"]]},
        "charges": {"labels": charges.index.tolist(), "values": values(charges)},
        "revenue": {"labels": revenue.index.tolist(), "values": values(revenue)},
    }


def airtel_form_fields(data, submitted=None):
    submitted = submitted or {}
    fields = {}
    for name in AIRTEL_FEATURES:
        if name in AIRTEL_NUMERIC_FEATURES:
            series = pd.to_numeric(data[name], errors="coerce").dropna()
            fields[name] = {"kind": "number", "value": submitted.get(name, str(float(series.median()))),
                            "min": float(series.min()), "max": float(series.max()),
                            "step": "1" if name in {"age", "number_of_referrals", "tenure_in_months"} else "any"}
        else:
            series = data[name].dropna().astype(str)
            options = sorted(series.unique().tolist())
            default = series.mode().iloc[0] if not series.mode().empty else ""
            fields[name] = {"kind": "select", "options": options, "value": submitted.get(name, default)}
    return fields


def airtel_dashboard_context(data):
    counts = data["customer_status"].value_counts()
    churned, stayed = int(counts.get("Churned", 0)), int(counts.get("Stayed", 0))
    joined, total = int(counts.get("Joined", 0)), int(len(data))
    binary_total = churned + stayed
    monthly = pd.to_numeric(data["monthly_charge"], errors="coerce")
    return {
        "kpis": {"total": total, "churned": churned, "stayed": stayed, "joined": joined,
                 "churn_rate": round(churned / binary_total * 100, 2) if binary_total else 0,
                 "binary_total": binary_total},
        "charts": make_airtel_charts(data),
        "fields": airtel_form_fields(data),
        "quality": {"negative_monthly_rows": int(monthly.lt(0).sum()), "monthly_min": float(monthly.min()),
                    "missing_value_deal": int(data["value_deal"].isna().sum()),
                    "missing_internet_type": int(data["internet_type"].isna().sum())},
    }


@app.route("/airtel", methods=["GET", "POST"])
def airtel_dashboard():
    data, model = load_airtel_assets()
    context = airtel_dashboard_context(data)
    result = None
    error = None
    if request.method == "POST":
        submitted = request.form.to_dict()
        row = {}
        try:
            require_submitted_features(submitted, AIRTEL_FEATURES)
            for name in AIRTEL_FEATURES:
                raw = submitted.get(name, "").strip()
                if name in AIRTEL_NUMERIC_FEATURES:
                    if not raw:
                        row[name] = np.nan
                    else:
                        value = parse_numeric_value(raw, name)
                        bounds = context["fields"][name]
                        validate_numeric_step(value, name, bounds)
                        if value < bounds["min"] or value > bounds["max"]:
                            raise ValueError(f"{name} must be between {bounds['min']:g} and {bounds['max']:g}, matching observed Airtel data ranges.")
                        row[name] = value
                elif not raw:
                    row[name] = np.nan
                elif raw not in context["fields"][name]["options"]:
                    raise ValueError(f"Choose a listed value for {name}.")
                else:
                    row[name] = raw
            sample = pd.DataFrame([row], columns=AIRTEL_FEATURES)
            predicted_class = int(model.predict(sample)[0])
            churn_probability = float(model.predict_proba(sample)[0][list(model.classes_).index(1)])
            result = {"class": predicted_class, "label": "Churned" if predicted_class == 1 else "Stayed",
                      "probability": round(churn_probability * 100, 2)}
            context["fields"] = airtel_form_fields(data, submitted)
        except (ValueError, TypeError) as exc:
            error = str(exc)
            context["fields"] = airtel_form_fields(data, submitted)
    return render_template("airtel.html", **context, result=result, error=error)


NETFLIX_DATA_PATH = BASE_DIR / "Datasets" / "Netflix" / "netflix_customer_churn.csv"
NETFLIX_MODEL_PATH = BASE_DIR / "models" / "netflix_churn_model.pkl"
NETFLIX_FEATURES = [
    "age", "gender", "subscription_type", "watch_hours", "last_login_days",
    "region", "device", "monthly_fee", "payment_method", "number_of_profiles",
    "avg_watch_time_per_day", "favorite_genre",
]
NETFLIX_NUMERIC_FEATURES = {
    "age", "watch_hours", "last_login_days", "monthly_fee", "number_of_profiles",
    "avg_watch_time_per_day",
}


@lru_cache(maxsize=1)
def load_netflix_assets():
    data = pd.read_csv(NETFLIX_DATA_PATH, low_memory=False)
    model = joblib.load(NETFLIX_MODEL_PATH)
    if list(model.feature_names_in_) != NETFLIX_FEATURES:
        raise RuntimeError("The Netflix model feature order does not match the dashboard form.")
    if list(model.classes_) != [0, 1]:
        raise RuntimeError("Expected Netflix model output classes [0, 1].")
    if "churned" not in data or not set(data["churned"].dropna().unique()).issubset({0, 1}):
        raise RuntimeError("Netflix target must be a binary churned column.")
    return data, model


def make_netflix_charts(data):
    binary = data[data["churned"].isin([0, 1])].copy()
    status = data["churned"].value_counts().reindex([1, 0], fill_value=0)
    churn_label = binary["churned"].map({0: "Stayed", 1: "Churned"})
    def grouped(column):
        table = pd.crosstab(binary[column].astype(str), churn_label).reindex(columns=["Stayed", "Churned"], fill_value=0)
        return {"labels": table.index.tolist(), "stayed": table["Stayed"].astype(int).tolist(), "churned": table["Churned"].astype(int).tolist()}
    age_bins = [17, 29, 39, 49, 59, float("inf")]
    age_labels = ["18–29", "30–39", "40–49", "50–59", "60+"]
    binary["Age group"] = pd.cut(binary["age"], bins=age_bins, labels=age_labels, include_lowest=True)
    age_table = pd.crosstab(binary["Age group"], churn_label).reindex(index=age_labels, columns=["Stayed", "Churned"], fill_value=0)
    age_totals = age_table.sum(axis=1)
    age_rates = (age_table["Churned"] / age_totals.replace(0, np.nan) * 100).fillna(0)
    watch = binary.groupby(churn_label)["watch_hours"].mean().reindex(["Stayed", "Churned"])
    fee = binary.groupby(churn_label)["monthly_fee"].mean().reindex(["Stayed", "Churned"])
    return {
        "status": {"labels": ["Churned", "Stayed"], "values": [int(status.loc[1]), int(status.loc[0])]},
        "subscription": grouped("subscription_type"), "region": grouped("region"), "device": grouped("device"),
        "age": {"labels": age_labels, "rates": [round(float(v), 2) for v in age_rates], "counts": age_totals.astype(int).tolist()},
        "watch": {"labels": watch.index.tolist(), "values": [round(float(v), 2) for v in watch.values]},
        "fee": {"labels": fee.index.tolist(), "values": [round(float(v), 2) for v in fee.values]},
    }


def netflix_form_fields(data, submitted=None):
    submitted = submitted or {}
    fields = {}
    for name in NETFLIX_FEATURES:
        if name in NETFLIX_NUMERIC_FEATURES:
            series = pd.to_numeric(data[name], errors="coerce").dropna()
            fields[name] = {"kind": "number", "value": submitted.get(name, str(float(series.median()))),
                            "min": float(series.min()), "max": float(series.max()),
                            "step": "1" if name in {"age", "last_login_days", "number_of_profiles"} else "any"}
        else:
            series = data[name].dropna().astype(str)
            options = sorted(series.unique().tolist())
            fields[name] = {"kind": "select", "options": options,
                            "value": submitted.get(name, series.mode().iloc[0] if not series.mode().empty else "")}
    return fields


@app.route("/netflix", methods=["GET", "POST"])
def netflix_dashboard():
    data, model = load_netflix_assets()
    counts = data["churned"].value_counts()
    total, churned, stayed = len(data), int(counts.get(1, 0)), int(counts.get(0, 0))
    daily = pd.to_numeric(data["avg_watch_time_per_day"], errors="coerce")
    context = {
        "kpis": {"total": total, "churned": churned, "stayed": stayed, "binary_total": churned + stayed,
                 "churn_rate": round(churned / total * 100, 2) if total else 0},
        "charts": make_netflix_charts(data), "fields": netflix_form_fields(data),
        "quality": {"over_24": int(daily.gt(24).sum()), "daily_max": float(daily.max()),
                    "missing": int(data.isna().sum().sum()), "duplicates": int(data.duplicated().sum())},
    }
    result = error = None
    if request.method == "POST":
        submitted = request.form.to_dict()
        try:
            require_submitted_features(submitted, NETFLIX_FEATURES)
            row = {}
            for name in NETFLIX_FEATURES:
                raw = submitted.get(name, "").strip()
                if name in NETFLIX_NUMERIC_FEATURES:
                    if not raw:
                        row[name] = np.nan
                    else:
                        value = parse_numeric_value(raw, name)
                        bounds = context["fields"][name]
                        validate_numeric_step(value, name, bounds)
                        if value < bounds["min"] or value > bounds["max"]:
                            raise ValueError(f"{name} must be between {bounds['min']:g} and {bounds['max']:g}, matching observed Netflix data ranges.")
                        row[name] = value
                elif not raw:
                    row[name] = np.nan
                elif raw not in context["fields"][name]["options"]:
                    raise ValueError(f"Choose a listed value for {name}.")
                else:
                    row[name] = raw
            sample = pd.DataFrame([row], columns=NETFLIX_FEATURES)
            predicted = int(model.predict(sample)[0])
            probability = float(model.predict_proba(sample)[0][list(model.classes_).index(1)])
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise RuntimeError("The saved model returned an invalid probability.")
            result = {"class": predicted, "label": "Churned" if predicted == 1 else "Stayed", "probability": round(probability * 100, 2)}
        except (ValueError, TypeError) as exc:
            error = str(exc)
        context["fields"] = netflix_form_fields(data, submitted)
    return render_template("netflix.html", **context, result=result, error=error)


AMAZON_PRIME_DATA_PATH = BASE_DIR / "Datasets" / "Amazon" / "amazon_prime_users.csv"
AMAZON_PROXY_TRAIN_PATH = BASE_DIR / "Datasets" / "Amazon" / "customer_churn_dataset-training-master.csv"
AMAZON_PROXY_MODEL_PATH = BASE_DIR / "models" / "amazon_proxy_churn_model_repaired.pkl"
AMAZON_PROXY_FEATURES = [
    "Age", "Gender", "Tenure", "Usage Frequency", "Support Calls",
    "Payment Delay", "Subscription Type", "Contract Length", "Total Spend",
    "Last Interaction",
]
AMAZON_PROXY_NUMERIC_FEATURES = {
    "Age", "Tenure", "Usage Frequency", "Support Calls", "Payment Delay",
    "Total Spend", "Last Interaction",
}


@lru_cache(maxsize=1)
def load_amazon_assets():
    prime = pd.read_csv(AMAZON_PRIME_DATA_PATH, low_memory=False)
    proxy = pd.read_csv(AMAZON_PROXY_TRAIN_PATH, low_memory=False).dropna(how="all")
    model = joblib.load(AMAZON_PROXY_MODEL_PATH)
    if list(model.feature_names_in_) != AMAZON_PROXY_FEATURES:
        raise RuntimeError("The Amazon proxy model feature order does not match the prediction form.")
    if list(model.classes_) != [0, 1]:
        raise RuntimeError("Expected Amazon proxy model output classes [0, 1].")
    if "Churn" not in proxy or set(proxy["Churn"].dropna().unique()) != {0, 1}:
        raise RuntimeError("The generic proxy training target must be binary Churn (0/1).")
    return prime, proxy, model


def make_amazon_charts(data):
    def counts(column):
        series = data[column].astype(str).value_counts().sort_index()
        return {"labels": series.index.tolist(), "values": [int(v) for v in series.values]}
    start = pd.to_datetime(data["Membership Start Date"], errors="coerce")
    end = pd.to_datetime(data["Membership End Date"], errors="coerce")
    days = (end - start).dt.days.dropna()
    durations = days.value_counts().sort_index()
    support = pd.to_numeric(data["Customer Support Interactions"], errors="coerce").value_counts().sort_index()
    return {
        "plans": counts("Subscription Plan"), "payments": counts("Payment Information"),
        "renewal": counts("Renewal Status"), "devices": counts("Devices Used"),
        "usage": counts("Usage Frequency"),
        "duration": {"labels": [f"{int(v)} days" for v in durations.index], "values": [int(v) for v in durations.values]},
        "support": {"labels": [str(v) for v in support.index], "values": [int(v) for v in support.values]},
    }


def amazon_proxy_form_fields(data, submitted=None):
    submitted = submitted or {}
    fields = {}
    for name in AMAZON_PROXY_FEATURES:
        if name in AMAZON_PROXY_NUMERIC_FEATURES:
            series = pd.to_numeric(data[name], errors="coerce").dropna()
            fields[name] = {"kind": "number", "value": submitted.get(name, str(float(series.median()))),
                            "min": float(series.min()), "max": float(series.max()),
                            "step": "1" if name != "Total Spend" else "any"}
        else:
            series = data[name].dropna().astype(str)
            options = sorted(series.unique().tolist())
            fields[name] = {"kind": "select", "options": options,
                            "value": submitted.get(name, series.mode().iloc[0] if not series.mode().empty else "")}
    return fields


@app.route("/amazon", methods=["GET", "POST"])
def amazon_dashboard():
    prime, proxy, model = load_amazon_assets()
    starts = pd.to_datetime(prime["Membership Start Date"], errors="coerce")
    ends = pd.to_datetime(prime["Membership End Date"], errors="coerce")
    duration_days = (ends - starts).dt.days.dropna()
    plans = prime["Subscription Plan"].value_counts()
    renewals = prime["Renewal Status"].value_counts()
    context = {
        "kpis": {"users": int(len(prime)), "annual": int(plans.get("Annual", 0)),
                 "auto_renew": int(renewals.get("Auto-renew", 0)),
                 "duration": round(float(duration_days.mean()), 1) if not duration_days.empty else 0},
        "charts": make_amazon_charts(prime), "fields": amazon_proxy_form_fields(proxy),
        "quality": {"missing": int(prime.isna().sum().sum()), "duplicates": int(prime.duplicated().sum()),
                    "target_available": False, "duration_unique": int(duration_days.nunique())},
    }
    result = error = None
    if request.method == "POST":
        submitted = request.form.to_dict()
        try:
            require_submitted_features(submitted, AMAZON_PROXY_FEATURES)
            row = {}
            for name in AMAZON_PROXY_FEATURES:
                raw = submitted.get(name, "").strip()
                if name in AMAZON_PROXY_NUMERIC_FEATURES:
                    if not raw:
                        row[name] = np.nan
                    else:
                        value = parse_numeric_value(raw, name)
                        bounds = context["fields"][name]
                        validate_numeric_step(value, name, bounds)
                        if value < bounds["min"] or value > bounds["max"]:
                            raise ValueError(f"{name} must be between {bounds['min']:g} and {bounds['max']:g}, matching observed proxy training-data ranges.")
                        row[name] = value
                elif not raw:
                    row[name] = np.nan
                elif raw not in context["fields"][name]["options"]:
                    raise ValueError(f"Choose a listed value for {name}.")
                else:
                    row[name] = raw
            sample = pd.DataFrame([row], columns=AMAZON_PROXY_FEATURES)
            predicted = int(model.predict(sample)[0])
            probability = float(model.predict_proba(sample)[0][list(model.classes_).index(1)])
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise RuntimeError("The saved proxy model returned an invalid probability.")
            result = {"class": predicted, "label": "Churned" if predicted == 1 else "Not Churned",
                      "probability": round(probability * 100, 2)}
        except (ValueError, TypeError) as exc:
            error = str(exc)
        except Exception:
            app.logger.exception("Amazon proxy prediction failed")
            error = "The educational proxy model could not score these inputs. Check the values and try again."
        context["fields"] = amazon_proxy_form_fields(proxy, submitted)
    return render_template("amazon.html", **context, result=result, error=error)


COMPARISON_REPORTS = {
    "jio": BASE_DIR / "reports" / "jio_model_comparison.csv",
    "airtel": BASE_DIR / "reports" / "airtel_model_comparison.csv",
    "netflix": BASE_DIR / "reports" / "netflix_model_comparison.csv",
    "amazon_proxy": BASE_DIR / "reports" / "amazon_proxy_model_comparison.csv",
}


@lru_cache(maxsize=1)
def load_comparison_metrics():
    metadata = [
        {"key": "jio", "company": "Jio", "dataset": "Jio-folder dataset", "algorithm": "Random Forest",
         "report_model": "Random Forest", "accuracy_col": "Accuracy", "precision_col": "Churn Precision",
         "recall_col": "Churn Recall", "f1_col": "Churn F1-score",
         "evaluation": "Stratified 80/20 holdout; random_state=42 (workflow notebook).", "precision": 2},
        {"key": "airtel", "company": "Airtel", "dataset": "Airtel-folder dataset", "algorithm": "Logistic Regression",
         "report_model": "Logistic Regression", "accuracy_col": "accuracy", "precision_col": "churned_precision",
         "recall_col": "churned_recall", "f1_col": "churned_f1",
         "evaluation": "Stratified 80/20 holdout; 1,202 test rows; random_state=42.", "precision": 2},
        {"key": "netflix", "company": "Netflix", "dataset": "Netflix-folder dataset", "algorithm": "Random Forest",
         "report_model": "Random Forest", "accuracy_col": "accuracy", "precision_col": "churned_precision",
         "recall_col": "churned_recall", "f1_col": "churned_f1",
         "evaluation": "Stratified 80/20 holdout; 1,000 test rows; random_state=42.", "precision": 2},
        {"key": "amazon_proxy", "company": "Amazon educational proxy", "dataset": "Generic customer churn educational proxy (not Prime data)", "algorithm": "Random Forest",
         "report_model": "Random Forest", "accuracy_col": "accuracy", "precision_col": "precision_churn_1",
         "recall_col": "recall_churn_1", "f1_col": "f1_churn_1",
         "evaluation": "Stratified 80/20 holdout from generic training CSV; 88,167 holdout rows; random_state=42. Supplied testing CSV not used.", "precision": 4},
    ]
    rows = []
    for item in metadata:
        report = pd.read_csv(COMPARISON_REPORTS[item["key"]])
        if item["key"] == "jio":
            selected = report.loc[report["Model"].astype(str).eq(item["report_model"])]
        else:
            selected = report.loc[report["model"].astype(str).eq(item["report_model"])]
            if "selected_model" in selected.columns:
                marked = selected.loc[selected["selected_model"].astype(str).str.lower().eq("true")]
                if not marked.empty:
                    selected = marked
        if len(selected) != 1:
            raise RuntimeError(f"Expected one selected {item['company']} model row in its comparison report.")
        source = selected.iloc[0]
        rows.append({
            **item,
            "accuracy": float(source[item["accuracy_col"]]) * 100,
            "churn_precision": float(source[item["precision_col"]]) * 100,
            "churn_recall": float(source[item["recall_col"]]) * 100,
            "churn_f1": float(source[item["f1_col"]]) * 100,
        })
    return rows


@app.get("/comparison")
def comparison_dashboard():
    rows = load_comparison_metrics()
    best_accuracy = max(rows, key=lambda row: row["accuracy"])
    best_f1 = max(rows, key=lambda row: row["churn_f1"])
    chart_data = {
        "labels": [row["company"] for row in rows],
        "keys": [row["key"] for row in rows],
        "colors": {"jio": "#2563EB", "airtel": "#E31E35", "netflix": "#E50914", "amazon_proxy": "#0D9488"},
        "accuracy": [row["accuracy"] for row in rows],
        "precision": [row["churn_precision"] for row in rows],
        "recall": [row["churn_recall"] for row in rows],
        "f1": [row["churn_f1"] for row in rows],
    }
    return render_template("comparison.html", rows=rows, chart_data=chart_data,
                           best_accuracy=best_accuracy, best_f1=best_f1)


@lru_cache(maxsize=1)
def load_insights_data():
    return {
        "jio": pd.read_csv(DATA_PATH, low_memory=False),
        "airtel": pd.read_csv(AIRTEL_DATA_PATH, low_memory=False),
        "netflix": pd.read_csv(NETFLIX_DATA_PATH, low_memory=False),
        "amazon": pd.read_csv(AMAZON_PRIME_DATA_PATH, low_memory=False),
    }


def _insights_counts(series):
    values = series.astype("string").fillna("Missing").value_counts().sort_index()
    return {"labels": values.index.astype(str).tolist(), "values": [int(v) for v in values.values]}


def _insights_status(data, col):
    counts = data[col].value_counts().reindex(["Churned", "Stayed", "Joined"], fill_value=0)
    binary = data[data[col].isin(["Churned", "Stayed"])].copy()
    denominator = int(len(binary))
    churned = int(counts["Churned"])
    return {"labels": counts.index.tolist(), "values": [int(v) for v in counts.values],
            "binary_total": denominator, "churned": churned,
            "rate": round(churned / denominator * 100, 2) if denominator else 0}, binary


def _insights_grouped_churn(binary, column, status_col):
    tab = pd.crosstab(binary[column].astype("string").fillna("Missing"), binary[status_col])
    for status in ["Stayed", "Churned"]:
        if status not in tab.columns:
            tab[status] = 0
    tab = tab[["Stayed", "Churned"]]
    total = tab.sum(axis=1)
    rates = (tab["Churned"] / total.replace(0, np.nan) * 100).fillna(0)
    return {"labels": tab.index.astype(str).tolist(), "stayed": tab["Stayed"].astype(int).tolist(),
            "churned": tab["Churned"].astype(int).tolist(),
            "rates": [round(float(v), 2) for v in rates], "totals": total.astype(int).tolist()}


def _insights_tenure(binary, tenure_col, status_col):
    labels = ["1-6", "7-12", "13-18", "19-24", "25-30", "31-36"]
    work = binary.copy()
    work["_tenure_band"] = pd.cut(pd.to_numeric(work[tenure_col], errors="coerce"),
                                  [0, 6, 12, 18, 24, 30, 36], labels=labels, include_lowest=True)
    work = work.dropna(subset=["_tenure_band"])
    tab = pd.crosstab(work["_tenure_band"], work[status_col]).reindex(index=labels, fill_value=0)
    for status in ["Stayed", "Churned"]:
        if status not in tab:
            tab[status] = 0
    totals = tab["Stayed"] + tab["Churned"]
    rates = (tab["Churned"] / totals.replace(0, np.nan) * 100).fillna(0)
    return {"labels": labels, "rates": [round(float(v), 2) for v in rates],
            "churned": tab["Churned"].astype(int).tolist(), "totals": totals.astype(int).tolist()}


def _insights_services(binary, status_col, columns):
    labels, no_rates, yes_rates = [], [], []
    for col in columns:
        answer = binary[col].astype("string").str.strip().str.casefold()
        observed = binary.loc[answer.isin(["yes", "no"])].copy()
        answer = answer[answer.isin(["yes", "no"])]
        if observed.empty:
            continue
        group_rates = {}
        for value in ["no", "yes"]:
            mask = answer == value
            subset = observed.loc[mask]
            denom = len(subset)
            group_rates[value] = (subset[status_col].eq("Churned").sum() / denom * 100) if denom else 0
        labels.append(col.replace("_", " ").title())
        no_rates.append(round(float(group_rates["no"]), 2))
        yes_rates.append(round(float(group_rates["yes"]), 2))
    return {"labels": labels, "no_rates": no_rates, "yes_rates": yes_rates}


def _top_rate(summary):
    if not summary["labels"]:
        return {"label": "Unavailable", "rate": 0, "count": 0, "total": 0}
    idx = max(range(len(summary["labels"])), key=lambda i: summary["rates"][i])
    return {"label": summary["labels"][idx], "rate": summary["rates"][idx],
            "count": summary["churned"][idx], "total": summary["totals"][idx]}


def make_insights_context(data):
    jio, airtel, netflix, amazon = data["jio"], data["airtel"], data["netflix"], data["amazon"]
    j_status, j_binary = _insights_status(jio, "Customer_Status")
    a_status, a_binary = _insights_status(airtel, "customer_status")
    n_counts = netflix["churned"].value_counts().reindex([1, 0], fill_value=0)
    n_rate = float((netflix["churned"] == 1).mean() * 100)
    j_contract = _insights_grouped_churn(j_binary, "Contract", "Customer_Status")
    a_contract = _insights_grouped_churn(a_binary, "contract", "customer_status")
    j_tenure = _insights_tenure(j_binary, "Tenure_in_Months", "Customer_Status")
    a_tenure = _insights_tenure(a_binary, "tenure_in_months", "customer_status")
    j_services = _insights_services(j_binary, "Customer_Status", ["Phone_Service", "Internet_Service", "Online_Security", "Online_Backup", "Device_Protection_Plan", "Premium_Support", "Streaming_TV", "Streaming_Movies", "Streaming_Music", "Unlimited_Data"])
    a_services = _insights_services(a_binary, "customer_status", ["phone_service", "internet_service", "online_security", "online_backup", "device_protection_plan", "premium_support", "streaming_tv", "streaming_movies", "streaming_music", "unlimited_data"])
    charge_j = pd.to_numeric(jio["Monthly_Charge"], errors="coerce")
    charge_a = pd.to_numeric(airtel["monthly_charge"], errors="coerce")
    airtel_charge_groups = {status: charge_a.loc[airtel["customer_status"].eq(status)].dropna().tolist()
                            for status in ["Stayed", "Churned", "Joined"]}
    durations = (pd.to_datetime(amazon["Membership End Date"], errors="coerce") - pd.to_datetime(amazon["Membership Start Date"], errors="coerce")).dt.days.dropna()

    def netflix_group(column):
        tab = pd.crosstab(netflix[column].astype("string").fillna("Missing"), netflix["churned"])
        for target in [0, 1]:
            if target not in tab:
                tab[target] = 0
        tab = tab[[0, 1]]
        totals = tab.sum(axis=1)
        rates = (tab[1] / totals.replace(0, np.nan) * 100).fillna(0)
        return {"labels": tab.index.astype(str).tolist(), "stayed": tab[0].astype(int).tolist(),
                "churned": tab[1].astype(int).tolist(), "rates": [round(float(x), 2) for x in rates],
                "totals": totals.astype(int).tolist()}

    def means(df, group, col, labels):
        s = df.groupby(group)[col].mean().reindex(labels)
        return {"labels": labels, "values": [round(float(v), 2) if pd.notna(v) else None for v in s.values]}

    j_revenue = means(jio, "Customer_Status", "Total_Revenue", ["Stayed", "Churned", "Joined"])
    n_watch = means(netflix, "churned", "watch_hours", [0, 1])
    n_watch["labels"] = ["Stayed (0)", "Churned (1)"]
    n_daily = means(netflix, "churned", "avg_watch_time_per_day", [0, 1])
    n_daily["labels"] = ["Stayed (0)", "Churned (1)"]
    n_daily_points = {label: pd.to_numeric(netflix.loc[netflix["churned"].eq(target), "avg_watch_time_per_day"], errors="coerce").dropna().tolist()
                      for target, label in [(0, "Stayed (0)"), (1, "Churned (1)")]}
    n_fee = means(netflix, "churned", "monthly_fee", [0, 1])
    n_fee["labels"] = ["Stayed (0)", "Churned (1)"]
    j_contract_top, a_contract_top = _top_rate(j_contract), _top_rate(a_contract)
    j_tenure_top, a_tenure_top = _top_rate(j_tenure), _top_rate(a_tenure)
    n_sub, n_region, n_device = netflix_group("subscription_type"), netflix_group("region"), netflix_group("device")
    n_sub_top = _top_rate(n_sub)
    plan_counts = _insights_counts(amazon["Subscription Plan"])
    payment_counts = _insights_counts(amazon["Payment Information"])
    device_counts = _insights_counts(amazon["Devices Used"])
    renewal_counts = _insights_counts(amazon["Renewal Status"])
    usage_counts = _insights_counts(amazon["Usage Frequency"])
    support_counts = _insights_counts(amazon["Customer Support Interactions"])
    j_total, a_total, n_total, amazon_total = len(jio), len(airtel), len(netflix), len(amazon)
    churn_rows = j_status["churned"] + a_status["churned"] + int(n_counts.loc[1])
    all_rows = j_total + a_total + n_total + amazon_total
    context = {
        "kpis": {"records": all_rows, "churn_rows": churn_rows, "labeled_sets": 3, "prime_users": amazon_total,
                 "jio_rate": j_status["rate"], "airtel_rate": a_status["rate"], "netflix_rate": round(n_rate, 2)},
        "quality": {"jio_missing": int(jio.isna().sum().sum()), "airtel_missing": int(airtel.isna().sum().sum()),
                    "netflix_missing": int(netflix.isna().sum().sum()), "amazon_missing": int(amazon.isna().sum().sum())},
        "jio": {"total": j_total, "status": j_status, "contract": j_contract, "tenure": j_tenure,
                "services": j_services, "revenue": j_revenue, "contract_top": j_contract_top, "tenure_top": j_tenure_top,
                "revenue_churned": j_revenue["values"][1], "revenue_stayed": j_revenue["values"][0]},
        "airtel": {"total": a_total, "status": a_status, "contract": a_contract, "tenure": a_tenure,
                   "services": a_services, "charges": {"values": charge_a.dropna().tolist(), "negative": int(charge_a.lt(0).sum()), "min": float(charge_a.min())},
                   "contract_top": a_contract_top, "tenure_top": a_tenure_top, "charge_mean": round(float(charge_a.mean()), 2)},
        "netflix": {"total": n_total, "status": {"labels": ["Churned (1)", "Stayed (0)"], "values": [int(n_counts.loc[1]), int(n_counts.loc[0])]},
                    "subscription": n_sub, "region": n_region, "device": n_device, "watch": n_watch, "daily": n_daily, "fee": n_fee,
                    "subscription_top": n_sub_top, "gt24": int(pd.to_numeric(netflix["avg_watch_time_per_day"], errors="coerce").gt(24).sum()),
                    "daily_max": float(pd.to_numeric(netflix["avg_watch_time_per_day"], errors="coerce").max()),
                    "watch_churned": n_watch["values"][1], "watch_stayed": n_watch["values"][0],
                    "fee_churned": n_fee["values"][1], "fee_stayed": n_fee["values"][0]},
        "amazon": {"total": amazon_total, "plans": plan_counts, "payments": payment_counts, "devices": device_counts,
                   "renewal": renewal_counts, "usage": usage_counts, "support": support_counts,
                   "duration": {"labels": [f"{int(v)} days" for v in sorted(durations.value_counts().index)],
                                "values": [int(durations.value_counts().loc[v]) for v in sorted(durations.value_counts().index)]},
                   "duration_days": round(float(durations.mean()), 1) if not durations.empty else None,
                   "plan_top": max(zip(plan_counts["labels"], plan_counts["values"]), key=lambda x:x[1]),
                   "payment_top": max(zip(payment_counts["labels"], payment_counts["values"]), key=lambda x:x[1]),
                   "device_top": max(zip(device_counts["labels"], device_counts["values"]), key=lambda x:x[1]),
                   "renewal_auto": int(amazon["Renewal Status"].eq("Auto-renew").sum()),
                   "renewal_manual": int(amazon["Renewal Status"].eq("Manual").sum()),
                   "usage_top": max(zip(usage_counts["labels"], usage_counts["values"]), key=lambda x:x[1]),
                   "support_mean": round(float(pd.to_numeric(amazon["Customer Support Interactions"], errors="coerce").mean()), 2)},
        "charts": {},
    }
    context["charts"] = {
        "jio": {"status": j_status, "contract": j_contract, "tenure": j_tenure, "services": j_services, "revenue": j_revenue},
        "airtel": {"status": a_status, "contract": a_contract, "tenure": a_tenure, "services": a_services,
                   "charges": airtel_charge_groups},
        "netflix": {"status": context["netflix"]["status"], "subscription": n_sub, "region": n_region, "device": n_device,
                    "watch": n_watch, "daily": n_daily, "daily_points": n_daily_points, "fee": n_fee},
        "amazon": {"plans": plan_counts, "payments": payment_counts, "devices": device_counts,
                   "renewal": renewal_counts, "usage": usage_counts, "support": support_counts,
                   "duration": context["amazon"]["duration"]},
    }
    context["jio"]["service_gap"] = max(zip(j_services["labels"], j_services["no_rates"], j_services["yes_rates"]), key=lambda x: abs(x[1]-x[2]))
    context["airtel"]["service_gap"] = max(zip(a_services["labels"], a_services["no_rates"], a_services["yes_rates"]), key=lambda x: abs(x[1]-x[2]))
    return context


@app.get("/insights")
def insights_dashboard():
    return render_template("insights.html", **make_insights_context(load_insights_data()))


@app.get("/about")
def about_project():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=False)
