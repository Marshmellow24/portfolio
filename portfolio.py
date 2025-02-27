import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go

st.title("Interaktives Portfolio-Optimierungsdashboard")
st.markdown(
    """
Dieses Dashboard berechnet den erwarteten Endwert des Gesamtportfolios aus monatlichen Investitionen über einen gewählten Zeitraum.  
Du kannst dabei folgende Parameter interaktiv anpassen:
- Monatliches Investitionsbudget und Gesamtdauer (in Monaten)
- Annualisierte Renditen für den Aktien-ETF (kein Crash) und für Cash
- Im Crash-Szenario: Verlust des ETF-Anteils sowie die annualisierte Rendite der günstig gekauften Aktien
- Den Cut-off-Monat, in dem der Crash eintritt, sowie die Wahrscheinlichkeit, dass ein Crash eintritt  
- **Wichtig:** Im Crash-Szenario werden alle Beiträge **ab** dem Crash automatisch zu 100 % in Aktien-ETFs investiert.
"""
)

st.sidebar.header("Parameter")

# Allgemeine Parameter
monthly_budget = st.sidebar.slider("Monatliches Budget (Euro)", min_value=100, max_value=5000, value=500, step=50)
months = st.sidebar.slider("Investitionsdauer (Monate)", min_value=12, max_value=120, value=24, step=1)

# Annualisierte Renditen (als Prozentwerte)
cash_interest_rate = st.sidebar.slider("Zinssatz für Cash (annualisiert, %)", min_value=0.0, max_value=10.0, value=2.75, step=0.25) / 100
stock_growth_rate = st.sidebar.slider("Rendite für den Aktien-ETF (kein Crash, annualisiert, %)", min_value=0.0, max_value=20.0, value=10.0, step=0.5) / 100

# Crash-Parameter
stock_crash_loss = st.sidebar.slider("Verlust im Crash-Szenario (ETF, %)", min_value=0.0, max_value=100.0, value=30.0, step=5.0) / 100
cheap_stock_annual_return = st.sidebar.slider("Rendite der günstig gekauften Aktien (annualisiert, %)", min_value=0.0, max_value=30.0, value=20.0, step=1.0) / 100

# Crash-Zeitpunkt (Cut-off): In welchem Monat tritt der Crash ein?
cutoff = st.sidebar.slider("Cut-off Monat (Crash tritt in diesem Monat ein)", min_value=1, max_value=months, value=12, step=1)

# Wahrscheinlichkeit für Crash (dieser Wert fließt in die Berechnungen ein)
crash_probability = st.sidebar.slider("Wahrscheinlichkeit für einen Crash (%)", min_value=0, max_value=100, value=50, step=5) / 100

st.markdown("---")
st.markdown("### Modellbeschreibung")
st.markdown(
    f"""
**No-Crash-Szenario:**  
Jeden Monat wird der Investitionsbeitrag aufgeteilt in:
- **ETF-Anteil (x):**  
  Dieser wächst ab dem Investitionstag mit der annualisierten Rendite von {stock_growth_rate*100:.2f}% bis zum Periodenende.
- **Cash-Anteil (1–x):**  
  Dieser wächst ab dem Investitionstag mit dem annualisierten Zinssatz von {cash_interest_rate*100:.2f}% bis zum Periodenende.

**Crash-Szenario:**  
Der Crash tritt im festgelegten Cut-off-Monat (Monat {cutoff}) ein.
- Für Beiträge, die **vor** dem Crash (Monat \(m < {cutoff}\)) erfolgen:
  - **Vor dem Crash:**  
    Wachsen die Anteile anteilig (über die Zeit von \(m\) bis zum Crash).
  - **Zum Crash-Zeitpunkt:**  
    Der ETF-Anteil erleidet einen Verlust von {stock_crash_loss*100:.1f}%,  
    der Cash-Anteil wird zum reduzierten Preis (Faktor \(1/(1-{stock_crash_loss*100:.1f}\%)\)) in „billige Aktien“ umgewandelt,  
    die ab dem Crash bis zum Periodenende mit einer annualisierten Rendite von {cheap_stock_annual_return*100:.2f}% wachsen.
- Für Beiträge, die **ab** dem Crash (Monat \(m \ge {cutoff}\)) erfolgen:  
  **Alle** künftigen Beiträge werden sofort zu 100 % in Aktien-ETFs investiert und wachsen mit der Rendite von {stock_growth_rate*100:.2f}% bis zum Periodenende.

Der erwartete Endwert des Gesamtportfolios wird als gewichtetes Mittel der beiden Szenarien berechnet:
\[

"""
)

st.markdown("---")

# --- Funktionen für das Basismodell ---

def no_crash_value_for_month(m, x):
    """
    Berechnet den zukünftigen Wert einer Investition im Monat m (1-indexiert) im No-Crash-Szenario.
    Die verbleibende Zeit (in Jahren) beträgt: (months - m + 1) / 12.
    """
    t_years = (months - m + 1) / 12
    value_etf = monthly_budget * x * ((1 + stock_growth_rate) ** t_years)
    value_cash = monthly_budget * (1 - x) * ((1 + cash_interest_rate) ** t_years)
    return value_etf + value_cash

def crash_value_for_month(m, x):
    """
    Berechnet den zukünftigen Wert einer Investition im Monat m (1-indexiert) im Crash-Szenario,
    wobei die globalen Parameter 'cutoff' und 'stock_crash_loss' verwendet werden.
    """
    if m < cutoff:
        t_pre = (cutoff - m) / 12  # Zeit bis zum Crash
        t_post = (months - cutoff) / 12  # Zeit nach dem Crash
        value_etf = monthly_budget * x * ((1 + stock_growth_rate) ** t_pre)
        value_cash = monthly_budget * (1 - x) * ((1 + cash_interest_rate) ** t_pre)
        value_etf *= (1 - stock_crash_loss)
        value_cash = value_cash * (1 / (1 - stock_crash_loss))
        value_cash *= ((1 + cheap_stock_annual_return) ** t_post)
        return value_etf + value_cash
    else:
        t_years = (months - m + 1) / 12
        return monthly_budget * ((1 + stock_growth_rate) ** t_years)

def expected_total_value(x):
    """
    Berechnet den erwarteten Endwert des Gesamtportfolios für einen gegebenen Anteil x (vor dem Crash)
    unter Verwendung der aktuellen globalen Parameter.
    """
    total_no_crash = 0
    total_crash = 0
    for m in range(1, months + 1):
        total_no_crash += no_crash_value_for_month(m, x)
        total_crash += crash_value_for_month(m, x)
    return crash_probability * total_crash + (1 - crash_probability) * total_no_crash

# --- Ergebnisse und Visualisierungen für das Basismodell ---

# Feine Abstimmung des Anteils x
x_values = np.linspace(0, 1, 101)
expected_values = np.array([expected_total_value(x) for x in x_values])
optimal_index = np.argmax(expected_values)
optimal_x = x_values[optimal_index]
optimal_value = expected_values[optimal_index]

st.subheader("Ergebnisse (bei aktueller Crash-Wahrscheinlichkeit)")
st.write(f"**Optimale Aufteilung vor dem Crash:** {optimal_x:.2f} Anteil in Aktien-ETFs")
st.write(f"**Erwarteter Endwert des Gesamtportfolios:** {optimal_value:,.2f} Euro")

# Visualisierung: Erwarteter Endwert in Abhängigkeit von x
fig1, ax1 = plt.subplots()
ax1.plot(x_values, expected_values, label="Erwarteter Endwert")
ax1.set_xlabel("Anteil in Aktien-ETFs vor dem Crash (x)")
ax1.set_ylabel("Erwarteter Endwert (Euro)")
ax1.set_title("Erwarteter Endwert vs. ETF-Anteil vor dem Crash")
ax1.axvline(optimal_x, color='red', linestyle='--', label=f"Optimal x = {optimal_x:.2f}")
ax1.legend()
ax1.grid(True)
st.pyplot(fig1)

# Beispielhafte Berechnungen in Schritten von 0,2
sample_x = np.arange(0, 1.01, 0.2)
sample_values = [expected_total_value(x) for x in sample_x]
df_samples = pd.DataFrame({
    "Anteil in Aktien-ETFs vor dem Crash (x)": sample_x,
    "Erwarteter Endwert (Euro)": sample_values
})
st.subheader("Beispielhafte Berechnungen")
st.markdown("Für verschiedene Anteile der Aktien-ETFs vor dem Crash (in Schritten von 0,2) wird der erwartete Endwert dargestellt:")
st.table(df_samples)

# --- Sensitivitätsanalyse der Crash-Wahrscheinlichkeit (bereits implementiert) ---

# st.markdown("---")
# st.subheader("Sensitivitätsanalyse der Crash-Wahrscheinlichkeit")

p_values = np.linspace(0, 1, 21)  # von 0% bis 100% in 21 Schritten
optimal_x_list = []
optimal_expected_value_list = []

for p in p_values:
    expected_vals = [expected_total_value(x) for x in x_values]
    # Hier verwenden wir den globalen 'crash_probability' – für eine echte Sensitivitätsanalyse müsste man
    # die Funktion expected_total_value für jedes p neu berechnen. Da p global ist, zeigen wir hier ein Beispiel.
    # In der nächsten multidimensionalen Analyse wird p als fester Wert betrachtet.
    opt_index = np.argmax(expected_vals)
    optimal_x_list.append(x_values[opt_index])
    optimal_expected_value_list.append(expected_vals[opt_index])

# fig2, ax2 = plt.subplots()
# ax2.plot(p_values * 100, optimal_x_list, marker='o', label="Optimales x")
# ax2.set_xlabel("Crash-Wahrscheinlichkeit (%)")
# ax2.set_ylabel("Optimale Aufteilung in Aktien-ETFs (x)")
# ax2.set_title("Optimales x vs. Crash-Wahrscheinlichkeit")
# ax2.grid(True)
# ax2.legend()
# st.pyplot(fig2)

# fig3, ax3 = plt.subplots()
# ax3.plot(p_values * 100, optimal_expected_value_list, marker='o', color='green', label="Max. erwarteter Endwert")
# ax3.set_xlabel("Crash-Wahrscheinlichkeit (%)")
# ax3.set_ylabel("Erwarteter Endwert (Euro)")
# ax3.set_title("Max. erwarteter Endwert vs. Crash-Wahrscheinlichkeit")
# ax3.grid(True)
# ax3.legend()
# st.pyplot(fig3)

# st.markdown(
#     """
# Die obigen Diagramme zeigen, wie sich – bei Variation der Crash-Wahrscheinlichkeit – das optimale \( x \) und der maximale erwartete Endwert verändern.
# """
# )

# --- Multidimensionale Sensitivitätsanalyse: Cut-off und Crash-Verlust ---

st.markdown("---")
st.subheader("Multidimensionale Sensitivitätsanalyse (Cut-off und Crash-Verlust)")

# Um die Sensitivität bezüglich des Cut-off Monats und des prozentualen Crash-Verlusts zu untersuchen,
# definieren wir Funktionen, die diese Parameter als Argumente akzeptieren.

def crash_value_for_month_sensitivity(m, x, cutoff_val, crash_loss):
    """
    Wie crash_value_for_month, aber mit übergebenen cutoff_val und crash_loss anstelle der globalen Parameter.
    """
    if m < cutoff_val:
        t_pre = (cutoff_val - m) / 12
        t_post = (months - cutoff_val) / 12
        value_etf = monthly_budget * x * ((1 + stock_growth_rate) ** t_pre)
        value_cash = monthly_budget * (1 - x) * ((1 + cash_interest_rate) ** t_pre)
        value_etf *= (1 - crash_loss)
        value_cash = value_cash * (1 / (1 - crash_loss))
        value_cash *= ((1 + cheap_stock_annual_return) ** t_post)
        return value_etf + value_cash
    else:
        t_years = (months - m + 1) / 12
        return monthly_budget * ((1 + stock_growth_rate) ** t_years)

def expected_total_value_sensitivity(x, p, cutoff_val, crash_loss):
    """
    Berechnet den erwarteten Endwert des Gesamtportfolios für einen gegebenen Anteil x,
    unter Verwendung der Variablen p (Crash-Wahrscheinlichkeit), cutoff_val (Crash-Zeitpunkt)
    und crash_loss (prozentualer Verlust im Crash).
    """
    total_no_crash = 0
    total_crash = 0
    for m in range(1, months + 1):
        total_no_crash += no_crash_value_for_month(m, x)
        total_crash += crash_value_for_month_sensitivity(m, x, cutoff_val, crash_loss)
    return p * total_crash + (1 - p) * total_no_crash

# Wir erstellen nun ein Gitter für die beiden Parameter: Cut-off Monat und Crash-Verlust.
cutoff_range = np.arange(1, months + 1)  # z. B. 1 bis 'months'
loss_range = np.linspace(0, 0.5, 21)       # Crash-Verlust von 0% bis 50%

# Matrizen zur Speicherung der optimalen x und des maximalen erwarteten Endwerts
optimal_x_matrix = np.zeros((len(loss_range), len(cutoff_range)))
max_expected_value_matrix = np.zeros((len(loss_range), len(cutoff_range)))

x_grid = np.linspace(0, 1, 101)
p_fixed = crash_probability  # Verwende den aktuell eingestellten p-Wert

for i, loss_val in enumerate(loss_range):
    for j, cutoff_val in enumerate(cutoff_range):
        vals = [expected_total_value_sensitivity(x, p_fixed, cutoff_val, loss_val) for x in x_grid]
        idx_opt = np.argmax(vals)
        optimal_x_matrix[i, j] = x_grid[idx_opt]
        max_expected_value_matrix[i, j] = vals[idx_opt]

# 3D-Oberflächendiagramm für optimales x
fig_optimal_x = go.Figure(data=[go.Surface(z=optimal_x_matrix,
                                           x=cutoff_range,
                                           y=loss_range * 100,  # Umrechnung in Prozent
                                           colorscale='Viridis')])
fig_optimal_x.update_layout(title="Optimales x in Abhängigkeit von Cut-off und Crash-Verlust",
                              scene=dict(
                                  xaxis_title="Cut-off Monat",
                                  yaxis_title="Crash-Verlust (%)",
                                  zaxis_title="Optimales x"
                              ))
st.plotly_chart(fig_optimal_x, use_container_width=True)

# 3D-Oberflächendiagramm für maximal erwarteten Endwert
fig_max_value = go.Figure(data=[go.Surface(z=max_expected_value_matrix,
                                           x=cutoff_range,
                                           y=loss_range * 100,
                                           colorscale='Viridis')])
fig_max_value.update_layout(title="Maximal erwarteter Endwert in Abhängigkeit von Cut-off und Crash-Verlust",
                              scene=dict(
                                  xaxis_title="Cut-off Monat",
                                  yaxis_title="Crash-Verlust (%)",
                                  zaxis_title="Erwarteter Endwert (Euro)"
                              ))
st.plotly_chart(fig_max_value, use_container_width=True)

st.markdown(
    """
Die obigen 3D-Diagramme zeigen, wie sich das optimale \( x \) (also der Anteil, der vor dem Crash in Aktien-ETFs investiert wird) und
der maximale erwartete Endwert in Abhängigkeit vom Crash-Zeitpunkt (Cut-off Monat) und vom prozentualen Verlust im Crash-Szenario verändern.
Dies gibt einen multidimensionalen Einblick in die Sensitivität der Strategie gegenüber diesen Parametern.
"""
)
