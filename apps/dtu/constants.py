"""
DTU 59.1 Constants — Updated for new flow
"""
from decimal import Decimal

# Project Types
PROJECT_TYPES = [
    ('batiment', 'Bâtiment'),
    ('industriel', 'Industriel'),
]

# Zones
ZONES = [
    ('interieur', 'Intérieur'),
    ('exterieur', 'Extérieur'),
]

# Elements
ELEMENTS = [
    ('mur', 'Mur'),
    ('plafond', 'Plafond'),
]

# Plafond Types
PLAFOND_TYPES = [
    ('placo', 'Placo'),
    ('enduit_ciment', 'Enduit Ciment'),
    ('ancien_peinture', 'Ancien Peinturé'),
    ('platre_projete', 'Plâtre Projeté'),
]

# Finition Types (for Mur)
FINITION_TYPES = [
    ('simple', 'Simple'),
    ('decorative', 'Décorative'),
]

# Peinture Aspects (for Mur Simple)
PEINTURE_ASPECTS = [
    ('mat', 'Mat'),
    ('satine', 'Satiné'),
    ('brillant', 'Brillant'),
]

# Decorative Options (for Mur Decorative)
DECORATIVE_OPTIONS = [
    ('produit_decoratif', 'Produit Décoratif'),
    ('papier_peint', 'Papier Peint'),
]

# Extérieur Types
EXTERIEUR_TYPES = [
    ('neuf', 'Neuf'),
    ('monocouche', 'Monocouche'),
    ('ancien_peinture', 'Ancien Peinturé'),
    ('placo', 'Placo'),
]

# Extérieur Neuf Finition
EXTERIEUR_FINITIONS = [
    ('simple', 'Simple'),
    ('decoratif', 'Décoratif'),
]

# Ancien Peinturé – Enduit option
ANCIEN_ENDUIT_OPTIONS = [
    ('avec_enduit', 'Avec Enduit'),
    ('sans_enduit', 'Sans Enduit'),
]

# Legacy DTU choices (kept for backward compatibility)
PAINT_TYPES = [
    ('standard', 'Standard (Vinyle)'),
    ('washable', 'Lessivable (Satinée)'),
    ('premium', 'Premium (Haute Opacité)'),
    ('waterproof', 'Imperméable (Façade)'),
    ('decorative', 'Décorative (Effets)'),
]

DTU_LEVELS = [
    ('A', 'Niveau A — Soigné'),
    ('B', 'Niveau B — Courant'),
    ('C', 'Niveau C — Élémentaire'),
    ('D', 'Niveau D — Économique'),
]

SUBSTRATE_TYPES = [
    ('plaster', 'Plâtre'),
    ('concrete', 'Béton'),
    ('cement_render', 'Enduit ciment'),
    ('wood', 'Bois'),
    ('metal', 'Métal'),
    ('existing_paint', 'Peinture existante'),
]

WALL_CONDITIONS = [
    ('new', 'Neuf'),
    ('good', 'Bon état'),
    ('normal', 'Normal'),
    ('damaged', 'Abîmé / Ancien'),
]

QUOTE_STATUSES = [
    ('draft', 'Brouillon'),
    ('sent', 'Envoyé'),
    ('accepted', 'Accepté'),
    ('rejected', 'Refusé'),
    ('expired', 'Expiré'),
]

ORDER_STATUSES = [
    ('pending', 'En attente'),
    ('in_progress', 'En cours'),
    ('completed', 'Terminé'),
    ('cancelled', 'Annulé'),
]

INVOICE_STATUSES = [
    ('unpaid', 'Non payée'),
    ('paid', 'Payée'),
    ('overdue', 'En retard'),
    ('cancelled', 'Annulée'),
]

# Material prices (DH)
MATERIAL_PRICES = {
    'impression': Decimal('12'),
    'enduit': Decimal('8'),
    'primaire': Decimal('15'),
    'peinture_mat': Decimal('45'),
    'peinture_satine': Decimal('55'),
    'peinture_brillant': Decimal('65'),
    'produit_decoratif': Decimal('85'),
    'papier_peint': Decimal('35'),
    'colle': Decimal('12'),
    # Extérieur
    'impression_ext': Decimal('15'),
    'peinture_facade': Decimal('60'),
    'enduit_facade': Decimal('10'),
    'produit_decoratif_ext': Decimal('95'),
    'peinture_monocouche': Decimal('70'),
}

# Labor prices per m² (DH)
LABOR_PRICES = {
    'impression': Decimal('15'),
    'enduit': Decimal('35'),
    'primaire': Decimal('20'),
    'finition': Decimal('25'),
    'preparation': Decimal('20'),
    'sous_couche': Decimal('20'),
    'decoratif': Decimal('55'),
    'pose_papier': Decimal('25'),
}

# System definitions (quantity = number of passes/coats for each step)
SYSTEMS = {
    'plafond_placo_fini': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Application impression universelle', 'unit_price': 15, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe de peinture', 'unit_price': 25, 'quantity': 2},
    ],
    'plafond_placo_non_fini': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Application impression universelle', 'unit_price': 15, 'quantity': 1},
        {'id': 'enduit', 'name': "Couche d'enduit", 'description': 'Passe enduit de lissage', 'unit_price': 35, 'quantity': 2},
        {'id': 'primaire', 'name': 'Couche primaire', 'description': 'Sous-couche avant finition', 'unit_price': 20, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe de peinture', 'unit_price': 25, 'quantity': 2},
    ],
    'plafond_standard': [
        {'id': 'enduit', 'name': 'Enduit si nécessaire', 'description': 'Rebouchage et lissage', 'unit_price': 30, 'quantity': 1},
        {'id': 'sous_couche', 'name': 'Sous-couche', 'description': 'Application sous-couche', 'unit_price': 20, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe de peinture', 'unit_price': 25, 'quantity': 2},
    ],
    'mur_peinture': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Application impression', 'unit_price': 15, 'quantity': 1},
        {'id': 'sous_couche', 'name': 'Sous-couche', 'description': 'Application sous-couche', 'unit_price': 20, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe de peinture', 'unit_price': 25, 'quantity': 2},
    ],
    'mur_decoratif': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Application impression spéciale', 'unit_price': 20, 'quantity': 1},
        {'id': 'base', 'name': 'Couche de base', 'description': 'Application produit de base', 'unit_price': 35, 'quantity': 1},
        {'id': 'decoratif', 'name': 'Application décorative', 'description': 'Finition décorative', 'unit_price': 55, 'quantity': 1},
    ],
    'mur_papier_peint': [
        {'id': 'sous_couche', 'name': 'Sous-couche spéciale', 'description': 'Primaire accrochage papier peint', 'unit_price': 15, 'quantity': 1},
        {'id': 'pose', 'name': 'Pose papier peint', 'description': 'Pose et maroufflage', 'unit_price': 25, 'quantity': 1},
        {'id': 'finition', 'name': 'Finition joints', 'description': 'Ajustement et finition des joints', 'unit_price': 15, 'quantity': 1},
    ],

    # ── Extérieur systems ──
    'ext_neuf_simple': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Impression façade neuve', 'unit_price': 18, 'quantity': 1},
        {'id': 'sous_couche', 'name': 'Sous-couche', 'description': 'Sous-couche extérieure', 'unit_price': 22, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe peinture façade', 'unit_price': 28, 'quantity': 2},
    ],
    'ext_neuf_decoratif': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Impression façade neuve', 'unit_price': 18, 'quantity': 1},
        {'id': 'base', 'name': 'Couche de base', 'description': 'Application produit de base extérieur', 'unit_price': 35, 'quantity': 1},
        {'id': 'decoratif', 'name': 'Application décorative', 'description': 'Finition décorative extérieure', 'unit_price': 60, 'quantity': 1},
    ],
    'ext_monocouche': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Impression façade', 'unit_price': 18, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe monocouche', 'unit_price': 30, 'quantity': 2},
    ],
    'ext_ancien_avec_enduit': [
        # {'id': 'grattage', 'name': 'Grattage / Décapage', 'description': 'Retrait ancienne peinture écaillée', 'unit_price': 20, 'quantity': 1},
        {'id': 'enduit', 'name': "Couche d'enduit", 'description': 'Passe enduit façade', 'unit_price': 35, 'quantity': 2},
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Impression après enduit', 'unit_price': 18, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe peinture façade', 'unit_price': 28, 'quantity': 2},
    ],
    'ext_ancien_sans_enduit': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Impression façade existante', 'unit_price': 18, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe peinture façade', 'unit_price': 28, 'quantity': 2},
    ],
    'ext_placo': [
        {'id': 'impression', 'name': "Couche d'impression", 'description': 'Impression placo extérieur', 'unit_price': 18, 'quantity': 1},
        {'id': 'enduit', 'name': "Couche d'enduit", 'description': 'Passe enduit de lissage', 'unit_price': 35, 'quantity': 2},
        {'id': 'primaire', 'name': 'Couche primaire', 'description': 'Sous-couche avant finition', 'unit_price': 22, 'quantity': 1},
        {'id': 'finition', 'name': 'Couche de finition', 'description': 'Passe peinture façade', 'unit_price': 28, 'quantity': 2},
    ],
}

EXECUTION_CONDITIONS = {
    'min_temperature': 5,
    'max_humidity': 80,
    'drying_time_between_coats': 4,
    'substrate_max_moisture': 5,
}

# VAT rate
VAT_RATE = Decimal('0.20')

# Default parameters
DEFAULTS = {
    'labor_per_m2': Decimal('45'),
    'vat_rate': VAT_RATE,
}


# ─── PRODUCT CATALOG ───
# Each product belongs to a material category.
# Categories: impression, enduit, finition
# Finition products are further grouped by aspect: mat, satine, brillant

PRODUCTS = {
    'impression': [
        {
            'id': 'pva_primer',
            'name': 'PVA Primer',
            'unit': 'L',
            'coverage': 10,       # m² per liter
            'price': Decimal('12'),
        },
    ],

    'enduit': [
        {
            'id': 'jeton_prefix_putty',
            'name': 'Jotun Prefix Putty',
            'unit': 'kg',
            'coverage': 1.5,      # kg per m²
            'price': Decimal('8'),
            'default': True,
        },
        {
            'id': 'jeton_stucco',
            'name': 'Jotun Stucco',
            'unit': 'kg',
            'coverage': 1.5,
            'price': Decimal('10'),
            'default': False,
        },
    ],

    'finition': {
        'mat': [
            {
                'id': 'fenomastic_emulsion_matt',
                'name': 'Fenomastic Pure Colours Emulsion Matt',
                'tier': 'Medium',
                'unit': 'L',
                'coverage': 10,   # m² per liter per coat
                'price': Decimal('45'),
                'default': True,
            },
            {
                'id': 'fenomastic_rich_matt',
                'name': 'Fenomastic My Home Rich Matt',
                'tier': 'Premium',
                'unit': 'L',
                'coverage': 12,
                'price': Decimal('65'),
                'default': False,
            },
            {
                'id': 'fenomastic_wonderwall_lux',
                'name': 'Fenomastic Wonderwall Lux',
                'tier': 'Ultra Premium',
                'unit': 'L',
                'coverage': 14,
                'price': Decimal('85'),
                'default': False,
            },
            {
                'id': 'fenomastic_enamel_matt',
                'name': 'Fenomastic Pure Colours Enamel Matt',
                'tier': 'Enamel',
                'unit': 'L',
                'coverage': 12,
                'price': Decimal('70'),
                'default': False,
            },
        ],
        'satine': [
            {
                'id': 'fenomastic_smooth_silk',
                'name': 'Fenomastic My Home Smooth Silk',
                'tier': 'Standard',
                'unit': 'L',
                'coverage': 12,
                'price': Decimal('55'),
                'default': True,
            },
            {
                'id': 'fenomastic_enamel_semigloss',
                'name': 'Fenomastic Pure Colours Enamel Semigloss',
                'tier': 'Enamel',
                'unit': 'L',
                'coverage': 12,
                'price': Decimal('60'),
                'default': False,
            },
        ],
        'brillant': [
            {
                'id': 'fenomastic_enamel_gloss',
                'name': 'Fenomastic Pure Colours Enamel Gloss',
                'tier': 'Standard',
                'unit': 'L',
                'coverage': 12,
                'price': Decimal('65'),
                'default': True,
            },
        ],
    },
}