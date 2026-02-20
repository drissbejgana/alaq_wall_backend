from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'company_name', 'city', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'city')
    search_fields = ('username', 'email', 'company_name', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations Professionnelles', {
            'fields': ('company_name', 'phone', 'city', 'siret'),
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations Professionnelles', {
            'fields': ('company_name', 'phone', 'city', 'siret'),
        }),
    )