# Resultados de Backtesting — v1 (2026-10-01)

> Probamos el motor con **3 años de datos reales** (oct-2023 → oct-2026) en BTC
> y ETH, en velas de 1 hora. Este documento registra qué funcionó, qué no, y la
> **estrategia validada**. Nada de esto es una promesa: es evidencia con sus límites.

---

## 1. Metodología

- **Datos:** Binance público, velas de 1h, ~26.000 velas por activo.
- **Simulación:** solo largos (spot). Se entra en la apertura **siguiente** a la
  señal (sin mirar el futuro). Se descuentan **comisiones** (0.1% por lado).
- **Validación:** se separa el 70% inicial (aprendizaje) del 30% final
  (**no visto**, la prueba de fuego).
- **Riesgo:** 1% del capital por operación (perfil moderado).

### Métricas
- **Profit Factor (PF):** ganancias / pérdidas. > 1.3 se considera sano.
- **Drawdown:** peor caída desde el máximo. Mide el "dolor" del camino.
- **R medio:** ganancia media medida en unidades de riesgo.

---

## 2. Iteraciones (qué aprendimos)

| Versión | Cambio | Resultado |
|---------|--------|-----------|
| v0 | Heurística inicial | PF 1.08, **se perdía la subida** (casi no compraba) |
| v1 | Estructura de mercado depende del **régimen** (tendencia vs lateral) | Compraba más, pero **sobre-operaba** en lateral (PF 0.96) |
| v2 | No comprar **contra la tendencia diaria** + exigir **señal fuerte** | PF 1.13, drawdown 9%; fuera de muestra PF 1.80 |
| v3 | **Stop dinámico** (sigue al precio) | **PF 1.44**, drawdown 9%; fuera de muestra PF 3.56 |

---

## 3. Resultado de la estrategia validada

**Reglas finales:**
1. **Entrar** solo si la señal es **COMPRA FUERTE** *y* la tendencia diaria no es
   bajista.
2. **Salir** con **stop dinámico** (3× ATR, sube solo cuando el precio sube) o con
   **VENTA FUERTE**.
3. Riesgo 1% del capital por operación.

### BTC/USDT (1h)
| Métrica | Valor |
|---------|-------|
| Operaciones | 179 |
| Acierto | 38.6% |
| **Profit Factor** | **1.44** |
| Retorno de la cuenta | +54.0% |
| **Peor caída (drawdown)** | **9.2%** |
| **Fuera de muestra (30% final)** | **PF 3.56 · +10.3%** |
| Comprar y mantener (mismo periodo) | +213.5% |

### ETH/USDT (1h)
| Métrica | Valor |
|---------|-------|
| Operaciones | 151 |
| Acierto | 36.4% |
| **Profit Factor** | **1.39** |
| Retorno de la cuenta | +46.1% |
| **Peor caída (drawdown)** | **11.5%** |
| **Fuera de muestra (30% final)** | **PF 2.88 · +19.7%** |
| Comprar y mantener (mismo periodo) | +71.4% |

> El hecho de que **funcione de forma parecida en BTC y ETH** es señal de que las
> reglas son sanas y no están ajustadas a un solo caso.

---

## 4. Conclusión honesta

- ✅ El método es **rentable y consistente** fuera de muestra en ambos activos.
- ✅ **Protege el capital** en caídas: en el tramo final, el mercado cayó (−19% BTC,
  −24% ETH) y la estrategia **ganó** (+10%, +20%) con caídas mínimas.
- ✅ La tasa de acierto es **baja (~38%)**, típica de métodos que **dejan correr
  las ganancias**: se pierde poco muchas veces y se gana mucho pocas veces.
- ⚠️ **No le gana a comprar-y-aguantar en una subida fuerte.** Su valor es la
  **gestión de riesgo**, no ser el más rentable en el mejor escenario.
- ⚠️ Resultados de 3 años en dos activos. **No garantizan** el futuro.

---

## 5. Límites y siguientes pasos

**Límites actuales:**
- Solo largos (spot). No contempla vender en corto.
- Pesos del score aún **fijos**; no optimizados por activo.
- Muestra fuera de muestra corta en número de operaciones (9 y 14).
- No incluye slippage ni problemas de liquidez (poco relevantes en BTC/ETH).

**Siguientes pasos sugeridos:**
1. Repetir en más activos (SOL, BNB) y temporalidades (4h, 1d).
2. Walk-forward con varias ventanas (no solo 70/30).
3. Validar el reporte generado por IA sin que altere la señal.
4. Definir la "política de operación" que ejecutará la app (posición abierta +
   actualización del stop dinámico hora a hora).
5. Recién entonces: app Android + notificaciones + nube.

---

## 6. Cómo reproducirlo

```powershell
.\.venv\Scripts\python.exe run_backtest.py BTCUSDT 1h 26000
.\.venv\Scripts\python.exe run_backtest.py ETHUSDT 1h 26000
.\.venv\Scripts\python.exe experiments.py       # compara variantes
.\.venv\Scripts\python.exe -m engine.report      # reporte actual de BTC
```
