import React, { useState } from "react";
import { SECTOR_CONFIGS } from "../config/sectorConfig";

/**
 * Composant affichage config avancée par secteur
 * Affiche: saisons, congés, RH, événements spéciaux
 */
export default function SectorAdvancedConfig({ sector, onParamsChange, params }) {
  const config = SECTOR_CONFIGS[sector] || SECTOR_CONFIGS.general;
  const [expandedSection, setExpandedSection] = useState(null);

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const MONTH_NAMES = [
    "Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
    "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"
  ];

  const SECTION_COLORS = {
    seasons: "#e8f4f8",
    holidays: "#f0f5f0",
    hr: "#f5f0f8",
    events: "#fff9e6",
    external: "#f8e8e8",
  };

  return (
    <div style={{ marginBottom: "24px", border: "1px solid #ddd", borderRadius: "4px" }}>
      {/* HEADER */}
      <div style={{ padding: "16px", background: "#f8f8f8", borderBottom: "1px solid #ddd" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "24px" }}>{config.icon}</span>
          <div>
            <h3 style={{ margin: "0 0 4px 0", fontSize: "16px", fontWeight: "700" }}>
              {config.label}
            </h3>
            <p style={{ margin: 0, fontSize: "12px", color: "#666" }}>
              {config.description}
            </p>
          </div>
        </div>
      </div>

      {/* CONTENUS */}
      <div style={{ padding: "16px" }}>
        {/* 1️⃣ SAISONNALITÉ */}
        <SectionCollapsible
          title="📅 Saisonnalité annuelle"
          isExpanded={expandedSection === "seasons"}
          onToggle={() => toggleSection("seasons")}
          color={SECTION_COLORS.seasons}
        >
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "8px" }}>
            {Object.entries(config.seasons).map(([month, data]) => (
              <div
                key={month}
                style={{
                  padding: "12px 8px",
                  background: data.impact > 50 ? "#c8e6c9" : data.impact < -20 ? "#ffcccc" : "#fff",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  textAlign: "center",
                  fontSize: "12px",
                }}
                title={data.description}
              >
                <div style={{ fontWeight: "700", marginBottom: "4px" }}>
                  {MONTH_NAMES[month - 1]}
                </div>
                <div
                  style={{
                    color: data.impact > 0 ? "#006600" : "#cc0000",
                    fontWeight: "700",
                    fontSize: "13px",
                  }}
                >
                  {data.impact > 0 ? "+" : ""}{data.impact}%
                </div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: "11px", color: "#666", marginTop: "12px" }}>
            <strong>💡 Conseil:</strong> Anticipez vos achats 2-3 mois avant les pics saisonniers.
            Stock de sécurité {config.logistics.marge_securite}% en{" "}
            {Math.max(...Object.values(config.seasons).map((s) => s.impact))}% peak.
          </p>
        </SectionCollapsible>

        {/* 2️⃣ CONGÉS & FERMETURES */}
        {config.holidays && config.holidays.length > 0 && (
          <SectionCollapsible
            title="🏖️ Congés & Fermetures"
            isExpanded={expandedSection === "holidays"}
            onToggle={() => toggleSection("holidays")}
            color={SECTION_COLORS.holidays}
          >
            {config.holidays.map((holiday, idx) => (
              <div
                key={idx}
                style={{
                  padding: "12px",
                  background: "#f9f9f9",
                  border: "1px solid #e0e0e0",
                  borderRadius: "4px",
                  marginBottom: "8px",
                }}
              >
                <div style={{ fontWeight: "700", marginBottom: "4px" }}>
                  {holiday.name}
                </div>
                <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>
                  {new Date(2024, holiday.startMonth - 1, holiday.startDay).toLocaleDateString("fr-FR")} →{" "}
                  {new Date(2024, holiday.endMonth - 1, holiday.endDay).toLocaleDateString("fr-FR")}
                </div>
                <div style={{ fontSize: "12px" }}>
                  Impact: <span style={{ fontWeight: "700", color: holiday.impact < 0 ? "#cc0000" : "#006600" }}>
                    {holiday.impact > 0 ? "+" : ""}{holiday.impact}%
                  </span>
                  {holiday.impact === -100 && " (Fermé)"}
                  {holiday.impact > 100 && " (Pic!)"}
                </div>
              </div>
            ))}
          </SectionCollapsible>
        )}

        {/* 3️⃣ RH & EFFECTIF */}
        {config.hr && (
          <SectionCollapsible
            title="👥 Gestion RH & Effectif"
            isExpanded={expandedSection === "hr"}
            onToggle={() => toggleSection("hr")}
            color={SECTION_COLORS.hr}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <MetricCard
                label="Effectif de base"
                value={config.hr.base_staff}
                unit="personnes"
                icon="💼"
              />
              {config.hr.seasonal_staff && (
                <MetricCard
                  label="Personnel saisonnier"
                  value={config.hr.seasonal_staff}
                  unit="personnes"
                  icon="📈"
                />
              )}
              <MetricCard
                label="Absentéisme moyen"
                value={config.hr.absenteeism_avg}
                unit="%"
                icon="🚑"
              />
              {config.hr.training_impact_pct && (
                <MetricCard
                  label="Impact formation"
                  value={config.hr.training_impact_pct}
                  unit="%"
                  icon="📚"
                />
              )}
            </div>
            <div style={{ marginTop: "12px", padding: "12px", background: "#fff9e6", borderRadius: "4px" }}>
              <div style={{ fontSize: "12px", fontWeight: "700", marginBottom: "4px" }}>
                📅 Mois d'embauche saisonnière:
              </div>
              <div style={{ fontSize: "12px" }}>
                {config.hr.seasonal_hiring_months
                  ?.map((m) => MONTH_NAMES[m - 1])
                  .join(", ")}
              </div>
            </div>
            <div style={{ marginTop: "8px", fontSize: "11px", color: "#666" }}>
              <strong>⚠️ Risque:</strong> Vacances concentration en{" "}
              {config.hr.vacation_risk_months?.map((m) => MONTH_NAMES[m - 1]).join(", ")}.
              Planifiez couverture d'avance.
            </div>
          </SectionCollapsible>
        )}

        {/* 4️⃣ ÉVÉNEMENTS SPÉCIAUX */}
        {config.special_events && config.special_events.length > 0 && (
          <SectionCollapsible
            title="🎉 Événements Spéciaux"
            isExpanded={expandedSection === "events"}
            onToggle={() => toggleSection("events")}
            color={SECTION_COLORS.events}
          >
            {config.special_events.map((event, idx) => (
              <div
                key={idx}
                style={{
                  padding: "12px",
                  background: "#fffde7",
                  border: "1px solid #f0d77d",
                  borderRadius: "4px",
                  marginBottom: "8px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontWeight: "700" }}>{event.name}</span>
                <span
                  style={{
                    background: "#ff9800",
                    color: "#fff",
                    padding: "4px 12px",
                    borderRadius: "12px",
                    fontSize: "12px",
                    fontWeight: "700",
                  }}
                >
                  +{event.impact}%
                </span>
              </div>
            ))}
          </SectionCollapsible>
        )}

        {/* 5️⃣ FACTEURS EXTERNES */}
        {config.external_factors && (
          <SectionCollapsible
            title="🌍 Facteurs Externes"
            isExpanded={expandedSection === "external"}
            onToggle={() => toggleSection("external")}
            color={SECTION_COLORS.external}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              {config.external_factors.weather_sensitivity > 0 && (
                <FactorCard
                  label="Sensibilité météo"
                  level={config.external_factors.weather_sensitivity}
                  icon="🌤️"
                />
              )}
              {config.external_factors.economic_cycles && config.external_factors.economic_cycles !== "none" && (
                <FactorCard
                  label="Cycles économiques"
                  level={config.external_factors.economic_cycles === "CRITICAL" ? 90 : 60}
                  icon="📊"
                  isText={true}
                  text={config.external_factors.economic_cycles}
                />
              )}
              {config.external_factors.competitor_risk > 0 && (
                <FactorCard
                  label="Risque concurrence"
                  level={config.external_factors.competitor_risk}
                  icon="🏆"
                />
              )}
            </div>
            <div style={{ marginTop: "12px", fontSize: "11px", color: "#555", background: "#fafafa", padding: "8px", borderRadius: "4px" }}>
              ⚡ <strong>Vigilance:</strong> Surveiller signaux externes qui pourraient affecter
              stock prévu (grèves, crise éco, concurrence accrue).
            </div>
          </SectionCollapsible>
        )}

        {/* PARAMÈTRES AJUSTABLES */}
        <SectionCollapsible
          title="⚙️ Paramètres Prévisionnels"
          isExpanded={expandedSection === "params"}
          onToggle={() => toggleSection("params")}
          color="#f0f4f8"
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            {[
              {
                key: "perissable",
                label: "Périssabilité",
                low: "Durable",
                high: "Ultra-périssable",
              },
              {
                key: "saisonnalite",
                label: "Saisonnalité",
                low: "Stable",
                high: "Très saisonnier",
              },
              {
                key: "marge_securite",
                label: "Marge de sécurité",
                low: "Juste (zéro stock)",
                high: "Large (buffer important)",
              },
              {
                key: "tolerance_rupture",
                label: "Tolérance rupture",
                low: "Zéro rupture",
                high: "Flexible",
              },
            ].map(({ key, label, low, high }) => (
              <ParamSlider
                key={key}
                label={label}
                value={params[key] || config.logistics[key]}
                onChange={(val) => onParamsChange({ ...params, [key]: val })}
                low={low}
                high={high}
              />
            ))}
          </div>
        </SectionCollapsible>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// SOUS-COMPOSANTS
// ═══════════════════════════════════════════════════════════

function SectionCollapsible({ title, isExpanded, onToggle, color, children }) {
  return (
    <div style={{ marginBottom: "12px" }}>
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          padding: "12px",
          background: color,
          border: "1px solid #ddd",
          borderRadius: "4px 4px 0 0",
          cursor: "pointer",
          fontWeight: "700",
          fontSize: "13px",
          textAlign: "left",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        {title}
        <span style={{ fontSize: "16px" }}>{isExpanded ? "▼" : "▶"}</span>
      </button>
      {isExpanded && (
        <div style={{ padding: "16px", background: "#fafafa", borderRadius: "0 0 4px 4px", borderLeft: "1px solid #ddd", borderRight: "1px solid #ddd", borderBottom: "1px solid #ddd" }}>
          {children}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, unit, icon }) {
  return (
    <div style={{ padding: "12px", background: "#fff", border: "1px solid #eee", borderRadius: "4px" }}>
      <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>{icon} {label}</div>
      <div style={{ fontSize: "18px", fontWeight: "700" }}>
        {value}
        <span style={{ fontSize: "12px", color: "#888", marginLeft: "4px" }}>{unit}</span>
      </div>
    </div>
  );
}

function FactorCard({ label, level, icon, isText, text }) {
  return (
    <div style={{ padding: "12px", background: "#fff", border: "1px solid #eee", borderRadius: "4px" }}>
      <div style={{ fontSize: "11px", color: "#666", marginBottom: "6px" }}>{icon} {label}</div>
      {!isText ? (
        <div>
          <div style={{ fontSize: "12px", fontWeight: "700", marginBottom: "4px" }}>
            {level > 70 ? "🔴 Critique" : level > 40 ? "🟡 Moyen" : "🟢 Faible"}
          </div>
          <div style={{ background: "#eee", height: "6px", borderRadius: "3px", overflow: "hidden" }}>
            <div
              style={{
                width: `${level}%`,
                background: level > 70 ? "#cc0000" : level > 40 ? "#ff9800" : "#4caf50",
                height: "100%",
              }}
            />
          </div>
        </div>
      ) : (
        <div style={{ fontSize: "12px", fontWeight: "700", color: "#cc0000" }}>{text}</div>
      )}
    </div>
  );
}

function ParamSlider({ label, value, onChange, low, high }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: "700", marginBottom: "6px" }}>
        <span>{label}</span>
        <span style={{ color: "#666" }}>{value}%</span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%", accentColor: "#000" }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: "#aaa", marginTop: "4px" }}>
        <span>{low}</span>
        <span>{high}</span>
      </div>
    </div>
  );
}
