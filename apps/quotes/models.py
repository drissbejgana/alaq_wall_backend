import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.dtu.constants import (
    PROJECT_TYPES, ZONES, ELEMENTS, PLAFOND_TYPES, FINITION_TYPES,
    PEINTURE_ASPECTS, DECORATIVE_OPTIONS, QUOTE_STATUSES, ORDER_STATUSES,
    INVOICE_STATUSES, EXTERIEUR_TYPES, EXTERIEUR_FINITIONS, ANCIEN_ENDUIT_OPTIONS,
)


class Quote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quotes'
    )
    quote_number = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=QUOTE_STATUSES, default='draft')
    valid_until = models.DateField(null=True, blank=True)

    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES, default='batiment')
    zone = models.CharField(max_length=20, choices=ZONES, default='interieur')

    element = models.CharField(max_length=20, choices=ELEMENTS, default='mur')
    surface = models.DecimalField(max_digits=10, decimal_places=2, default=0)


    plafond_type = models.CharField(max_length=20, choices=PLAFOND_TYPES, default='placo', blank=True)
    placo_fini = models.BooleanField(default=True)

    finition_type = models.CharField(max_length=20, choices=FINITION_TYPES, default='simple', blank=True)
    peinture_aspect = models.CharField(max_length=20, choices=PEINTURE_ASPECTS, default='satine', blank=True)
    decorative_option = models.CharField(max_length=20, choices=DECORATIVE_OPTIONS, default='produit_decoratif', blank=True)

    exterieur_type = models.CharField(max_length=20, choices=EXTERIEUR_TYPES, default='neuf', blank=True)
    exterieur_finition = models.CharField(max_length=20, choices=EXTERIEUR_FINITIONS, default='simple', blank=True)
    ancien_enduit = models.CharField(max_length=20, choices=ANCIEN_ENDUIT_OPTIONS, default='avec_enduit', blank=True)

    system_key = models.CharField(max_length=50, blank=True, default='')

    selected_impression = models.CharField(max_length=50, blank=True, default='pva_primer')
    selected_enduit = models.CharField(max_length=50, blank=True, default='jeton_prefix_putty')
    selected_finition = models.CharField(max_length=50, blank=True, default='')

    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    material_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    client_name = models.CharField(max_length=200, blank=True, default='')
    client_address = models.TextField(blank=True, default='')
    client_phone = models.CharField(max_length=30, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'quotes_quote'
        ordering = ['-created_at']
        verbose_name = 'Devis'
        verbose_name_plural = 'Devis'

    def __str__(self):
        return f'{self.quote_number} — {self.surface}m² {self.get_element_display()}'

    def save(self, *args, **kwargs):
        if not self.quote_number:
            ts = timezone.now().strftime('%y%m%d%H%M%S')
            self.quote_number = f'DV-{ts}'
        if not self.valid_until:
            self.valid_until = (timezone.now() + timezone.timedelta(days=30)).date()
        # Compute system key
        self.system_key = self.compute_system_key()
        super().save(*args, **kwargs)

    def compute_system_key(self):
        """Determine which system to apply based on selections."""
        if self.zone == 'exterieur':
            if self.exterieur_type == 'neuf':
                return 'ext_neuf_decoratif' if self.exterieur_finition == 'decoratif' else 'ext_neuf_simple'
            elif self.exterieur_type == 'monocouche':
                return 'ext_monocouche'
            elif self.exterieur_type == 'ancien_peinture':
                return 'ext_ancien_avec_enduit' if self.ancien_enduit == 'avec_enduit' else 'ext_ancien_sans_enduit'
            else:  # placo
                return 'ext_placo'

        # Intérieur
        if self.element == 'plafond':
            if self.plafond_type == 'placo':
                return 'plafond_placo_fini' if self.placo_fini else 'plafond_placo_non_fini'
            return 'plafond_standard'
        else:  # mur
            if self.finition_type == 'simple':
                return 'mur_peinture'
            else:
                return 'mur_papier_peint' if self.decorative_option == 'papier_peint' else 'mur_decoratif'

    def get_summary_text(self):
        """Get human-readable summary of the quote."""
        if self.zone == 'exterieur':
            ext_label = dict(EXTERIEUR_TYPES).get(self.exterieur_type, self.exterieur_type)
            text = f"Extérieur — {ext_label}"
            if self.exterieur_type == 'neuf':
                fin_label = dict(EXTERIEUR_FINITIONS).get(self.exterieur_finition, self.exterieur_finition)
                text += f" ({fin_label})"
            elif self.exterieur_type == 'ancien_peinture':
                enduit_label = dict(ANCIEN_ENDUIT_OPTIONS).get(self.ancien_enduit, self.ancien_enduit)
                text += f" ({enduit_label})"
            return text

        text = f"{self.get_element_display()} — "
        
        if self.element == 'plafond':
            type_label = dict(PLAFOND_TYPES).get(self.plafond_type, self.plafond_type)
            text += type_label
            if self.plafond_type == 'placo':
                text += ' (Fini)' if self.placo_fini else ' (Non Fini)'
        else:
            if self.finition_type == 'simple':
                aspect_label = dict(PEINTURE_ASPECTS).get(self.peinture_aspect, self.peinture_aspect)
                text += f"Peinture {aspect_label}"
            else:
                deco_label = dict(DECORATIVE_OPTIONS).get(self.decorative_option, self.decorative_option)
                text += deco_label
        
        return text


class QuoteSystemStep(models.Model):
    """System step (work operation) on a quote."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='system_steps')
    step_id = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'quotes_system_step'
        ordering = ['order']

    def __str__(self):
        return f'{self.order}. {self.name}'


class QuoteMaterial(models.Model):
    """Material line item on a quote."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='materials')
    material_id = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'quotes_material'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} x{self.quantity}'

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class Order(models.Model):
    """Order created when a quote is accepted."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders'
    )
    quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name='order')
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUSES, default='pending')

    class Meta:
        db_table = 'quotes_order'
        ordering = ['-created_at']
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'

    def __str__(self):
        return f'{self.order_number} ({self.status})'

    def save(self, *args, **kwargs):
        if not self.order_number:
            ts = timezone.now().strftime('%y%m%d%H%M%S')
            self.order_number = f'CMD-{ts}'
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """Invoice created alongside an order."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices'
    )
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=INVOICE_STATUSES, default='unpaid')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'quotes_invoice'
        ordering = ['-created_at']
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'

    def __str__(self):
        return f'{self.invoice_number} — {self.total} DH'

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            ts = timezone.now().strftime('%y%m%d%H%M%S')
            self.invoice_number = f'FAC-{ts}'
        if not self.due_date:
            self.due_date = (timezone.now() + timezone.timedelta(days=15)).date()
        super().save(*args, **kwargs)