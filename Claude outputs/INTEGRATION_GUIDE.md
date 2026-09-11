# 🎯 Guide d'Intégration - Paramètres Métier Avancés

## Vue d'ensemble
Nouvelle architecture pour **anticipation intelligente** avec paramètres détaillés par secteur d'emploi.

### Fichiers Créés
1. **`src/config/sectorConfig.js`** — Configuration complète 7 secteurs
2. **`src/components/SectorAdvancedConfig.jsx`** — UI interactive

### Intégration dans Dashboard.jsx

#### 1️⃣ Imports
```javascript
import { SECTOR_CONFIGS, calculateSeasonalImpact } from "../config/sectorConfig";
import SectorAdvancedConfig from "../components/SectorAdvancedConfig";
```

#### 2️⃣ Remplacer SECTOR_PRESETS

**AVANT:**
```javascript
const SECTOR_PRESETS = {
  general: { perissable: 30, saisonnalite: 50, marge_securite: 20, tolerance_rupture: 30 },
  restaurant: { perissable: 95, saisonnalite: 70, marge_securite: 15, tolerance_rupture: 10 },
  // ...
};

function handleSectorChange(val) {
  setSector(val);
  setSectorParams(SECTOR_PRESETS[val] || SECTOR_PRESETS.general);
}
```

**APRÈS:**
```javascript
function handleSectorChange(val) {
  setSector(val);
  const config = SECTOR_CONFIGS[val] || SECTOR_CONFIGS.general;
  setSectorParams(config.logistics);
  setAdvancedConfig(config); // nouveau state
}

// State à ajouter
const [advancedConfig, setAdvancedConfig] = useState(SECTOR_CONFIGS.general);
```

#### 3️⃣ Ajouter UI Avancée (dans le formulaire)

**Remplacer les sliders simples par:**
```javascript
{(data || result) && (
  <div style={STYLE.card}>
    <h2 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "20px" }}>
      Paramètres
    </h2>

    {/* Sélection secteur */}
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "20px" }}>
      <div>
        <label style={STYLE.label}>Secteur d'activité</label>
        <select 
          style={STYLE.input} 
          value={sector} 
          onChange={e => handleSectorChange(e.target.value)}
        >
          <option value="general">Général</option>
          <option value="restaurant">Restaurant / Traiteur</option>
          <option value="epicerie">Épicerie / Alimentation</option>
          <option value="boulangerie">Boulangerie / Pâtisserie</option>
          <option value="pepiniere">Pépinière / Jardinerie</option>
          <option value="boutique">Boutique / Commerce de détail</option>
          <option value="bureau_etude">Bureau d'études / Services</option>
        </select>
      </div>

      <div>
        <label style={STYLE.label}>Horizon de prévision (jours)</label>
        <select style={STYLE.input} value={periods} onChange={e => setPeriods(Number(e.target.value))}>
          <option value={7}>7 jours</option>
          <option value={14}>14 jours</option>
          <option value={30}>30 jours</option>
          <option value={60}>60 jours</option>
          <option value={90}>90 jours</option>
        </select>
      </div>
    </div>

    {/* Composant config avancée */}
    <SectorAdvancedConfig
      sector={sector}
      params={sectorParams}
      onParamsChange={setSectorParams}
    />

    {/* Autres boutons comme avant */}
  </div>
)}
```

#### 4️⃣ Backend Integration

Le payload envoyé au backend doit inclure:
```javascript
const payload = {
  data: data || SAMPLE_DATA,
  product_name: productName,
  periods: periods,
  sector: sector,
  sector_params: sectorParams,
  sector_metadata: advancedConfig, // ✨ NOUVEAU: metadata complète
};

const res = await backendClient.recommendations(
  payload.data,
  payload.product_name,
  payload.periods,
  payload.sector,
  payload.sector_params,
  payload.sector_metadata // passer metadata
);
```

#### 5️⃣ Mises à jour Backend (Python/Flask)

**Fichier: `backend/app.py`**

```python
@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    """Enhanced avec paramètres métier avancés"""
    data = request.json
    
    sector = data.get('sector', 'general')
    sector_metadata = data.get('sector_metadata', {})
    
    # Calcul impact saisonnal
    holidays = sector_metadata.get('holidays', [])
    seasons = sector_metadata.get('seasons', {})
    hr_config = sector_metadata.get('hr', {})
    special_events = sector_metadata.get('special_events', [])
    
    # ✨ Nouveau: Ajuster prévisions selon:
    # 1. Saisonnalité (déjà fait)
    # 2. Congés programmés
    # 3. Risque RH (vacances, formations)
    # 4. Événements spéciaux
    
    # Exemple: si juillet + mois congés + secteur HR-sensible
    if is_vacation_month(current_date, hr_config.get('vacation_risk_months', [])):
        capacity_reduction = hr_config.get('absenteeism_avg', 5) * 1.5  # 50% plus d'absences
        forecast_adjustment = 1 - (capacity_reduction / 100)
    
    # Recommandations intelligentes
    recommendations = generate_smart_recommendations(
        forecast_data,
        sector=sector,
        holidays=holidays,
        special_events=special_events,
        hr_config=hr_config,
    )
    
    return jsonify(recommendations)
```

---

## 📊 Exemple: Restaurant en Juillet

### Données Entrantes
```
- Secteur: "restaurant"
- Période: 30 jours
- Données historiques: 12 mois
```

### Configuration Appliquée
```
Juillet = +50% (vacances, tourisme)
  + "Été fermeture" (2-3 semaines) = -100% (0 ventes)
  + 15 staff de base + 8 saisonniers en juillet
  + Absentéisme = 8% moyen + 15% (congés) = 23%
  + Capacité = 23 * (1 - 0.23) = ~18 personnes
  + Événements: mariages +80%, séminaires +40%

Impact combiné: 
  Base +50% (saisonnier)
  - 100% (fermeture 2 semaines)
  + 80% (mariages)
  = +30% net (avec perte effective)
```

### Recommandations Générées
1. **Stock:** Augmenter 40% par rapport normal
2. **RH:** Recruter 8 saisonniers dès juin (avant rush)
3. **Planning:** Fermer 2-3 semaines au 15 juillet (communiquer clients)
4. **Approvisionnement:** Commander gros quantité "easy-perishable" (fruits, légumes frais)
5. **Alerte:** Risque rupture si événement improvu + 1 staff absent = prévenir margin

---

## 🎯 Flux Utilisateur Complet

```
1. Utilisateur log + Dashboard
   ↓
2. Import CSV données historiques
   ↓
3. Sélectionne secteur (ex: "Restaurant")
   ↓
4. UI affiche:
   - Calendrier saisonnier 2024 (pics/creux)
   - Congés prévus (fermetures spécifiques)
   - Configuration RH (staff, absences)
   - Événements spéciaux (mariages, séminaires)
   - Facteurs externes (météo, concurrence)
   ↓
5. Peut ajuster paramètres sliders (marges, tolérances)
   ↓
6. Clique "Lancer prévision IA"
   ↓
7. Backend reçoit:
   - Données CSV
   - Sector ID
   - Config complète (saisons, congés, RH, events)
   - Paramètres utilisateur (ajustements)
   ↓
8. Prévisions retournent:
   - Graphique 30j avec annotations (fermetures, pics)
   - Recommandations contextuelles
   - Alertes RH (vacances, formations)
   - Alerts stocks (rupture risk sur événements)
   ↓
9. Rapport exportable PDF:
   - Résumé executive
   - Calendrier anticipation
   - Recommandations RH
   - Scénarios risque
```

---

## 🚀 Phasing Implémentation

### Phase 1 (Semaine 1)
- ✅ Config files créés (sectorConfig.js)
- ✅ UI component créé (SectorAdvancedConfig.jsx)
- [ ] Intégrer Dashboard.jsx
- [ ] Tester affichage UI

### Phase 2 (Semaine 2)
- [ ] Backend ajuste recommandations selon saisons
- [ ] Ajuster prévisions selon vacances
- [ ] Alertes RH intégrées

### Phase 3 (Semaine 3)
- [ ] Génération PDF avanc ée (calendrier + recommandations)
- [ ] Analytics dashboard par secteur
- [ ] Tests complets + users tests

---

## 📈 Métriques de Succès

| Métrique | Target |
|---|---|
| Réduction ruptures (restaurant) | -35% |
| Réduction over-stock (jardins) | -50% |
| Satisfaction users | 4.5/5 |
| Taux adoption config avancée | >70% |
| Temps anticipation client | 6 mois (vs 1 avant) |

---

## 🔍 Testing Scenarios

### Scenario 1: Restaurant July
- Input: Restaurant data, july-only
- Expected: +30% recommendation vs normal month
- Alert: Check staff availability, plan suppliers

### Scenario 2: Bakery Easter  
- Input: Boulangerie data, mars-avril
- Expected: Peak +150% via Easter holiday
- Alert: Easter eggs production +200%, hire 5+ apprentices

### Scenario 3: Nursery Spring
- Input: Pépinière data, février-mai
- Expected: Massive +200% april-may peak, weather-sensitive
- Alert: Frost risk april, greenhouse heating critical

---

## 📞 Support & Questions

- Métier spécifique? Créer issue avec details
- Nouvelle saison? Updater SECTOR_CONFIGS.js
- Nouvelles features? Créer PR avec tests
