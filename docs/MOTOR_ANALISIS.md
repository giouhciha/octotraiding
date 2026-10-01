# OctoTrading — Motor de Análisis ("el experto en el bolsillo")

> Este documento define **cómo piensa** la app. Es la parte central del proyecto:
> de aquí sale la recomendación de comprar/vender. La infraestructura (AWS, etc.)
> es secundaria; esto es el volante.

Estado: **Definición técnica (pre-código)**
Fecha: 2026-10-01

---

## 0. Contrato de honestidad (leer primero)

El usuario final **no sabe de trading** y confiará en la app. Por eso:

- La app **no predice** el futuro. Evalúa la **situación actual** del mercado con
  un método consistente y traduce esa evaluación a lenguaje simple.
- La app **nunca promete rentabilidad** ni dice "esto va a subir".
- La app **siempre** comunica el **riesgo** (dónde está el stop) junto con la idea.
- La app **no actúa sola**: sugiere y explica; el usuario decide.
- La app deja claro que **no es asesoría financiera**.

> Lema interno: *"No te digo qué va a pasar. Te digo qué está pasando,
> qué haría un analista disciplinado, y cuánto puedes perder si se equivoca."*

---

## 1. Qué significa "experto en el bolsillo"

No es un oráculo. Es un **analista metódico disponible 24/7** que:

1. **Vigila** un activo cada hora por ti.
2. **Evalúa** tendencia, fuerza, volatilidad y volumen con indicadores estándar.
3. **Filtra** señales contradictorias (evita el ruido).
4. **Sugiere** una acción: COMPRAR / MANTENER / VENDER / ESPERAR.
5. **Explica el porqué** en 3–5 frases que cualquiera entiende.
6. **Define el riesgo**: dónde salir si se equivoca (stop loss) y con cuánto capital.
7. **Te avisa** solo cuando algo relevante cambia.

La ventaja del "experto" no es adivinar: es **no improvisar, no dejarse llevar por
el miedo o la codicia, y siempre gestionar el riesgo**. Eso es lo que un humano
novato hace mal y una máquina hace bien.

---

## 2. Principios de diseño del motor

1. **Los números deciden; el LLM solo explica.** La IA de texto nunca inventa una
   señal distinta a la calculada.
2. **Consistencia > creatividad.** Mismas reglas siempre, para bien y para mal.
3. **Contexto antes que señal.** Primero se determina el *régimen* del mercado;
   luego se aplican las reglas que corresponden a ese régimen.
4. **El riesgo manda.** No hay señal de compra sin stop loss y ratio riesgo/beneficio.
5. **Nada es verdad hasta backtestearlo.** Los pesos iniciales son hipótesis.
6. **Explicabilidad total.** Cada punto del score debe poder rastrearse a una regla.

---

## 3. Pipeline del análisis (se ejecuta cada hora)

```
1. Obtener velas OHLCV      → 1h (200), 4h (200), 1d (200)
2. Calcular indicadores      → EMA, MACD, RSI, Stoch, ADX, Bollinger, ATR, OBV, volumen
3. Detectar régimen          → ¿mercado en TENDENCIA o en RANGO?
4. Calcular score            → suma ponderada de factores (-10 a +10)
5. Traducir a señal          → COMPRA / MANTENER / VENDER / ESPERAR
6. Calcular niveles          → entrada, stop loss, take profit, R:R, tamaño de posición
7. Generar narrativa (LLM)   → texto en lenguaje llano a partir del JSON
8. Guardar reporte           → historial
9. Comparar con señal previa → decidir si se notifica o no
```

---

## 4. Detección de régimen (el "contexto")

Este paso evita el error clásico: aplicar reglas de tendencia en un mercado
lateral, o reglas de rebote en una tendencia fuerte.

**Indicadores de régimen:**
- **EMA 200 (1h):** precio por encima = sesgo alcista; por debajo = bajista.
- **ADX (14):** mide fuerza de tendencia.
  - ADX ≥ 25 → **TENDENCIA**
  - ADX < 20 → **RANGO**
  - 20–25 → **TRANSICIÓN** (se trata con cautela, señales suavizadas)

**Qué cambia según el régimen:**

| Régimen | Filosofía | Ejemplo |
|---------|-----------|---------|
| **TENDENCIA** | Seguir la corriente; comprar retrocesos | Precio sube, esperar que caiga un poco y comprar a favor de la EMA |
| **RANGO** | Comprar abajo, vender arriba | Precio rebota entre soporte y resistencia |
| **TRANSICIÓN** | Máxima prudencia | Señales débiles, muchas veces "ESPERAR" |

> Esto es lo que separa a un novato (usa una sola receta para todo) de un analista
> (usa la receta que corresponde al momento).

---

## 5. Indicadores seleccionados (y por qué)

Solo indicadores **estándar, públicos y bien entendidos**. Nada exótico.

| Categoría | Indicador | Qué mide (en simple) |
|-----------|-----------|----------------------|
| Tendencia | EMA 20 / 50 / 200 | Dirección y fuerza del movimiento |
| Tendencia | MACD (12,26,9) | Cambios de impulso y cruces |
| Tendencia | ADX (14) | ¿Hay tendencia o está plano? |
| Momentum | RSI (14) | ¿Está caro (sobrecompra) o barato (sobreventa)? |
| Momentum | Stochastic (14,3,3) | Momentum de corto plazo |
| Volatilidad | Bandas de Bollinger (20,2) | Zona "normal" y extremos del precio |
| Volatilidad | ATR (14) | Cuánto se mueve el precio (para el stop) |
| Volumen | OBV | ¿El volumen respalda el movimiento? |
| Volumen | Volumen medio (20) | Detectar picos anómalos |
| Estructura | Pivotes / swings | Soportes y resistencias reales |

Temporalidades:
- **1h** = decisión principal.
- **4h** y **1d** = contexto/confirmación (si 1h dice compra pero 1d es bajista, se penaliza).

---

## 6. Sistema de puntuación (el corazón)

Cada factor produce un sub-score entre **-1 y +1**. Se multiplica por su **peso**
y se suman. El resultado final va de **-10 a +10**.

### 6.1 Factores y pesos (v1 — hipótesis a validar)

| Factor | Peso | Qué evalúa | Ejemplo de regla (régimen tendencia) |
|--------|------|-----------|--------------------------------------|
| **Tendencia** | 3.0 | EMA20/50/200, pendiente | Precio > EMA200 (+), EMA20 > EMA50 (+), pendientes al alza |
| **Momentum** | 2.5 | RSI, Stoch, MACD hist. | RSI 40–60 con MACD girando al alza (+), RSI > 75 (−) |
| **Volumen** | 1.5 | OBV, pico de volumen | OBV sube y volumen confirma la vela (+) |
| **Volatilidad** | 1.5 | Posición en Bollinger, ATR | Precio en banda inferior sin pánico (+), ATR expandiéndose con caída (−) |
| **Estructura** | 1.5 | Soportes/resistencias, swings | Cerca de soporte con mechas de rechazo (+) |
| **Total** | **10.0** | | |

> **Modo RANGO:** Momentum y Estructura invierten su lógica (sobreventa = comprar,
> sobrecompra = vender), porque en lateral el precio tiende a volver al centro.

### 6.2 Ejemplo de cálculo (ilustrativo)

```
Tendencia    +0.8 × 3.0 = +2.4   (precio sobre EMA200, EMAs alineadas)
Momentum     +0.5 × 2.5 = +1.25  (RSI 52 subiendo, MACD a punto de cruzar)
Volumen      +0.3 × 1.5 = +0.45  (volumen normal, OBV levemente al alza)
Volatilidad  +0.6 × 1.5 = +0.9   (precio cerca de banda inferior, sin pánico)
Estructura   +0.4 × 1.5 = +0.6   (cerca de soporte con rechazo)
                                    ─────
                          SCORE  = +5.6  → COMPRA
```

---

## 7. Traducción de score a señal

| Score | Señal | Lectura para el usuario |
|-------|-------|-------------------------|
| +6 a +10 | **COMPRA FUERTE** | "El contexto favorece comprar; riesgo definido." |
| +3 a +5.9 | **COMPRA** | "Se puede considerar comprar de forma prudente." |
| -2.9 a +2.9 | **ESPERAR / MANTENER** | "No hay ventaja clara. Si ya tienes, mantén." |
| -5.9 a -3 | **VENTA** | "Conviene reducir o vender." |
| -10 a -6 | **VENTA FUERTE** | "El contexto favorece salir." |

Además, **filtros de seguridad** que pueden anular una señal:
- Si el **R:R < 1.5** → no se emite COMPRA (aunque el score la pida).
- Si la volatilidad es **anormalmente alta** (ATR spike) → señal atenuada a ESPERAR.
- Si **1d contradice fuerte** a 1h → compra degradada a ESPERAR.

---

## 8. Niveles y gestión de riesgo (lo que salva al usuario)

Cada señal de COMPRA/VENTA incluye **siempre**:

- **Precio de entrada** sugerido (o zona de entrada escalonada).
- **Stop loss**: dónde reconocer que la idea falló.
  - *Long:* `entrada − 2×ATR` al abrir.
  - **Stop dinámico:** después sube a `máximo alcanzado − 3×ATR` y nunca baja.
- **Take profit**: `entrada + 3×ATR` o próxima resistencia relevante.
- **Ratio Riesgo/Beneficio (R:R)**: objetivo mínimo 1.5.
- **Tamaño de posición sugerido**:
  `capital × %riesgo_por_operación / (entrada − stop)`
  Ejemplo: con $1.000 y 1% de riesgo, si el stop está a 2% del precio,
  la posición sugerida es de $500. *(El usuario define su capital y su % de riesgo;
  por defecto 1%.)*

> Sin esta sección, una señal es un volado disfrazado de análisis. Con esta sección,
> incluso una señal equivocada tiene un costo controlado.

---

## 8.b Política de operación validada (v1, respaldada por backtesting)

Resultado de probar el motor con 3 años de datos reales (ver
[`docs/BACKTEST_RESULTS.md`](./BACKTEST_RESULTS.md)). Es la regla que la app
aplicará y notificará:

**Entrada (comprar) — solo si se cumplen AMBAS:**
1. Señal **COMPRA FUERTE** (score ≥ +6).
2. La **tendencia diaria NO es bajista** (no se compra contra corriente).

**Salida (vender) — lo que ocurra primero:**
1. **Stop dinámico** alcanzado: el stop sube con el precio (a 3× ATR) y nunca baja.
   Este es el motor de las ganancias: corta las pérdidas y deja correr los aciertos.
2. Señal **VENTA FUERTE** (score ≤ −6).

**Riesgo:** 1% del capital por operación (perfil moderado).

**Observaciones de los resultados:**
- Tasa de acierto ~38%: baja a propósito. El sistema gana poco muchas veces y
  mucho pocas veces (así funcionan los métodos que dejan correr las ganancias).
- No busca superar a "comprar y aguantar" en subidas fuertes; busca **proteger el
  capital** en caídas. En el tramo bajista, el mercado perdió ~20% y la estrategia
  ganó.

> Importante: el stop dinámico **debe actualizarse cada hora**. La app lleva la
> cuenta de la posición abierta y avisa cuando el stop sube o se activa.

---

## 9. El reporte (cómo se lo explica al usuario)

El LLM recibe un **JSON estructurado** (precio, indicadores, régimen, score, niveles)
y devuelve texto llano. El LLM **no puede** cambiar el número ni la señal.

### Plantilla del reporte

```
📊 BTC/USDT — hace 5 min
Precio: $61.450  |  Señal: COMPRA (score +5.6)

QUÉ ESTÁ PASANDO
El precio viene subiendo por encima de sus medias largas (tendencia al alza).
El RSI está en 52, ni caro ni barato, y el volumen empieza a acompañar.

QUÉ SUGIERE EL MÉTODO
Comprar de forma prudente. El momento aún no es "fuerte" porque el volumen
todavía es normal, no alto.

SI DECIDES ENTRAR
  Entrada sugerida:  $61.450
  Stop loss:         $59.800  (si cae aquí, la idea falló)
  Objetivo:          $64.650
  Riesgo/Beneficio:  1 : 1.9
  Con 1% de riesgo sobre $1.000 → posición sugerida de ~$600.

RIESGOS A VIGILAR
- El volumen no ha confirmado del todo.
- La tendencia en 1d es más débil.

⚠️ Esto es análisis técnico automatizado, no asesoramiento financiero.
```

Reglas del prompt:
- Prohibido usar palabras como "seguro", "garantizado", "va a subir".
- Siempre incluir el bloque de riesgo.
- Máximo 120 palabras.
- Tono claro, sin jerga (o con jerga explicada entre paréntesis).

---

## 10. Notificaciones (anti-spam)

Se notifica **solo** si:
1. La señal entra o sale de **COMPRA FUERTE o VENTA FUERTE** (score ±6), o
2. Se **alcanza el stop o el take profit** de una señal previa.

> Configuración acordada: **solo señales fuertes**. Los cambios a señales
> moderadas (COMPRA / VENTA / ESPERAR) se guardan en el historial, pero **no
> generan notificación**.

Límites:
- Máximo 1 notificación por activo por hora.
- Horario de silencio configurable (ej. 23:00–07:00).
- Si no hay cambio → **no se notifica**, aunque se guarde el reporte.

---

## 11. Backtesting (cómo sabremos si el "experto" sirve)

> ✅ **Primera ronda completada** (BTC y ETH, 3 años). Ver resultados en
> [`docs/BACKTEST_RESULTS.md`](./BACKTEST_RESULTS.md). El motor resultó rentable y
> consistente fuera de muestra, con bajo drawdown. La política de la sección 8.b
> es su consecuencia.

**Nada** de los pesos anteriores se da por bueno hasta probarlo con datos históricos.

- **Datos:** 2–3 años de velas reales del activo.
- **Simulación:** recorrer el histórico hora a hora, generar la señal con las
  mismas reglas y simular la operación (entrada, stop, objetivo, comisiones).
- **Métrica clave:** resultar rentable **después** de comisiones y con drawdown
  controlado, no solo "acertar".

### Métricas que reportaremos
| Métrica | Qué significa | Objetivo sano |
|---------|---------------|---------------|
| Win rate | % de operaciones ganadoras | 45–60% (no necesitas 90%) |
| Profit factor | ganancias / pérdidas | > 1.3 |
| Max drawdown | peor caída desde el máximo | < 20–25% |
| Ratio R:R medio | ganancia media / pérdida media | > 1.5 |
| Nº de operaciones | muestra suficiente | > 100 |

### Anti-overfitting
- **Walk-forward**: optimizar en un periodo, validar en otro que el modelo no vio.
- **Out-of-sample**: dejar los últimos meses apartados y no tocarlos hasta el final.
- Si una configuración bonita en el pasado falla en el futuro → era sobreajuste.

> Este paso es **obligatorio** antes de decir que las señales son confiables.
> Sin backtesting, son corazonadas con buena presentación.

---

## 12. Gobernanza: qué decide cada parte

| Parte | Decide | NO puede |
|-------|--------|----------|
| **Indicadores** | Los números | — |
| **Score + reglas** | La señal (COMPRA/VENTA/…) | Ignorar los filtros de riesgo |
| **Módulo de riesgo** | Entrada, stop, objetivo, tamaño | Emitir compra sin stop |
| **LLM** | El texto explicativo | Cambiar número, señal o niveles |
| **Usuario** | Si opera o no, y su capital | — |

---

## 13. Limitaciones y expectativas honestas

- **No es predicción.** Acierta a veces y falla a veces; el sistema gana si el
  conjunto es rentable, no cada operación.
- **Las señales no son consejos financieros.** El usuario es responsable.
- **Los mercados cambian.** Un método que funcionó en 2021 puede fallar en 2026;
  por eso hay re-validación periódica (v3).
- **El pasado no garantiza el futuro.** El backtesting reduce la incertidumbre,
  no la elimina.
- **Empezar simple.** Reglas claras > machine learning opaco, hasta tener datos.

---

## 14. Evolución por versiones

| Versión | Motor |
|---------|-------|
| **v1** | Reglas fijas + pesos definidos aquí + backtest básico |
| **v2** | Ajuste de pesos por activo, watchlist multi-activo, más regímenes |
| **v3** | Modelos estadísticos / ML, re-entrenamiento, detección de anomalías |
| **v4** | (Opcional) Ejecución automática en exchange, con controles estrictos |

---

## 15. Decisiones que tomo por defecto (y puedo cambiar)

| Tema | Default | Motivo |
|------|---------|--------|
| Timeframe de decisión | 1h | Es lo pedido; buen balance ruido/velocidad |
| Contexto | 4h y 1d | Confirmación |
| Riesgo por operación | 1% del capital | Estándar conservador |
| R:R mínimo para comprar | 1.5 | No operar ventajas pequeñas |
| Stop | 2 × ATR | Se adapta a la volatilidad de cada activo |
| Activo inicial | BTC/USDT | Mayor liquidez y datos limpios |

## 16. Configuración acordada con el usuario (2026-10-01)

| Tema | Decisión | Efecto en el motor |
|------|----------|--------------------|
| **Perfil de riesgo** | **Moderado** | Umbrales intermedios; riesgo por operación 1%; R:R mínimo 1.5 |
| **Frecuencia de avisos** | **Solo señales fuertes** | Notifica únicamente al entrar/salir de COMPRA FUERTE o VENTA FUERTE (score ±6) o al tocar stop/objetivo |
| **Silencio nocturno** | **23:00 a 07:00** | En esa franja no se envían push; se acumulan en el historial |
| **Tamaño de posición** | *Pendiente* | El usuario lo definirá más adelante; por defecto se usa 1% de riesgo |

### Perfil de riesgo — cómo se traduce (moderado)

| Parámetro | Conservador | **Moderado (elegido)** | Agresivo |
|-----------|-------------|------------------------|----------|
| Umbral COMPRA/VENTA | ±4 | **±3** | ±2 |
| Umbral señal FUERTE | ±7 | **±6** | ±5 |
| Riesgo por operación | 0.5% | **1%** | 2% |
| R:R mínimo | 2.0 | **1.5** | 1.2 |
| Avisos | solo fuertes | **solo fuertes** | todos |

---

## 17. Rol del equipo (acordado)

- **El agente (yo):** diseñar el motor, elegir indicadores y pesos, escribir todo
  el código del backend y de la app, montar el backtesting y explicar cada
  decisión en lenguaje llano.
- **El usuario:** definir preferencias con opciones simples (riesgo, avisos,
  horario), validar que los reportes se entiendan, y decidir sobre su dinero.
  **El usuario no escribe código ni necesita saber de trading.**

> Guía de comunicación: evitar jerga; cuando aparezca un término técnico,
> explicarlo en una frase entre paréntesis.

---

## 18. Preguntas pendientes (sin bloqueo)

1. **Capital de referencia:** solo para calcular tamaño de posición; no se conecta
   a ningún banco ni se mueve dinero. Se puede definir después.
2. **Nombre y branding** de la app.
3. **Restricciones legales** según el país donde se publique.
