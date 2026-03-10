from django import forms
from .models import UserRegister
from django.contrib.auth.hashers import make_password

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = UserRegister
        fields = ['full_name', 'username', 'email', 'phone', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        cleaned_data["password_hash"] = make_password(password)
        return cleaned_data


from django import forms
from .models import HealthRecord
from django.utils import timezone

class HealthRecordForm(forms.ModelForm):

    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = HealthRecord
        fields = [
            "date",
            "weight",
            "systolic_bp",
            "diastolic_bp",
            "sugar_level",
            "sleep_hours",
            "exercise_minutes",
            "mood"
        ]

    def clean_date(self):
        date = self.cleaned_data.get("date")

        if date > timezone.now().date():
            raise forms.ValidationError("Date cannot be in the future.")

        return date


    def clean_weight(self):
        weight = self.cleaned_data.get("weight")
        if weight <= 0 or weight > 500:
            raise forms.ValidationError("Weight must be between 1 and 500 kg.")
        return weight


    def clean_systolic_bp(self):
        value = self.cleaned_data.get("systolic_bp")
        if value < 50 or value > 250:
            raise forms.ValidationError("Invalid systolic BP.")
        return value


    def clean_diastolic_bp(self):
        value = self.cleaned_data.get("diastolic_bp")
        if value < 30 or value > 150:
            raise forms.ValidationError("Invalid diastolic BP.")
        return value


    def clean_sugar_level(self):
        value = self.cleaned_data.get("sugar_level")
        if value < 40 or value > 500:
            raise forms.ValidationError("Invalid sugar level.")
        return value


    def clean_sleep_hours(self):
        value = self.cleaned_data.get("sleep_hours")
        if value < 0 or value > 24:
            raise forms.ValidationError("Sleep hours must be between 0 and 24.")
        return value


    def clean_exercise_minutes(self):
        value = self.cleaned_data.get("exercise_minutes")
        if value < 0 or value > 1440:
            raise forms.ValidationError("Invalid exercise minutes.")
        return value
    


# forms.py
from django import forms

class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="From"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="To"
    )