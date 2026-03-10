from django.db import models
from django.utils import timezone


class UserRegister(models.Model):
    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username


class HealthRecord(models.Model):
    user = models.ForeignKey(UserRegister, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)

    weight = models.FloatField()
    systolic_bp = models.IntegerField()
    diastolic_bp = models.IntegerField()
    sugar_level = models.FloatField()
    sleep_hours = models.FloatField()
    exercise_minutes = models.IntegerField()
    mood = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"