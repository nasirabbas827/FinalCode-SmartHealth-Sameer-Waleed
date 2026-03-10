from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("", views.index_view, name="index"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),
    path("health-records/", views.health_records_view, name="health_records"),
    path("add-record/", views.add_health_record, name="add_health_record"),
    path("edit-record/<int:id>/", views.edit_health_record, name="edit_health_record"),
    path("delete-record/<int:id>/", views.delete_health_record, name="delete_health_record"),
    path("upload-data/", views.upload_health_data, name="upload_data"),
    path("export-csv/", views.export_csv, name="export_csv"),
    path("export-excel/", views.export_excel, name="export_excel"),
    path("download_report/<str:period>/", views.download_health_report, name="download_report"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)