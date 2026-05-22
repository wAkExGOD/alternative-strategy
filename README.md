# SYBAU Alternative Strategy

Реализация стратегии `Alternative Alpha Capture + Commercial Real Estate Stability Buffer` для коммерческой недвижимости с долгосрочной арендой.

## Идея

Стратегия строит портфель из двух основных блоков:

- `growth_real_estate` - объекты роста стоимости, редевелопмент и покупка недооцененных коммерческих объектов.
- `lease_income` - стабильная коммерческая недвижимость с долгосрочной арендой и Net Lease логикой.

Дополнительно используется `reit_hedge_short` - короткий хедж через ликвидные REIT/futures, когда быстрая волатильность публичного рынка недвижимости становится заметно выше медленной волатильности физической недвижимости.

Базовая аллокация из документа: 70% growth / 30% lease income. Модель меняет веса по сигналам occupancy, tenant score, cap rate, rent indexation, liquidity score и spread fast-vs-slow volatility.

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

- total return;
- annual volatility;
- Sharpe ratio;
- max drawdown;
- win rate;
- число ребалансировок;
- финальную стоимость портфеля;
- последний сигнал с целевыми весами и факторным breakdown.

Данные синтетические, потому что документ описывает частную коммерческую недвижимость, а не публичный единый тикер. Модель отражает заявленные в документе параметры: низкую волатильность физического актива, арендный cash flow, cap-rate сигнал и хедж через более волатильный публичный рынок недвижимости.
В бэктесте также учитывается дополнительная alpha-компонента от fast-vs-slow volatility spread при активном хедже, что соответствует тезису документа про arbitrage/capture разницы скоростей реакции рынков.
