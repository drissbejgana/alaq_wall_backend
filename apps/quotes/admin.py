from django.contrib import admin
from .models import Quote, QuoteMaterial, QuoteSystemStep, Order, Invoice


class QuoteSystemStepInline(admin.TabularInline):
    model = QuoteSystemStep
    extra = 0
    readonly_fields = ['step_id', 'name', 'description', 'unit_price', 'total_price', 'order']


class QuoteMaterialInline(admin.TabularInline):
    model = QuoteMaterial
    extra = 0
    readonly_fields = ['material_id', 'name', 'unit', 'quantity', 'unit_price']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_number', 'user', 'element', 'surface', 'total', 'status', 'created_at']
    list_filter = ['status', 'element', 'project_type', 'zone', 'created_at']
    search_fields = ['quote_number', 'client_name', 'user__username']
    readonly_fields = ['quote_number', 'system_key', 'labor_cost', 'material_cost', 'subtotal', 'tax', 'total', 'created_at', 'updated_at']
    inlines = [QuoteSystemStepInline, QuoteMaterialInline]
    
    fieldsets = (
        ('Informations', {
            'fields': ('quote_number', 'user', 'status', 'valid_until', 'created_at', 'updated_at')
        }),
        ('Projet', {
            'fields': ('project_type', 'zone', 'element', 'surface')
        }),
        ('Options Plafond', {
            'fields': ('plafond_type', 'placo_fini'),
            'classes': ('collapse',),
        }),
        ('Options Mur', {
            'fields': ('finition_type', 'peinture_aspect', 'decorative_option'),
            'classes': ('collapse',),
        }),
        ('Système', {
            'fields': ('system_key',),
        }),
        ('Coûts', {
            'fields': ('labor_cost', 'material_cost', 'subtotal', 'tax', 'total'),
        }),
        ('Client', {
            'fields': ('client_name', 'client_phone', 'client_address', 'notes'),
        }),
    )


@admin.register(QuoteMaterial)
class QuoteMaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'quote', 'quantity', 'unit', 'unit_price']
    list_filter = ['unit']
    search_fields = ['name', 'quote__quote_number']


@admin.register(QuoteSystemStep)
class QuoteSystemStepAdmin(admin.ModelAdmin):
    list_display = ['name', 'quote', 'order', 'unit_price', 'total_price']
    list_filter = ['step_id']
    search_fields = ['name', 'quote__quote_number']
    ordering = ['quote', 'order']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'quote', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'quote__quote_number', 'user__username']
    readonly_fields = ['order_number', 'created_at', 'updated_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'user', 'order', 'total', 'status', 'due_date']
    list_filter = ['status', 'created_at', 'due_date']
    search_fields = ['invoice_number', 'order__order_number', 'user__username']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']