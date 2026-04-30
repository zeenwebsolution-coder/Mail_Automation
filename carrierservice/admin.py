from django.contrib import admin
from .models import Package

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'carrier', 'email', 'package_status', 'updated_at')
    search_fields = ('tracking_number', 'email', 'carrier')
    list_filter = ('carrier', 'package_status')
    readonly_fields = ('created_at', 'updated_at')
