"""
DTU Reference Views — Updated for new flow
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from .constants import (
    SYSTEMS, MATERIAL_PRICES, LABOR_PRICES,
    PLAFOND_TYPES, FINITION_TYPES, PEINTURE_ASPECTS, DECORATIVE_OPTIONS,
    ELEMENTS, PROJECT_TYPES, ZONES, VAT_RATE, DEFAULTS,
    EXTERIEUR_TYPES, EXTERIEUR_FINITIONS, ANCIEN_ENDUIT_OPTIONS,
)


class DTUReferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'project_types': [{'value': v, 'label': l} for v, l in PROJECT_TYPES],
            'zones': [{'value': v, 'label': l} for v, l in ZONES],
            'elements': [{'value': v, 'label': l} for v, l in ELEMENTS],
            'plafond_types': [{'value': v, 'label': l} for v, l in PLAFOND_TYPES],
            'finition_types': [{'value': v, 'label': l} for v, l in FINITION_TYPES],
            'peinture_aspects': [{'value': v, 'label': l} for v, l in PEINTURE_ASPECTS],
            'decorative_options': [{'value': v, 'label': l} for v, l in DECORATIVE_OPTIONS],
            'exterieur_types': [{'value': v, 'label': l} for v, l in EXTERIEUR_TYPES],
            'exterieur_finitions': [{'value': v, 'label': l} for v, l in EXTERIEUR_FINITIONS],
            'ancien_enduit_options': [{'value': v, 'label': l} for v, l in ANCIEN_ENDUIT_OPTIONS],
            'systems': {k: v for k, v in SYSTEMS.items()},
            'material_prices': {k: float(v) for k, v in MATERIAL_PRICES.items()},
            'labor_prices': {k: float(v) for k, v in LABOR_PRICES.items()},
            'defaults': {
                'vat_rate': float(VAT_RATE),
                'labor_per_m2': float(DEFAULTS['labor_per_m2']),
            },
        })


class SystemPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        zone = request.query_params.get('zone', 'interieur')
        element = request.query_params.get('element', 'mur')
        plafond_type = request.query_params.get('plafond_type', 'placo')
        placo_fini = request.query_params.get('placo_fini', 'true').lower() == 'true'
        finition_type = request.query_params.get('finition_type', 'simple')
        decorative_option = request.query_params.get('decorative_option', 'produit_decoratif')
        exterieur_type = request.query_params.get('exterieur_type', 'neuf')
        exterieur_finition = request.query_params.get('exterieur_finition', 'simple')
        ancien_enduit = request.query_params.get('ancien_enduit', 'avec_enduit')

        if zone == 'exterieur':
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

        system = SYSTEMS.get(system_key, SYSTEMS['mur_peinture'])

        return Response({
            'system_key': system_key,
            'steps': system,
        })