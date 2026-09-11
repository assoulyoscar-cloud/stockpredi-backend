/**
 * CONFIGURATION MÉTIER AVANCÉE - StockPredi
 * Paramètres détaillés par secteur pour anticipation intelligente
 * Inclut: saisons, congés, effectif, événements spéciaux
 */

export const SECTOR_CONFIGS = {
  general: {
    label: "Général",
    description: "Configuration standard multi-secteur",
    icon: "📦",
    // Paramètres base
    logistics: {
      perissable: 30,        // % produits périssables
      saisonnalite: 50,      // intensité saisonnalité
      marge_securite: 20,    // % buffer stock
      tolerance_rupture: 30, // % ruptures acceptées
    },
    // SAISONS: mois 1-12, impact -100% à +100% sur demande
    seasons: {
      1: { name: "Janvier", impact: -20, description: "Post-fêtes, reprise lente" },
      2: { name: "Février", impact: -10, description: "Hiver, demande faible" },
      3: { name: "Mars", impact: 0, description: "Printemps, stabilisation" },
      4: { name: "Avril", impact: 15, description: "Pâques, pic léger" },
      5: { name: "Mai", impact: 10, description: "Printemps, stable" },
      6: { name: "Juin", impact: 5, description: "Pré-estival" },
      7: { name: "Juillet", impact: 30, description: "Vacances, pic consommation" },
      8: { name: "Août", impact: 25, description: "Vacances continues" },
      9: { name: "Septembre", impact: 0, description: "Rentrée, stable" },
      10: { name: "Octobre", impact: -5, description: "Automne calme" },
      11: { name: "Novembre", impact: 40, description: "Black Friday, Noël pré-pic" },
      12: { name: "Décembre", impact: 80, description: "Noël, pic maximal" },
    },
    // CONGÉS: périodes de fermeture/ralentissement
    holidays: [
      { name: "Noël/Jour An", startMonth: 12, startDay: 20, endMonth: 1, endDay: 5, impact: 60 }, // % réduction demande
      { name: "Été (optional)", startMonth: 7, startDay: 15, endMonth: 8, endDay: 31, impact: 0 }, // fermé = impact 0
      { name: "Pâques", startMonth: 4, startDay: 1, endMonth: 4, endDay: 15, impact: 20 },
    ],
    // RH: EFFECTIF et absentéisme
    hr: {
      base_staff: 10,              // nombre collaborateurs de base
      absenteeism_avg: 5,          // % absentéisme moyen annuel
      seasonal_hiring_months: [6,7,8,11,12], // mois d'embauche saisonnière
      vacation_risk_months: [7,8], // mois risque congés
      training_impact_pct: 10,     // % productivité réduite en formation
    },
    // ÉVÉNEMENTS SPÉCIAUX
    special_events: [
      { name: "Soldes été", month: 7, impact: -30 },     // réduction prix = volume ↑
      { name: "Soldes hiver", month: 1, impact: -30 },
    ],
    // FACTEURS EXTERNES
    external_factors: {
      weather_sensitivity: 20,    // % impact météo
      economic_cycles: "none",     // impact cycles éco
      competitor_risk: 10,         // % risque concurrence saisonnière
    },
  },

  restaurant: {
    label: "Restaurant / Traiteur",
    description: "Hospitality: gestion repas, stocks très périssables",
    icon: "🍽️",
    logistics: {
      perissable: 95,
      saisonnalite: 75,
      marge_securite: 12,
      tolerance_rupture: 8,
    },
    seasons: {
      1: { name: "Janvier", impact: -40, description: "Post-fêtes, clients diète" },
      2: { name: "Février", impact: -30, description: "Hiver + St-Valentin (pic)" },
      3: { name: "Mars", impact: -10, description: "Carême, printemps lent" },
      4: { name: "Avril", impact: 15, description: "Pâques, terrasses ouvertes" },
      5: { name: "Mai", impact: 25, description: "Beau temps, weekends ++" },
      6: { name: "Juin", impact: 35, description: "Été, tourisme commence" },
      7: { name: "Juillet", impact: 50, description: "Vacances, pics midi/soir" },
      8: { name: "Août", impact: 45, description: "Vacances, mais quelques fermetures" },
      9: { name: "Septembre", impact: -20, description: "Rentrée, clients en routine" },
      10: { name: "Octobre", impact: -10, description: "Automne calme" },
      11: { name: "Novembre", impact: 30, description: "Thanksgiving, Black Friday" },
      12: { name: "Décembre", impact: 70, description: "Noël, réveillons, fêtes d'entreprise" },
    },
    holidays: [
      { name: "Noël/Jour An", startMonth: 12, startDay: 20, endMonth: 1, endDay: 5, impact: 0 },  // Fermé
      { name: "Été fermeture", startMonth: 7, startDay: 15, endMonth: 8, endDay: 31, impact: -100 }, // Fermeture 2-3 semaines
      { name: "Pâques", startMonth: 4, startDay: 1, endMonth: 4, endDay: 15, impact: 40 },
    ],
    hr: {
      base_staff: 15,
      absenteeism_avg: 8,
      seasonal_hiring_months: [5,6,7,8,11,12],
      vacation_risk_months: [7,8],
      training_impact_pct: 15,
    },
    special_events: [
      { name: "Saint-Valentin", month: 2, impact: 60 },
      { name: "Mère-Grand", month: 5, impact: 45 },
      { name: "Mariages (juin-sept)", month: 6, impact: 80 },
      { name: "Réveillon Noël", month: 12, impact: 200 },
    ],
    external_factors: {
      weather_sensitivity: 45,    // Très sensible: beau temps = terrasse remplie
      economic_cycles: "high",     // Dépense loisir = économie
      competitor_risk: 30,         // Compétition saisonnière forte
      tourist_season: [6,7,8,9],   // Mois tourisme
    },
  },

  boulangerie: {
    label: "Boulangerie / Pâtisserie",
    description: "Ultra-périssable: vente jour-même obligatoire",
    icon: "🥐",
    logistics: {
      perissable: 100,  // 0% stock multi-jours
      saisonnalite: 70,
      marge_securite: 8,
      tolerance_rupture: 3,
    },
    seasons: {
      1: { name: "Janvier", impact: 20, description: "Galettes des rois, pic pâtisserie" },
      2: { name: "Février", impact: 5, description: "Hiver stable" },
      3: { name: "Mars", impact: 10, description: "Printemps léger" },
      4: { name: "Avril", impact: 50, description: "Pâques: chocolats, oeufs, brioches" },
      5: { name: "Mai", impact: 15, description: "Printemps normal" },
      6: { name: "Juin", impact: 20, description: "Mariages, réceptions" },
      7: { name: "Juillet", impact: 30, description: "Vacances, tourisme" },
      8: { name: "Août", impact: 25, description: "Vacances mais demande stable" },
      9: { name: "Septembre", impact: 10, description: "Rentrée scolaire ++" },
      10: { name: "Octobre", impact: 5, description: "Automne calme" },
      11: { name: "Novembre", impact: 40, description: "Thanksgiving US, approche Noël" },
      12: { name: "Décembre", impact: 100, description: "Noël: brioches, pain d'épices, bûches" },
    },
    holidays: [
      { name: "Noël", startMonth: 12, startDay: 15, endMonth: 1, endDay: 5, impact: 200 },
      { name: "Pâques", startMonth: 4, startDay: 1, endMonth: 4, endDay: 15, impact: 150 },
    ],
    hr: {
      base_staff: 8,
      absenteeism_avg: 6,
      seasonal_hiring_months: [3,4,11,12],
      vacation_risk_months: [7,8],
      training_impact_pct: 12,
      shift_coverage: 2, // Équipes 5h-14h et 14h-22h
    },
    special_events: [
      { name: "Épiphanie (Galettes)", month: 1, impact: 120 },
      { name: "Pâques (Œufs, brioches)", month: 4, impact: 150 },
      { name: "Mariages (Pièces montées)", month: 6, impact: 80 },
      { name: "Noël (Bûches, pains)", month: 12, impact: 200 },
    ],
    external_factors: {
      weather_sensitivity: 25,
      economic_cycles: "medium",
      competitor_risk: 20,
      school_calendar_impact: true, // Petits pains pour école
    },
  },

  epicerie: {
    label: "Épicerie / Alimentation",
    description: "Panier moyen stable, forte dépendance saisonière",
    icon: "🛒",
    logistics: {
      perissable: 60,
      saisonnalite: 65,
      marge_securite: 18,
      tolerance_rupture: 20,
    },
    seasons: {
      1: { name: "Janvier", impact: 0, description: "Post-fêtes, retour équilibre" },
      2: { name: "Février", impact: -10, description: "Budget serré clients" },
      3: { name: "Mars", impact: 5, description: "Printemps, produits frais" },
      4: { name: "Avril", impact: 10, description: "Pâques, chocolats, oeufs" },
      5: { name: "Mai", impact: 15, description: "Produits locaux saisonniers" },
      6: { name: "Juin", impact: 20, description: "Barbecue season" },
      7: { name: "Juillet", impact: 30, description: "Vacances, pique-niques" },
      8: { name: "Août", impact: 25, description: "Conserves, produits voyage" },
      9: { name: "Septembre", impact: 5, description: "Rentrée, basique" },
      10: { name: "Octobre", impact: 10, description: "Automne, courges" },
      11: { name: "Novembre", impact: 45, description: "Black Friday, Christmas prep" },
      12: { name: "Décembre", impact: 70, description: "Noël, stocks importants" },
    },
    holidays: [
      { name: "Noël/Jour An", startMonth: 12, startDay: 20, endMonth: 1, endDay: 5, impact: 150 },
    ],
    hr: {
      base_staff: 12,
      absenteeism_avg: 7,
      seasonal_hiring_months: [11,12],
      vacation_risk_months: [7,8],
      training_impact_pct: 8,
    },
    special_events: [
      { name: "Pâques", month: 4, impact: 40 },
      { name: "Black Friday", month: 11, impact: 80 },
      { name: "Noël", month: 12, impact: 120 },
    ],
    external_factors: {
      weather_sensitivity: 30,
      economic_cycles: "high",     // Consommation économique
      competitor_risk: 40,          // Grande concurrence
      location_impact: true,         // Centre-ville vs périphérie
    },
  },

  pepiniere: {
    label: "Pépinière / Jardinerie",
    description: "Ultra-saisonnier: printemps/automne = 80% du chiffre",
    icon: "🌱",
    logistics: {
      perissable: 25,
      saisonnalite: 95,  // ⚠️ TRÈS saisonnier
      marge_securite: 35,
      tolerance_rupture: 50,
    },
    seasons: {
      1: { name: "Janvier", impact: -70, description: "Fermé ou minimal" },
      2: { name: "Février", impact: -50, description: "Stocks minima, préparation" },
      3: { name: "Mars", impact: 150, description: "PICS: plantation printemps commence" },
      4: { name: "Avril", impact: 200, description: "PICS MAXIMAL: plantation fleurs/légumes" },
      5: { name: "Mai", impact: 140, description: "Fin printemps, fleurs annuelles" },
      6: { name: "Juin", impact: 40, description: "Post-pic, entretien produits" },
      7: { name: "Juillet", impact: -40, description: "Vacances, chaleur, fermeture partielle" },
      8: { name: "Août", impact: -30, description: "Vacances, stock dormant" },
      9: { name: "Septembre", impact: 130, description: "PICS: plantation automne/arbustes" },
      10: { name: "Octobre", impact: 110, description: "Automne, préparation hiver" },
      11: { name: "Novembre", impact: 30, description: "Fin saison, fleurs hiver" },
      12: { name: "Décembre", impact: -80, description: "Noël déco min, fermetures" },
    },
    holidays: [
      { name: "Hiver (déc-fév)", startMonth: 12, startDay: 1, endMonth: 2, endDay: 28, impact: -90 }, // Fermé ou réduit
    ],
    hr: {
      base_staff: 6,
      seasonal_staff: 15,           // Personnel saisonnier printemps
      absenteeism_avg: 10,
      seasonal_hiring_months: [2,3,4,8,9],
      vacation_risk_months: [7,8],
      training_impact_pct: 20,
    },
    special_events: [
      { name: "Printemps (mars-mai)", month: 3, impact: 250 },
      { name: "Automne (sept-oct)", month: 9, impact: 200 },
      { name: "Fêtes des jardins", month: 4, impact: 100 },
    ],
    external_factors: {
      weather_sensitivity: 80,      // Très important: gel, pluie, soleil
      economic_cycles: "medium",     // Loisir/maison
      competitor_risk: 35,
      climate_impact: "CRITICAL",    // Gel tardif, sécheresse = impacts énormes
    },
  },

  boutique: {
    label: "Boutique / Commerce de détail",
    description: "Variabilité selon emplacement: centre-ville vs galerie",
    icon: "🏪",
    logistics: {
      perissable: 5,      // Peu périssable (vêtements, accéssoires)
      saisonnalite: 60,
      marge_securite: 22,
      tolerance_rupture: 25,
    },
    seasons: {
      1: { name: "Janvier", impact: 50, description: "Soldes hiver, bonnes ventes" },
      2: { name: "Février", impact: 10, description: "Post-soldes, lent" },
      3: { name: "Mars", impact: 15, description: "Printemps, renouvellement collection" },
      4: { name: "Avril", impact: 20, description: "Pâques, vacances de printemps" },
      5: { name: "Mai", impact: 25, description: "Printemps, ponts, vacances" },
      6: { name: "Juin", impact: 30, description: "Été, tourisme début" },
      7: { name: "Juillet", impact: 40, description: "Vacances, tourisme pic" },
      8: { name: "Août", impact: 35, description: "Vacances, soldes fin d'été" },
      9: { name: "Septembre", impact: 10, description: "Rentrée scolaire modérée" },
      10: { name: "Octobre", impact: 15, description: "Automne, Halloween" },
      11: { name: "Novembre", impact: 60, description: "Black Friday MASSIVE, Noël prep" },
      12: { name: "Décembre", impact: 100, description: "Noël: cadeaux, achats cadeaux PICS" },
    },
    holidays: [
      { name: "Noël", startMonth: 12, startDay: 15, endMonth: 1, endDay: 5, impact: 180 },
      { name: "Soldes d'été", startMonth: 7, startDay: 1, endMonth: 7, endDay: 31, impact: -40 }, // Réduction prix
      { name: "Soldes d'hiver", startMonth: 1, startDay: 1, endMonth: 1, endDay: 31, impact: 80 },
    ],
    hr: {
      base_staff: 10,
      absenteeism_avg: 6,
      seasonal_hiring_months: [11,12],
      vacation_risk_months: [7,8],
      training_impact_pct: 10,
    },
    special_events: [
      { name: "Saint-Valentin", month: 2, impact: 50 },
      { name: "Black Friday/Cyber", month: 11, impact: 120 },
      { name: "Noël", month: 12, impact: 150 },
    ],
    external_factors: {
      weather_sensitivity: 20,
      economic_cycles: "CRITICAL",   // Très dépendant
      competitor_risk: 50,            // E-commerce, grands magasins
      location_impact: true,
      foot_traffic_seasonal: [7,8,11,12],
    },
  },

  bureau_etude: {
    label: "Bureau d'études / Services B2B",
    description: "Non-périssable, cycles longs, RH-focused",
    icon: "💼",
    logistics: {
      perissable: 0,
      saisonnalite: 35,
      marge_securite: 40,  // Plus de flexibilité
      tolerance_rupture: 60,
    },
    seasons: {
      1: { name: "Janvier", impact: 40, description: "Budgets 2025 approuvés, projets lancés" },
      2: { name: "Février", impact: 30, description: "Projets en cours" },
      3: { name: "Mars", impact: 25, description: "Stable, fin Q1" },
      4: { name: "Avril", impact: 20, description: "Printemps calme" },
      5: { name: "Mai", impact: 15, description: "Ponts, vacances début" },
      6: { name: "Juin", impact: 10, description: "Fin de projets Q2, vacances" },
      7: { name: "Juillet", impact: -20, description: "Vacances collectifs" },
      8: { name: "Août", impact: -15, description: "Vacances, peu d'activité" },
      9: { name: "Septembre", impact: 30, description: "Rentrée, nouveaux projets Q4" },
      10: { name: "Octobre", impact: 35, description: "Projets en cours, Q4 lance" },
      11: { name: "Novembre", impact: 40, description: "Budgets finaux 2026 en discussion" },
      12: { name: "Décembre", impact: -10, description: "Fin d'année, fermetures" },
    },
    holidays: [
      { name: "Noël/Jour An", startMonth: 12, startDay: 20, endMonth: 1, endDay: 5, impact: -50 },
      { name: "Été", startMonth: 7, startDay: 15, endMonth: 8, endDay: 31, impact: -60 },
    ],
    hr: {
      base_staff: 25,
      absenteeism_avg: 8,
      seasonal_hiring_months: [1,9],
      vacation_risk_months: [7,8,12],
      training_impact_pct: 20,
      skill_scarcity: "HIGH",       // Difficile à trouver bons profils
    },
    special_events: [
      { name: "Budget approval (Jan)", month: 1, impact: 100 },
      { name: "Project kickoffs", month: 9, impact: 80 },
    ],
    external_factors: {
      weather_sensitivity: 0,
      economic_cycles: "CRITICAL",   // Crises = réduction investissement
      competitor_risk: 45,
      talent_retention: "CRITICAL",   // Turnover = réduction capacité
      client_budget_cycles: "CRITICAL", // Budget public sept/oct
    },
  },
};

/**
 * Calcul impact combiné pour une date donnée
 * @param {string} sector - Code secteur
 * @param {Date} date - Date pour calcul
 * @returns {number} Impact global (-100 à +300%)
 */
export function calculateSeasonalImpact(sector, date) {
  const config = SECTOR_CONFIGS[sector];
  if (!config) return 0;

  const month = date.getMonth() + 1; // 1-12
  let impact = config.seasons[month]?.impact || 0;

  // Ajustement congés
  config.holidays?.forEach(holiday => {
    const isInRange =
      (month > holiday.startMonth) ||
      (month === holiday.startMonth && date.getDate() >= holiday.startDay) ||
      (month < holiday.endMonth) ||
      (month === holiday.endMonth && date.getDate() <= holiday.endDay);

    if (isInRange) impact += holiday.impact;
  });

  return Math.max(-100, Math.min(300, impact)); // Clamp -100 à +300%
}

export default SECTOR_CONFIGS;
