"""
Occupation Categories - Central configuration for profession-specific forecasting
"""

OCCUPATION_CATEGORIES = {
    "restaurateur": {
        "name": "Restaurateur",
        "description": "Restaurants, cafés, pizzerias, fast-food",
        "subcategories": [
            "Fast-food / Quick service",
            "Café / Brasserie",
            "Pizzeria",
            "Restaurant classique",
            "Crêperie",
            "Salon de thé",
            "Food truck / Catering"
        ],
        "default_forecast_period": 30,
        "default_alert_threshold": 0.2,
        "forecasting_config": {
            "seasonality": "weekly",
            "min_data_points": 30,
            "forecast_horizon": 30,
            "alert_sensitivity": "high"
        },
        "business_metrics": {
            "peak_days": ["Friday", "Saturday", "Sunday"],
            "slow_days": ["Monday", "Tuesday"],
            "seasonality_factor": 1.5,
            "peak_season": "Summer"
        },
        "key_products": [
            "Fruits et légumes frais",
            "Viande et poisson",
            "Produits laitiers",
            "Boissons",
            "Condiments et épices",
            "Emballages"
        ]
    },
    
    "paysagiste_pepinieriste": {
        "name": "Paysagiste / Pépiniériste",
        "description": "Gardening, landscaping, plant nurseries",
        "subcategories": [
            "Entreprise paysagère",
            "Pépinière",
            "Arboretum",
            "Paysagiste-conseil",
            "Vente de fleurs/plantes"
        ],
        "default_forecast_period": 90,
        "default_alert_threshold": 0.15,
        "forecasting_config": {
            "seasonality": "monthly",
            "min_data_points": 90,
            "forecast_horizon": 90,
            "alert_sensitivity": "medium"
        },
        "business_metrics": {
            "peak_season": ["March", "April", "May", "September"],
            "slow_season": ["November", "December", "January", "February"],
            "seasonality_factor": 3.0,
            "peak_days": []
        },
        "key_products": [
            "Plants et fleurs",
            "Seeds et engrais",
            "Garden tools",
            "Terreau et mulch",
            "Pesticides/traitements",
            "Équipements d'irrigation"
        ]
    },
    
    "pharmacie": {
        "name": "Pharmacie / Parapharmacie",
        "description": "Pharmacies and para-pharmacies",
        "subcategories": [
            "Pharmacie classique",
            "Parapharmacie",
            "Pharmacie d'urgence",
            "Point de vente spécialisé"
        ],
        "default_forecast_period": 60,
        "default_alert_threshold": 0.1,
        "forecasting_config": {
            "seasonality": "monthly",
            "min_data_points": 60,
            "forecast_horizon": 60,
            "alert_sensitivity": "high"
        },
        "business_metrics": {
            "peak_season": ["October", "November", "December", "March", "April"],
            "slow_season": ["July", "August"],
            "seasonality_factor": 1.8,
            "peak_days": []
        },
        "key_products": [
            "Médicaments OTC",
            "Compléments alimentaires",
            "Cosmétiques",
            "Articles de parapharmacie",
            "Tests et diagnostics"
        ]
    },
    
    "boulangerie_patisserie": {
        "name": "Boulangerie / Pâtisserie",
        "description": "Bakeries and pastry shops",
        "subcategories": [
            "Boulangerie traditionnelle",
            "Pâtisserie artisanale",
            "Boulangerie-pâtisserie",
            "Viennoiserie"
        ],
        "default_forecast_period": 14,
        "default_alert_threshold": 0.25,
        "forecasting_config": {
            "seasonality": "daily",
            "min_data_points": 14,
            "forecast_horizon": 14,
            "alert_sensitivity": "high"
        },
        "business_metrics": {
            "peak_days": ["Friday", "Saturday", "Sunday"],
            "slow_days": ["Monday"],
            "seasonality_factor": 2.2,
            "peak_season": "Holidays (Christmas, Easter)"
        },
        "key_products": [
            "Farine et grains",
            "Levain et levures",
            "Beurre et œufs",
            "Sucre et miel",
            "Fruits frais",
            "Emballages alimentaires"
        ]
    },
    
    "hotel_restaurant": {
        "name": "Hôtel / Hôtel-Restaurant",
        "description": "Hotels with food and beverage services",
        "subcategories": [
            "Hôtel avec restaurant",
            "Hôtel sans restauration",
            "Resort",
            "Auberge"
        ],
        "default_forecast_period": 30,
        "default_alert_threshold": 0.18,
        "forecasting_config": {
            "seasonality": "mixed",
            "min_data_points": 60,
            "forecast_horizon": 30,
            "alert_sensitivity": "medium"
        },
        "business_metrics": {
            "peak_season": ["April", "May", "June", "July", "August", "September"],
            "slow_season": ["November", "December"],
            "seasonality_factor": 2.5,
            "peak_days": ["Friday", "Saturday", "Sunday"]
        },
        "key_products": [
            "Provisions alimentaires",
            "Boissons",
            "Linge de lit",
            "Produits de nettoyage",
            "Équipement hôtelier"
        ]
    },
    
    "fleuriste": {
        "name": "Fleuriste",
        "description": "Flower shops and florists",
        "subcategories": [
            "Fleuriste indépendant",
            "Fleuriste en ligne",
            "Fleuriste événementiel",
            "Grossiste fleurs"
        ],
        "default_forecast_period": 7,
        "default_alert_threshold": 0.3,
        "forecasting_config": {
            "seasonality": "mixed",
            "min_data_points": 30,
            "forecast_horizon": 7,
            "alert_sensitivity": "very_high"
        },
        "business_metrics": {
            "peak_days": ["Friday", "Saturday"],
            "peak_dates": ["Valentine's Day", "Mother's Day", "Christmas"],
            "seasonality_factor": 4.0,
            "perishable": True
        },
        "key_products": [
            "Fleurs fraîches",
            "Plantes en pot",
            "Accessoires floraux",
            "Emballages",
            "Engrais et activateurs"
        ]
    },
    
    "vente_retail": {
        "name": "Magasin Retail Généraliste",
        "description": "General retail stores and supermarkets",
        "subcategories": [
            "Supermarché",
            "Magasin de proximité",
            "Magasin spécialisé",
            "Hypermarché"
        ],
        "default_forecast_period": 30,
        "default_alert_threshold": 0.15,
        "forecasting_config": {
            "seasonality": "weekly",
            "min_data_points": 30,
            "forecast_horizon": 30,
            "alert_sensitivity": "medium"
        },
        "business_metrics": {
            "peak_days": ["Friday", "Saturday", "Sunday"],
            "slow_days": ["Monday", "Tuesday"],
            "seasonality_factor": 1.6,
            "peak_season": "Christmas, Back-to-School"
        },
        "key_products": [
            "Articles alimentaires",
            "Électroménager",
            "Électronique",
            "Habillement",
            "Articles de maison"
        ]
    },
    
    "fitness_wellness": {
        "name": "Fitness / Wellness / Spa",
        "description": "Gyms, fitness centers, wellness and spa services",
        "subcategories": [
            "Salle de fitness",
            "Yoga studio",
            "Spa / Wellness center",
            "Piscine / Aquagym"
        ],
        "default_forecast_period": 30,
        "default_alert_threshold": 0.2,
        "forecasting_config": {
            "seasonality": "monthly",
            "min_data_points": 60,
            "forecast_horizon": 30,
            "alert_sensitivity": "medium"
        },
        "business_metrics": {
            "peak_season": ["January", "September"],
            "slow_season": ["July", "August"],
            "seasonality_factor": 2.0,
            "peak_days": ["Monday", "Tuesday", "Thursday", "Friday"]
        },
        "key_products": [
            "Equipment maintenance",
            "Supplies and materials",
            "Energy drinks",
            "Towels and accessories",
            "Cleaning products"
        ]
    },
    
    "veterinaire": {
        "name": "Cabinet Vétérinaire",
        "description": "Veterinary clinics and animal hospitals",
        "subcategories": [
            "Cabinet vétérinaire",
            "Clinique vétérinaire",
            "Urgences vétérinaires",
            "Grooming / Toilettage"
        ],
        "default_forecast_period": 30,
        "default_alert_threshold": 0.12,
        "forecasting_config": {
            "seasonality": "monthly",
            "min_data_points": 60,
            "forecast_horizon": 30,
            "alert_sensitivity": "medium"
        },
        "business_metrics": {
            "peak_season": ["Spring", "Fall"],
            "slow_season": ["August"],
            "seasonality_factor": 1.7,
            "peak_days": []
        },
        "key_products": [
            "Médicaments vétérinaires",
            "Food animale",
            "Consommables médicaux",
            "Équipement diagnostique",
            "Produits d'hygiène"
        ]
    }
}


def get_occupation_list():
    """Get list of all occupations"""
    return [
        {
            "key": key,
            "name": config["name"],
            "description": config["description"],
            "subcategories": config.get("subcategories", [])
        }
        for key, config in OCCUPATION_CATEGORIES.items()
    ]


def get_occupation_config(occupation_key):
    """Get full configuration for an occupation"""
    return OCCUPATION_CATEGORIES.get(occupation_key)


def validate_occupation(occupation_key):
    """Validate if occupation exists"""
    return occupation_key in OCCUPATION_CATEGORIES


def get_occupation_forecast_config(occupation_key):
    """Get only forecast configuration"""
    config = OCCUPATION_CATEGORIES.get(occupation_key)
    if not config:
        return None
    
    return {
        "default_forecast_period": config["default_forecast_period"],
        "default_alert_threshold": config["default_alert_threshold"],
        "forecasting_config": config["forecasting_config"]
    }


def get_occupation_business_metrics(occupation_key):
    """Get only business metrics"""
    config = OCCUPATION_CATEGORIES.get(occupation_key)
    if not config:
        return None
    
    return config.get("business_metrics", {})
