from decimal import Decimal
from django.db.models import Sum
from django.http import FileResponse
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Quote, Order, Invoice
from .serializers import (
    QuoteListSerializer, QuoteDetailSerializer, QuoteCreateSerializer, QuoteStatusSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderStatusSerializer,
    InvoiceListSerializer, InvoiceDetailSerializer, InvoiceStatusSerializer,
    DashboardSerializer,
)
from .pdf_generator import generate_quote_pdf
from apps.dtu.constants import SYSTEMS, MATERIAL_PRICES, VAT_RATE


class QuoteViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'element', 'project_type', 'zone']
    search_fields = ['quote_number', 'client_name']
    ordering = ['-created_at']

    def get_queryset(self):
        return Quote.objects.filter(user=self.request.user).prefetch_related('materials', 'system_steps')

    def get_serializer_class(self):
        if self.action == 'list':
            return QuoteListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return QuoteCreateSerializer
        return QuoteDetailSerializer

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        quote = self.get_object()
        serializer = QuoteStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote.status = serializer.validated_data['status']
        quote.save(update_fields=['status', 'updated_at'])
        return Response(QuoteDetailSerializer(quote).data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        quote = self.get_object()
        if quote.status == 'accepted':
            return Response({'detail': 'Déjà accepté.'}, status=status.HTTP_400_BAD_REQUEST)

        quote.status = 'accepted'
        quote.save(update_fields=['status', 'updated_at'])

        order, order_created = Order.objects.get_or_create(
            quote=quote,
            defaults={'user': request.user}
        )
        if order_created:
            Invoice.objects.create(user=request.user, order=order, total=quote.total)

        return Response({
            'quote': QuoteDetailSerializer(quote).data,
            'order': OrderDetailSerializer(order).data,
            'invoice': InvoiceDetailSerializer(order.invoice).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        original = self.get_object()
        data = {
            'project_type': original.project_type,
            'zone': original.zone,
            'element': original.element,
            'surface': original.surface,
            'plafond_type': original.plafond_type,
            'placo_fini': original.placo_fini,
            'finition_type': original.finition_type,
            'peinture_aspect': original.peinture_aspect,
            'decorative_option': original.decorative_option,
            'exterieur_type': original.exterieur_type,
            'exterieur_finition': original.exterieur_finition,
            'ancien_enduit': original.ancien_enduit,
            'client_name': original.client_name,
            'client_address': original.client_address,
            'client_phone': original.client_phone,
            'notes': original.notes,
        }
        serializer = QuoteCreateSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        new_quote = serializer.save()
        return Response(QuoteDetailSerializer(new_quote).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='pdf')
    def download_pdf(self, request, pk=None):
        """Generate and download quote as PDF."""
        quote = self.get_object()
        import os
        from django.conf import settings

        logo_path = os.path.join(settings.BASE_DIR, 'media', 'logo.png')
        pdf_buffer = generate_quote_pdf(quote, logo_path)
        
        response = FileResponse(
            pdf_buffer,
            content_type='application/pdf',
            as_attachment=True,
            filename=f'Devis_{quote.quote_number}.pdf'
        )
        return response


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering = ['-created_at']

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related('quote')

    def get_serializer_class(self):
        return OrderListSerializer if self.action == 'list' else OrderDetailSerializer

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.status = serializer.validated_data['status']
        order.save(update_fields=['status', 'updated_at'])
        return Response(OrderDetailSerializer(order).data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering = ['-created_at']

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user).select_related('order', 'order__quote')

    def get_serializer_class(self):
        return InvoiceListSerializer if self.action == 'list' else InvoiceDetailSerializer

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        invoice = self.get_object()
        serializer = InvoiceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice.status = serializer.validated_data['status']
        invoice.save(update_fields=['status', 'updated_at'])
        return Response(InvoiceDetailSerializer(invoice).data)


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        quotes = Quote.objects.filter(user=user)
        orders = Order.objects.filter(user=user)
        invoices = Invoice.objects.filter(user=user)

        total_revenue = invoices.filter(status='paid').aggregate(total=Sum('total'))['total'] or Decimal('0')
        total_quotes = quotes.count()
        total_orders = orders.count()
        conversion_rate = (total_orders / total_quotes * 100) if total_quotes > 0 else 0

        data = {
            'total_revenue': total_revenue,
            'pending_quotes': quotes.filter(status='draft').count(),
            'active_orders': orders.exclude(status='completed').count(),
            'unpaid_invoices': invoices.filter(status='unpaid').count(),
            'total_quotes': total_quotes,
            'total_orders': total_orders,
            'total_invoices': invoices.count(),
            'conversion_rate': round(conversion_rate, 1),
        }
        return Response(DashboardSerializer(data).data)


class CalculatePreviewView(APIView):
    """Calculate quote preview without saving."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        D = Decimal

        try:
            import math

            surface = D(str(data.get('surface', 0)))
            zone = data.get('zone', 'interieur')
            element = data.get('element', 'mur')
            plafond_type = data.get('plafond_type', 'placo')
            placo_fini = data.get('placo_fini', True)
            finition_type = data.get('finition_type', 'simple')
            peinture_aspect = data.get('peinture_aspect', 'satine')
            decorative_option = data.get('decorative_option', 'produit_decoratif')
            exterieur_type = data.get('exterieur_type', 'neuf')
            exterieur_finition = data.get('exterieur_finition', 'simple')
            ancien_enduit = data.get('ancien_enduit', 'avec_enduit')

            is_ext = zone == 'exterieur'

            if is_ext:
                if exterieur_type == 'neuf':
                    system_key = 'ext_neuf_decoratif' if exterieur_finition == 'decoratif' else 'ext_neuf_simple'
                elif exterieur_type == 'monocouche':
                    system_key = 'ext_monocouche'
                elif exterieur_type == 'ancien_peinture':
                    system_key = 'ext_ancien_avec_enduit' if ancien_enduit == 'avec_enduit' else 'ext_ancien_sans_enduit'
                else:
                    system_key = 'ext_placo'
            elif element == 'plafond':
                if plafond_type == 'placo':
                    system_key = 'plafond_placo_fini' if placo_fini else 'plafond_placo_non_fini'
                else:
                    system_key = 'plafond_standard'
            else:
                if finition_type == 'simple':
                    system_key = 'mur_peinture'
                else:
                    system_key = 'mur_papier_peint' if decorative_option == 'papier_peint' else 'mur_decoratif'

            system_steps = SYSTEMS.get(system_key, SYSTEMS['mur_peinture'])

            labor_cost = D('0')
            steps_output = []
            for idx, step in enumerate(system_steps):
                qty = step.get('quantity', 1)
                step_total = D(str(step['unit_price'])) * D(str(qty)) * surface
                labor_cost += step_total
                steps_output.append({
                    'id': step['id'],
                    'name': step['name'],
                    'description': step['description'],
                    'quantity': qty,
                    'unit_price': float(step['unit_price']),
                    'total_price': float(step_total),
                    'order': idx + 1,
                })

            materials = []
            material_cost = D('0')

            imp_key = 'impression_ext' if is_ext else 'impression'
            imp_price = MATERIAL_PRICES[imp_key]
            impression_qty = math.ceil(float(surface) / 10)
            materials.append({
                'material_id': imp_key,
                'name': 'Impression façade' if is_ext else 'Impression universelle',
                'unit': 'L',
                'quantity': impression_qty,
                'unit_price': float(imp_price),
            })
            material_cost += impression_qty * imp_price

            if is_ext:
                if exterieur_type in ('ancien_peinture', 'placo') and (
                    exterieur_type == 'placo' or ancien_enduit == 'avec_enduit'
                ):
                    enduit_qty = math.ceil(float(surface) * 1.5)
                    materials.append({
                        'material_id': 'enduit_facade',
                        'name': 'Enduit façade',
                        'unit': 'kg',
                        'quantity': enduit_qty,
                        'unit_price': float(MATERIAL_PRICES['enduit_facade']),
                    })
                    material_cost += enduit_qty * MATERIAL_PRICES['enduit_facade']

                if exterieur_type == 'neuf' and exterieur_finition == 'decoratif':
                    deco_qty = math.ceil(float(surface) / 4)
                    materials.append({
                        'material_id': 'produit_decoratif_ext',
                        'name': 'Produit décoratif extérieur',
                        'unit': 'L',
                        'quantity': deco_qty,
                        'unit_price': float(MATERIAL_PRICES['produit_decoratif_ext']),
                    })
                    material_cost += deco_qty * MATERIAL_PRICES['produit_decoratif_ext']
                elif exterieur_type == 'monocouche':
                    paint_qty = math.ceil((float(surface) * 2) / 8)
                    materials.append({
                        'material_id': 'peinture_monocouche',
                        'name': 'Peinture monocouche façade',
                        'unit': 'L',
                        'quantity': paint_qty,
                        'unit_price': float(MATERIAL_PRICES['peinture_monocouche']),
                    })
                    material_cost += paint_qty * MATERIAL_PRICES['peinture_monocouche']
                else:
                    paint_qty = math.ceil((float(surface) * 2) / 10)
                    materials.append({
                        'material_id': 'peinture_facade',
                        'name': 'Peinture façade',
                        'unit': 'L',
                        'quantity': paint_qty,
                        'unit_price': float(MATERIAL_PRICES['peinture_facade']),
                    })
                    material_cost += paint_qty * MATERIAL_PRICES['peinture_facade']
            else:
                if element == 'plafond' and plafond_type == 'placo' and not placo_fini:
                    enduit_qty = math.ceil(float(surface) * 1.5)
                    materials.append({
                        'material_id': 'enduit',
                        'name': 'Enduit de lissage',
                        'unit': 'kg',
                        'quantity': enduit_qty,
                        'unit_price': float(MATERIAL_PRICES['enduit']),
                    })
                    material_cost += enduit_qty * MATERIAL_PRICES['enduit']

                if element == 'mur' and finition_type == 'decorative':
                    if decorative_option == 'produit_decoratif':
                        deco_qty = math.ceil(float(surface) / 4)
                        materials.append({
                            'material_id': 'produit_decoratif',
                            'name': 'Produit décoratif',
                            'unit': 'L',
                            'quantity': deco_qty,
                            'unit_price': float(MATERIAL_PRICES['produit_decoratif']),
                        })
                        material_cost += deco_qty * MATERIAL_PRICES['produit_decoratif']
                    else:
                        pp_qty = math.ceil(float(surface) * 1.1)
                        colle_qty = math.ceil(float(surface) / 5)
                        materials.append({
                            'material_id': 'papier_peint',
                            'name': 'Papier peint',
                            'unit': 'm²',
                            'quantity': pp_qty,
                            'unit_price': float(MATERIAL_PRICES['papier_peint']),
                        })
                        materials.append({
                            'material_id': 'colle',
                            'name': 'Colle papier peint',
                            'unit': 'kg',
                            'quantity': colle_qty,
                            'unit_price': float(MATERIAL_PRICES['colle']),
                        })
                        material_cost += pp_qty * MATERIAL_PRICES['papier_peint'] + colle_qty * MATERIAL_PRICES['colle']
                else:
                    aspect = peinture_aspect if element == 'mur' else 'mat'
                    paint_key = f'peinture_{aspect}'
                    paint_price = MATERIAL_PRICES.get(paint_key, MATERIAL_PRICES['peinture_mat'])
                    paint_qty = math.ceil((float(surface) * 2) / 10)
                    materials.append({
                        'material_id': paint_key,
                        'name': f'Peinture {aspect.capitalize()}',
                        'unit': 'L',
                        'quantity': paint_qty,
                        'unit_price': float(paint_price),
                    })
                    material_cost += paint_qty * paint_price

            subtotal = labor_cost + material_cost
            tax = subtotal * VAT_RATE
            total = subtotal + tax

            return Response({
                'system_key': system_key,
                'system_steps': steps_output,
                'materials': materials,
                'costs': {
                    'labor_cost': float(labor_cost),
                    'material_cost': float(material_cost),
                    'subtotal': float(subtotal),
                    'tax': float(tax),
                    'total': float(total),
                },
            })

        except (ValueError, TypeError, KeyError) as e:
            return Response({'detail': f'Erreur: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)