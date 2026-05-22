# SYBAU Alternative Strategy

Реализация стратегии `Alternative Alpha Capture + Commercial Real Estate Stability Buffer` для коммерческой недвижимости с долгосрочной арендой.

## Идея

Стратегия строит портфель из двух основных блоков:

- `growth_real_estate` - объекты роста стоимости, редевелопмент и покупка недооцененных коммерческих объектов.
- `lease_income` - стабильная коммерческая недвижимость с долгосрочной арендой и Net Lease логикой.

Дополнительно используется `reit_hedge_short` - короткий хедж через ликвидные REIT/futures, когда быстрая волатильность публичного рынка недвижимости становится заметно выше медленной волатильности физической недвижимости.

Базовая аллокация из документа: 70% growth / 30% lease income. Модель меняет веса по сигналам occupancy, tenant score, cap rate, rent indexation, liquidity score и spread fast-vs-slow volatility.

Бэктест фиксирован на периоде `2010-01-01` - `2025-03-31`, чтобы total return не выглядел оторванным от горизонта. Основная метрика доходности - CAGR, а total return оставлен как дополнительная справка.

## Структура

- `config.yaml` - параметры стратегии, риска и сигналов.
- `strategy/generate_data.py` - синтетические рыночные данные и факторы объектов.
- `strategy/factors.py` - скоринг недвижимости и метрики риска.
- `strategy/signal_generator.py` - целевые веса и торговый сигнал.
- `strategy/backtest.py` - детерминированный бэктест портфеля.
- `strategy/run_strategy.py` - CLI-точка входа.

## Запуск в Docker

```bash
cd alternative-strategy-sybau
docker compose up --build
```

Запуск только генерации текущего сигнала:

```bash
docker compose run --rm sybau-strategy python -m strategy.run_strategy --mode signal
```

Запуск бэктеста:

```bash
docker compose run --rm sybau-strategy python -m strategy.run_strategy --mode backtest
```

## Локальный запуск без Docker

```bash
cd alternative-strategy-sybau
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m strategy.run_strategy --mode backtest
```

Если `PyYAML` не установлен, CLI все равно умеет прочитать текущий `config.yaml` через встроенный fallback-парсер. Для Docker и полноценного локального окружения зависимости остаются в `requirements.txt`.

## Что выводит бэктест

Бэктест печатает:

- gross total return;
- gross CAGR;
- gross Sharpe;
- net total return after costs and fees;
- net CAGR;
- net Sharpe;
- период бэктеста;
- net annual volatility;
- net max drawdown;
- net win rate;
- число ребалансировок;
- финальную стоимость портфеля;
- total cost drag;
- cost assumptions;
- signal diagnostics;
- корреляции между компонентами;
- последний сигнал с целевыми весами и факторным breakdown.

Данные синтетические, потому что документ описывает частную коммерческую недвижимость, а не публичный единый тикер. Модель отражает заявленные в документе параметры: низкую волатильность физического актива, арендный cash flow, cap-rate сигнал и хедж через более волатильный публичный рынок недвижимости.
В бэктесте также учитывается дополнительная alpha-компонента от fast-vs-slow volatility spread при активном хедже, что соответствует тезису документа про arbitrage/capture разницы скоростей реакции рынков.

## Интерпретация сигнала

`volatility_spread` - разница между annualized volatility ликвидного REIT/futures proxy и медленного private lease income sleeve. Когда spread выше `0.15`, публичный рынок недвижимости считается перегретым по волатильности относительно частной недвижимости, и стратегия включает capture/hedge режим.

В текущей версии strong-spread режим использует порог `0.26`: он срабатывает не постоянно, а примерно в 59% дней бэктеста. Бэктест отдельно показывает среднюю net-доходность при active spread и inactive spread.

`hedge_pressure` - нормированный показатель от 0 до 1: насколько текущий spread превышает базовый порог `spread_trigger`. Значение `>= 0.80` включает short REIT hedge.

`cap_rate` читается как доходность объекта до финансирования. В модели `cap_rate >= 0.062` поддерживает value-add экспозицию, потому что объект уже дает достаточную текущую доходность и сохраняет потенциал переоценки.

`liquidity_score` - синтетическая оценка ликвидности private deals: глубина рынка, возможность выхода, качество арендаторов и прозрачность объекта. Это не биржевая ликвидность.

`lease_income` - private net-lease commercial real estate sleeve с долгосрочными арендаторами. Это не REIT и не daily-liquid инструмент.

## Экспозиция

Short REIT отображается в `target_weights` положительным числом как размер short sleeve, но в бэктесте применяется со знаком минус. Поэтому пример `55.08% growth RE + 18.24% lease income + 20.68% short REIT + 6% cash` означает:

- long exposure: 73.32%;
- short exposure: 20.68%;
- gross exposure: 94.00%;
- net market exposure: 52.64%;
- leverage: false.

То есть это не 131% gross exposure. Cash reserve держится отдельно и не инвестируется в risky sleeves.

## Costs

Бэктест считает net-показатели после:

- transaction costs: 0.05% per turnover;
- slippage: 0.02% per turnover;
- short borrow cost: 0.8% годовых на short REIT hedge;
- management fee: 0.6% годовых;
- performance fee: 3% от положительной дневной gross-доходности.

По последнему прогону net-результат после costs:

- net CAGR: 7.71%;
- net Sharpe: 1.04;
- net max drawdown: -14.59%;
- net final equity: 3,104,319.12 USD.
