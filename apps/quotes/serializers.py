from decimal import Decimal
import math
from rest_framework import serializers
from .models import Quote, QuoteMaterial, QuoteSystemStep, Order, Invoice
from apps.dtu.constants import SYSTEMS, MATERIAL_PRICES, VAT_RATE


class QuoteMaterialSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = QuoteMaterial
        fields = ['id', 'material_id', 'name', 'unit', 'quantity', 'unit_price', 'line_total']


class QuoteSystemStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteSystemStep
        fields = ['id', 'step_id', 'name', 'description', 'quantity', 'unit_price', 'total_price', 'order']


class QuoteListSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            'id', 'quote_number', 'created_at', 'status', 'valid_until',
            'project_type', 'zone', 'element', 'surface',
            'client_name', 'total', 'summary',
        ]

    def get_summary(self, obj):
        return obj.get_summary_text()


class QuoteDetailSerializer(serializers.ModelSerializer):
    materials = QuoteMaterialSerializer(many=True, read_only=True)
    system_steps = QuoteSystemStepSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            'id', 'quote_number', 'created_at', 'updated_at', 'status', 'valid_until',
            'project_type', 'zone', 'element', 'surface',
            'plafond_type', 'placo_fini',
            'finition_type', 'peinture_aspect', 'decorative_option',
            'exterieur_type', 'exterieur_finition', 'ancien_enduit',
            'system_key',
            'labor_cost', 'material_cost', 'subtotal', 'tax', 'total',
            'client_name', 'client_address', 'client_phone', 'notes',
            'materials', 'system_steps', 'summary',
        ]

    def get_summary(self, obj):
        return obj.get_summary_text()


class QuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = [
            'id',
            'project_type', 'zone', 'element', 'surface',
            'plafond_type', 'placo_fini',
            'finition_type', 'peinture_aspect', 'decorative_option',
            'exterieur_type', 'exterieur_finition', 'ancien_enduit',
            'client_name', 'client_address', 'client_phone', 'notes',
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user

        quote = Quote.objects.create(**validated_data)

        self._calculate_and_save(quote)

        return quote

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        instance.system_steps.all().delete()
        instance.materials.all().delete()
        self._calculate_and_save(instance)

        return instance

    def _calculate_and_save(self, quote):
        """Calculate costs, create system steps and materials."""
        surface = float(quote.surface)
        system_key = quote.system_key
        system_steps = SYSTEMS.get(system_key, SYSTEMS['mur_peinture'])

        labor_cost = Decimal('0')
        for idx, step in enumerate(system_steps):
            qty = step.get('quantity', 1)
            step_total = Decimal(str(step['unit_price'])) * Decimal(str(qty)) * Decimal(str(surface))
            labor_cost += step_total
            QuoteSystemStep.objects.create(
                quote=quote,
                step_id=step['id'],
                name=step['name'],
                description=step['description'],
                quantity=qty,
                unit_price=Decimal(str(step['unit_price'])),
                total_price=step_total,
                order=idx + 1,
            )

        materials = []
        material_cost = Decimal('0')
        is_ext = quote.zone == 'exterieur'

        imp_key = 'impression_ext' if is_ext else 'impression'
        imp_price = MATERIAL_PRICES[imp_key]
        impression_qty = math.ceil(surface / 10)
        materials.append({
            'material_id': imp_key,
            'name': 'Impression façade' if is_ext else 'Impression universelle',
            'unit': 'L',
            'quantity': impression_qty,
            'unit_price': imp_price,
        })
        material_cost += impression_qty * imp_price

        if is_ext:
            ext_type = quote.exterieur_type

            if ext_type in ('ancien_peinture', 'placo') and (
                ext_type == 'placo' or quote.ancien_enduit == 'avec_enduit'
            ):
                enduit_qty = math.ceil(surface * 1.5)
                materials.append({
                    'material_id': 'enduit_facade',
                    'name': 'Enduit façade',
                    'unit': 'kg',
                    'quantity': enduit_qty,
                    'unit_price': MATERIAL_PRICES['enduit_facade'],
                })
                material_cost += enduit_qty * MATERIAL_PRICES['enduit_facade']

            if ext_type == 'neuf' and quote.exterieur_finition == 'decoratif':
                deco_qty = math.ceil(surface / 4)
                materials.append({
                    'material_id': 'produit_decoratif_ext',
                    'name': 'Produit décoratif extérieur',
                    'unit': 'L',
                    'quantity': deco_qty,
                    'unit_price': MATERIAL_PRICES['produit_decoratif_ext'],
                })
                material_cost += deco_qty * MATERIAL_PRICES['produit_decoratif_ext']
            elif ext_type == 'monocouche':
                paint_qty = math.ceil((surface * 2) / 8)  
                materials.append({
                    'material_id': 'peinture_monocouche',
                    'name': 'Peinture monocouche façade',
                    'unit': 'L',
                    'quantity': paint_qty,
                    'unit_price': MATERIAL_PRICES['peinture_monocouche'],
                })
                material_cost += paint_qty * MATERIAL_PRICES['peinture_monocouche']
            else:
                paint_qty = math.ceil((surface * 2) / 10)
                materials.append({
                    'material_id': 'peinture_facade',
                    'name': 'Peinture façade',
                    'unit': 'L',
                    'quantity': paint_qty,
                    'unit_price': MATERIAL_PRICES['peinture_facade'],
                })
                material_cost += paint_qty * MATERIAL_PRICES['peinture_facade']
        else:
            if quote.element == 'plafond' and quote.plafond_type == 'placo' and not quote.placo_fini:
                enduit_qty = math.ceil(surface * 1.5)
                materials.append({
                    'material_id': 'enduit',
                    'name': 'Enduit de lissage',
                    'unit': 'kg',
                    'quantity': enduit_qty,
                    'unit_price': MATERIAL_PRICES['enduit'],
                })
                material_cost += enduit_qty * MATERIAL_PRICES['enduit']

            if quote.element == 'mur' and quote.finition_type == 'decorative':
                if quote.decorative_option == 'produit_decoratif':
                    deco_qty = math.ceil(surface / 4)
                    materials.append({
                        'material_id': 'produit_decoratif',
                        'name': 'Produit décoratif',
                        'unit': 'L',
                        'quantity': deco_qty,
                        'unit_price': MATERIAL_PRICES['produit_decoratif'],
                    })
                    material_cost += deco_qty * MATERIAL_PRICES['produit_decoratif']
                else:  
                    pp_qty = math.ceil(surface * 1.1)
                    colle_qty = math.ceil(surface / 5)
                    materials.append({
                        'material_id': 'papier_peint',
                        'name': 'Papier peint',
                        'unit': 'm²',
                        'quantity': pp_qty,
                        'unit_price': MATERIAL_PRICES['papier_peint'],
                    })
                    materials.append({
                        'material_id': 'colle',
                        'name': 'Colle papier peint',
                        'unit': 'kg',
                        'quantity': colle_qty,
                        'unit_price': MATERIAL_PRICES['colle'],
                    })
                    material_cost += pp_qty * MATERIAL_PRICES['papier_peint']
                    material_cost += colle_qty * MATERIAL_PRICES['colle']
            else:
                aspect = quote.peinture_aspect if quote.element == 'mur' else 'mat'
                paint_key = f'peinture_{aspect}'
                paint_price = MATERIAL_PRICES.get(paint_key, MATERIAL_PRICES['peinture_mat'])
                paint_qty = math.ceil((surface * 2) / 10)  
                paint_name = f"Peinture {aspect.capitalize()}"
                materials.append({
                    'material_id': paint_key,
                    'name': paint_name,
                    'unit': 'L',
                    'quantity': paint_qty,
                    'unit_price': paint_price,
                })
                material_cost += paint_qty * paint_price

        for mat in materials:
            QuoteMaterial.objects.create(quote=quote, **mat)

        subtotal = labor_cost + material_cost
        tax = subtotal * VAT_RATE
        total = subtotal + tax

        quote.labor_cost = labor_cost
        quote.material_cost = material_cost
        quote.subtotal = subtotal
        quote.tax = tax
        quote.total = total
        quote.save(update_fields=['labor_cost', 'material_cost', 'subtotal', 'tax', 'total'])


class QuoteStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['draft', 'sent', 'accepted', 'rejected', 'expired'])


class OrderListSerializer(serializers.ModelSerializer):
    quote_number = serializers.CharField(source='quote.quote_number', read_only=True)
    total = serializers.DecimalField(source='quote.total', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'quote_number', 'created_at', 'status', 'total']


class OrderDetailSerializer(serializers.ModelSerializer):
    quote = QuoteDetailSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'created_at', 'updated_at', 'status', 'quote']


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['pending', 'in_progress', 'completed', 'cancelled'])


class InvoiceListSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'order_number', 'created_at', 'status', 'total', 'due_date']


class InvoiceDetailSerializer(serializers.ModelSerializer):
    order = OrderDetailSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'created_at', 'updated_at', 'status', 'total', 'due_date', 'order']


class InvoiceStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['unpaid', 'paid', 'overdue', 'cancelled'])


class DashboardSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_quotes = serializers.IntegerField()
    active_orders = serializers.IntegerField()
    unpaid_invoices = serializers.IntegerField()
    total_quotes = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_invoices = serializers.IntegerField()
    conversion_rate = serializers.FloatField()