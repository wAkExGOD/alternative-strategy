# FAQ

## 1. Что делает код

Код реализует версию стратегии `Alternative Alpha Capture + Commercial Real Estate Stability Buffer`.

Идея стратегии: держать портфель коммерческой недвижимости, где часть капитала направлена в value-add/growth объекты, часть - в стабильный арендный cash flow, а часть используется как short hedge через ликвидный REIT/futures proxy, когда публичный рынок недвижимости становится намного волатильнее частной недвижимости.

Основные файлы:

- `config.yaml` - задает параметры стратегии: даты бэктеста, стартовый капитал, веса портфеля, риск-лимиты, пороги сигналов и издержки.
- `strategy/generate_data.py` - генерирует синтетические данные по трем компонентам:
  - `growth_real_estate`: коммерческая недвижимость с потенциалом роста стоимости;
  - `lease_income`: private net-lease объекты с долгосрочными арендаторами;
  - `reit_hedge`: ликвидный REIT/futures proxy для short hedge.
- `strategy/factors.py` - считает факторные оценки и метрики:
  - occupancy;
  - tenant score;
  - cap rate;
  - rent indexation;
  - liquidity score;
  - fast/slow volatility spread;
  - total return, CAGR, volatility, Sharpe, drawdown, win rate.
- `strategy/signal_generator.py` - превращает факторы в текущий сигнал:
  - выбирает действие стратегии;
  - рассчитывает целевые веса;
  - показывает long/short/gross/net exposure;
  - объясняет правила сигнала.
- `strategy/backtest.py` - прогоняет исторический синтетический бэктест:
  - ежедневно пересчитывает сигнал;
  - ребалансирует портфель, если отклонение от целевых весов выше порога;
  - считает gross return;
  - вычитает transaction costs, slippage, short borrow cost, management fee и performance fee;
  - выводит net-показатели после всех издержек.
- `strategy/run_strategy.py` - CLI-точка входа. Запускается в двух режимах:
  - `python -m strategy.run_strategy --mode backtest`
  - `python -m strategy.run_strategy --mode signal`

Важно: данные синтетические. Это нормально для учебного проекта, потому что стратегия описывает private commercial real estate, а не один публичный тикер. Синтетика нужна, чтобы показать логику модели, риск-контроль, fees/costs и интерпретацию сигнала.

## 2. Что означает вывод кода

### Верхний блок бэктеста

`Backtest period` - период, за который прогоняется стратегия. Сейчас это `2010-01-01 to 2025-03-31`, то есть 15.24 года.

`Gross total return` - общая доходность портфеля до издержек и комиссий за весь период.

`Gross CAGR` - среднегодовая доходность до издержек. CAGR удобнее total return, потому что учитывает длину периода.

`Gross Sharpe` - Sharpe ratio до издержек. Показывает доходность на единицу риска.

`Net total return` - общая доходность после всех издержек и комиссий.

`Net CAGR` - среднегодовая доходность после всех издержек и комиссий. Это главный показатель доходности стратегии.

`Net volatility` - годовая волатильность net-доходностей.

`Net Sharpe ratio` - Sharpe ratio после costs/fees. Это главный показатель risk-adjusted performance.

`Net max drawdown` - максимальная просадка net equity curve от локального максимума до минимума.

`Net win rate` - доля дней с положительной net-доходностью.

`Rebalances` - сколько раз портфель реально ребалансировался за период. Ребаланс происходит только если новые целевые веса отличаются от текущих больше, чем `rebalance_threshold`.

`Net final equity` - финальная стоимость портфеля после всех издержек и комиссий. Стартовый капитал задается в `config.yaml`.

`Total cost drag` - суммарный накопленный drag от комиссий, slippage, borrow costs и fees за весь период.

### Cost assumptions

`transaction_cost_per_turnover_pct` - комиссия за оборот портфеля при ребалансе. Например, 0.05 означает 0.05% на единицу turnover.

`slippage_per_turnover_pct` - модельная потеря на исполнении сделки: bid-ask spread, неидеальная цена входа/выхода.

`short_borrow_cost_annual_pct` - годовая стоимость short REIT hedge. Short-позиция не бесплатная, поэтому borrow cost вычитается из доходности.

`management_fee_annual_pct` - годовая management fee фонда.

`performance_fee_rate_pct` - performance fee с положительной дневной gross-доходности.

### Signal diagnostics

`spread_active_days_pct` - процент дней, когда raw volatility spread был выше strong-spread threshold. Это показывает, не является ли сигнал почти постоянным.

`cap_rate_rule_active_days_pct` - процент дней, когда cap rate был выше buy-threshold. Если показатель около 100%, threshold был бы бесполезен; текущая логика делает правило выборочным.

`avg_daily_net_return_when_spread_active_pct` - средняя дневная net-доходность в дни, когда spread-сигнал активен.

`avg_daily_net_return_when_spread_inactive_pct` - средняя дневная net-доходность в дни, когда spread-сигнал не активен.

### Component correlations

`growth_vs_reit_hedge` - корреляция доходностей growth real estate sleeve и REIT hedge proxy.

`lease_vs_reit_hedge` - корреляция lease income sleeve и REIT hedge proxy.

`growth_vs_lease` - корреляция growth real estate sleeve и lease income sleeve.

Эти поля нужны, чтобы показать, что short REIT hedge связан с real estate рынком, но не является полной копией private real estate.

### Latest signal

`strategy` - название стратегии.

`timestamp` - время генерации сигнала.

`action` - текущее действие модели:

- `CAPTURE_VOLATILITY_SPREAD`: активен режим заработка на spread между быстрой волатильностью REIT/futures и медленной волатильностью private real estate;
- `HEDGE_AND_HOLD`: hedge включен, но spread-сигнал менее сильный;
- `ADD_VALUE_ADD_EXPOSURE`: условия поддерживают увеличение value-add exposure;
- `HOLD_CORE_PORTFOLIO`: держим базовую структуру портфеля.

### target_weights

`growth_real_estate` - доля портфеля в value-add/growth commercial real estate.

`lease_income` - доля портфеля в private net-lease commercial real estate с долгосрочными арендаторами.

`reit_hedge_short` - размер short hedge через REIT/futures proxy. В выводе это положительное число как размер short sleeve, но в бэктесте оно применяется со знаком минус.

`cash_reserve` - доля портфеля в кэше. Она не инвестируется в risky sleeves.

### exposure

`long_exposure` - сумма long-позиций: growth real estate плюс lease income.

`short_exposure` - размер short REIT hedge.

`gross_exposure` - сумма long и short exposure по модулю. Если gross exposure меньше или равен 1, скрытого плеча нет.

`net_market_exposure` - long exposure минус short exposure. Показывает чистую направленную рыночную экспозицию.

`uses_leverage` - использует ли стратегия leverage. Сейчас `false`.

### signal_logic

`volatility_spread_rule` - объясняет правило spread: если волатильность REIT/futures значительно выше волатильности private real estate, стратегия включает volatility-spread capture.

`hedge_pressure_rule` - объясняет, когда активируется short REIT hedge. `hedge_pressure` нормируется от 0 до 1 и может быть capped at 1.0.

`cap_rate_rule` - объясняет cap-rate правило. Если cap rate выше порога, объект считается достаточно доходным для value-add exposure.

`hold_period_rationale` - объясняет, почему используется горизонт 12 месяцев: private real estate нельзя честно трактовать как daily-liquid asset.

`lease_income_definition` - уточняет, что `lease_income` - это private net-lease sleeve, а не биржевой REIT.

### scores

`stability_score` - агрегированная оценка стабильности портфеля. Учитывает occupancy, tenant score, rent indexation и liquidity score.

`alpha_score` - оценка потенциала дополнительной доходности. Учитывает cap rate, rent indexation и liquidity score.

`hedge_pressure` - нормированная сила hedge/spread сигнала от 0 до 1. Значение `1.0` означает capped максимум шкалы, а не 100% вероятность.

`fast_volatility` - годовая волатильность ликвидного REIT/futures proxy.

`slow_volatility` - годовая волатильность lease income/private real estate sleeve.

`volatility_spread` - разница между fast volatility и slow volatility. Чем больше spread, тем сильнее идея volatility-spread capture.

### scores.breakdown

`occupancy` - уровень заполняемости объектов арендаторами.

`tenant_score` - качество арендаторов: устойчивость, платежеспособность, надежность lease cash flow.

`cap_rate` - текущая доходность объекта до финансирования. Например, `0.0668` означает 6.68%.

`rent_indexation` - индексация арендных ставок, то есть защита cash flow от инфляции.

`liquidity_score` - оценка ликвидности private deals: качество выхода, глубина рынка, прозрачность объекта и возможность продать позицию.
