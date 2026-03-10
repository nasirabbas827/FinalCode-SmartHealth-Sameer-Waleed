from django.contrib import admin
from .models import UserRegister , HealthRecord

# -------------------------
# UserAdmin
# -------------------------
@admin.register(UserRegister)
class UserRegisterAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'username', 'full_name', 'email', 'phone', 'created_at')
    search_fields = ('username', 'full_name', 'email', 'phone')
    list_filter = ('created_at',)
    ordering = ('-created_at',)

admin.site.register(HealthRecord)

