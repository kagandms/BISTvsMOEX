"""
Configuration module for The Eurasian Bridge application.
Loads settings from config.yaml and provides constants.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_MIN_TIMEOUT_SECONDS = 1
_MAX_TIMEOUT_SECONDS = 120
_MIN_MOEX_DELAY_DAYS = 1
_MAX_MOEX_DELAY_DAYS = 14
_DEFAULT_SENTRY_TRACES_SAMPLE_RATE = 0.1


def _read_bounded_int_env(
    env_name: str,
    *,
    minimum: int,
    maximum: int,
) -> int | None:
    """Return a validated integer environment override."""

    raw_value = os.environ.get(env_name)
    if raw_value is None:
        return None

    try:
        parsed_value = int(raw_value)
    except ValueError:
        logger.warning(
            "Ignoring invalid %s value %r; expected an integer.",
            env_name,
            raw_value,
        )
        return None

    if parsed_value < minimum or parsed_value > maximum:
        logger.warning(
            "Ignoring invalid %s value %r; expected an integer in [%d, %d].",
            env_name,
            raw_value,
            minimum,
            maximum,
        )
        return None

    return parsed_value


def get_sentry_traces_sample_rate(
    default: float = _DEFAULT_SENTRY_TRACES_SAMPLE_RATE,
) -> float:
    """Return a validated Sentry trace sample rate."""

    env_name = "BM_SENTRY_TRACE_SAMPLE_RATE"
    raw_value = os.environ.get(env_name)
    if raw_value is None:
        return default

    try:
        sample_rate = float(raw_value)
    except ValueError:
        logger.warning(
            "Ignoring invalid %s value %r; expected a float in [0.0, 1.0].",
            env_name,
            raw_value,
        )
        return default

    if sample_rate < 0 or sample_rate > 1:
        logger.warning(
            "Ignoring invalid %s value %r; expected a float in [0.0, 1.0].",
            env_name,
            raw_value,
        )
        return default

    return sample_rate


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml file and apply environment overrides."""

    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise RuntimeError(
                f"Failed to parse configuration file {config_path}: {exc}"
            ) from exc

    if not isinstance(config, dict):
        raise RuntimeError(
            f"Configuration file {config_path} must contain a YAML mapping, "
            f"got {type(config).__name__}"
        )

    timeout = _read_bounded_int_env(
        "BM_TIMEOUT",
        minimum=_MIN_TIMEOUT_SECONDS,
        maximum=_MAX_TIMEOUT_SECONDS,
    )
    if timeout is not None and "api" in config and "moex_iss" in config["api"]:
        config["api"]["moex_iss"]["timeout_seconds"] = timeout

    delay = _read_bounded_int_env(
        "BM_MOEX_DELAY",
        minimum=_MIN_MOEX_DELAY_DAYS,
        maximum=_MAX_MOEX_DELAY_DAYS,
    )
    if delay is not None and "data" in config:
        config["data"]["moex_delay_days"] = delay

    return config


# Load config at module level
CONFIG = load_config()

# Convenience accessors
SECTORS = CONFIG["sectors"]
COLORS = CONFIG["colors"]
API_CONFIG = CONFIG["api"]
DATA_CONFIG = CONFIG["data"]
CACHE_CONFIG = CONFIG["cache"]
APP_CONFIG = CONFIG["app"]
MARKET_CAPS = CONFIG.get("market_caps", {})
MARKET_CAP_METADATA = CONFIG.get("market_cap_metadata", {})
INFLATION_CONFIG = CONFIG.get("inflation_adjustment", {})

# Macro economic events for chart annotations
MACRO_EVENTS = CONFIG.get("macro_events", [])

# Translations dictionary (kept in Python for complex string formatting)
TRANSLATIONS = {
    "en": {
        "app_title": "🌉 The Eurasian Bridge",
        "app_subtitle": "BIST (Turkey) vs. MOEX (Russia) | Cross-Market Sector Analysis",
        "sector_analysis": "Sector Analysis",
        "select_sector": "📊 Select Sector",
        "sector_help": "Choose a sector to compare Turkish and Russian market leaders",
        "analysis_options": "💱 Currency Settings",
        "analysis_period": "📅 Analysis Period",
        "start": "Start",
        "end": "End",
        "current_pair": "CURRENT PAIR",
        "turkey": "Turkey",
        "russia": "Russia",
        "data_source": "Data: Yahoo Finance, MOEX ISS API & curated CPI snapshots",
        "built_with": "Built with Streamlit",
        "current_metrics": "📈 Current Metrics",
        "tr_period_change": "TR Period Change",
        "ru_period_change": "RU Period Change",
        "sim_label": "(Sim)",
        "normalized_performance": "📊 Normalized Performance",
        "correlation_analysis": "🔗 Correlation Analysis",
        "pearson_correlation": "Pearson Correlation Coefficient",
        "interpretation_guide": "📝 Interpretation Guide",
        "interpretation_text": """The Pearson correlation coefficient measures the linear relationship between daily returns of both assets.
        <br><br>
        <strong>Values range from -1 to +1:</strong><br>
        • <strong>+0.7 to +1.0:</strong> Strong positive — assets tend to move together<br>
        • <strong>+0.4 to +0.7:</strong> Moderate positive — some co-movement exists<br>
        • <strong>-0.4 to +0.4:</strong> Weak or no correlation — independent movements<br>
        • <strong>-0.7 to -0.4:</strong> Moderate negative — assets often move in opposite directions<br>
        • <strong>-1.0 to -0.7:</strong> Strong negative — inverse relationship""",
        "footer_title": "The Eurasian Bridge Analyzer | Comparative Financial Analysis Tool",
        "footer_disclaimer": "Data for demonstration purposes. Not financial advice.",
        "fetching_data": "Fetching market data...",
        "error_timeout": "⏱️ Connection timed out. Please try again.",
        "error_connection": "🔌 Connection error. Check your internet or API status.",
        "error_schema": "⚠️ Upstream response format changed. Please try again later.",
        "error_no_data": "📉 No trading data found for {ticker} in this period (possible holiday/delisting).",
        "error_insufficient": "⚠️ Insufficient data points for {ticker} to perform analysis.",
        "error_unsupported_window": "⚠️ The selected date range is unsupported.",
        "error_conversion_incomplete": "⚠️ USD comparison is unavailable because both FX series did not cover the selected window safely.",
        "error_inflation_incomplete": "⚠️ Real comparison is unavailable because CPI coverage did not safely cover the selected window.",
        "data_unavailable": "⚠️ Data unavailable for {ticker}. Try selecting an earlier end date (MOEX data has 1-2 day delay).",
        "date_adjusted": "⚠️ Using data until {actual_date} (selected: {requested_date}) - latest available data",
        "moex_live": "✅ Live data from MOEX ISS API",
        "bist_live": "✅ Live data from Yahoo Finance",
        "no_data_error": "Unable to load data. Please adjust date range.",
        "metric_unavailable": "Unavailable",
        "chart_title": "Normalized Performance Comparison (Rebased to 100)",
        "date_axis": "Date",
        "value_axis": "Normalized Value",
        "base_label": "Base = 100",
        "usd_conversion_partial": "⚠️ USD comparison is limited to the shared FX-covered window: {start_date} - {end_date}.",
        "comparison_window_partial": "⚠️ Comparison is limited to the shared trading window: {start_date} - {end_date}.",
        "comparison_window_unavailable": "⚠️ Shared USD-covered history is too short for a safe comparison.",
        "comparison_window_unavailable_local": "⚠️ The two assets do not share enough trading days for a safe comparison.",
        "correlation_unavailable": "⚠️ Correlation could not be calculated safely for this window.",
        "chart_unavailable": "⚠️ The normalized comparison chart is unavailable for this window.",
        "language": "🌐 Language",
        "start_price_label": "Start: {currency}{price} ({date})",
        "date_error": "⚠️ Start date must be before end date. Please adjust the date range.",
        "analysis_mode": "Comparison Mode",
        "analysis_mode_help": "Choose whether to compare nominal local prices, USD-converted prices, or CPI-adjusted real prices.",
        "mode_local": "Local Currency",
        "mode_usd": "USD",
        "mode_real": "Real (CPI-adjusted)",
        # Sector names
        "sector_aviation": "Aviation",
        "sector_energy": "Energy",
        "sector_banking": "Banking",
        "sector_retail": "Retail",
        "sector_steel": "Steel",
        # Sector descriptions
        "aviation_desc": "Geopolitical Risks & Tourism",
        "energy_desc": "Supply Chain & Refining",
        "banking_desc": "Interest Rates & Monetary Policy",
        "retail_desc": "Inflation & Consumer Behavior",
        "steel_desc": "Global Industrial Cycles",
        # Correlation interpretations
        "strong_positive": "Strong Positive Correlation",
        "moderate_positive": "Moderate Positive Correlation",
        "weak_positive": "Weak Positive Correlation",
        "no_correlation": "No Significant Correlation",
        "weak_negative": "Weak Negative Correlation",
        "moderate_negative": "Moderate Negative Correlation",
        "strong_negative": "Strong Negative Correlation",
        "insufficient_data": "Insufficient data",
        # Risk metrics
        "volatility": "Volatility (Ann.)",
        "sharpe_ratio": "Sharpe Ratio",
        "max_drawdown": "Max Drawdown",
        "cagr": "CAGR",
        # Risk metrics section
        "risk_metrics": "Risk Metrics",
        "risk_summary_title": "Risk Metric Quick Guide",
        "risk_summary_intro": "These metrics complement headline returns by showing volatility, downside depth, and return quality.",
        "volatility_summary": "Annualized return dispersion. Higher values mean wider price swings and less stable behavior.",
        "sharpe_ratio_summary": "Risk-adjusted return per unit of volatility. Higher values usually indicate better efficiency.",
        "max_drawdown_summary": "Largest peak-to-trough loss within the selected period. More negative values signal deeper downside risk.",
        "cagr_summary": "Smoothed annualized growth rate between the first and last observation. Useful for long-horizon comparisons.",
        # USD conversion
        "show_usd": "Show Prices in USD ($)",
        "show_usd_help": "Convert prices to USD for fair comparison (enables inflation-adjusted view)",
        "usd_conversion_active": "USD Conversion Active - All values in USD",
        "general_overview": "General Overview",
        "usd_conversion_unavailable": "USD conversion unavailable because one or more FX series could not be loaded. Local currency view is shown instead.",
        "real_conversion_active": "Real mode active - Values are shown in {base_month} purchasing power.",
        "real_conversion_partial": "⚠️ Real comparison is limited to the CPI-covered window: {start_date} - {end_date} ({base_month} purchasing power).",
        "real_conversion_unavailable": "⚠️ Real comparison is unavailable because the curated CPI snapshot does not fully cover the selected window.",
        "market_cap_comparison": "Market Cap Comparison",
        "market_cap_source_note": "Source: curated snapshot from config.yaml (as of {as_of}).",
        "market_cap_snapshot_disclaimer": "Snapshot-based values support presentation consistency and may differ from live exchange values.",
        "market_cap_unavailable": "Comparison unavailable due to missing market-cap data.",
        "market_cap_leader": "{market} leads by {multiple}.",
        "ytd_performance": "YTD Performance ({year})",
        "leader_label": "Leader",
        "tie_label": "Tie",
        "methodology_title": "Methodology & Limitations",
        "methodology_point_1": "Daily close prices are fetched from Yahoo Finance for BIST and the official MOEX ISS REST API for MOEX.",
        "methodology_point_2": "MOEX data can lag the selected end date by 1-2 trading days.",
        "methodology_point_3": "USD mode aligns FX series to trading days and forward-fills missing exchange-rate observations.",
        "methodology_point_4": "The comparison chart rebases each asset to 100 on the first available point in the analysis window.",
        "methodology_point_5": "Real mode deflates daily prices with curated monthly CPI change snapshots and uses the latest shared published month as the purchasing-power anchor.",
        "methodology_point_6": "Correlation is calculated on daily returns, while market-cap values use a curated snapshot for presentation consistency.",
    },
    "tr": {
        "app_title": "🌉 Avrasya Köprüsü",
        "app_subtitle": "BIST (Türkiye) vs. MOEX (Rusya) | Sektörler Arası Piyasa Analizi",
        "sector_analysis": "Sektör Analizi",
        "select_sector": "📊 Sektör Seçin",
        "sector_help": "Türk ve Rus piyasa liderlerini karşılaştırmak için bir sektör seçin",
        "analysis_options": "💱 Para Birimi Ayarları",
        "analysis_period": "📅 Analiz Dönemi",
        "start": "Başlangıç",
        "end": "Bitiş",
        "current_pair": "MEVCUT ÇİFT",
        "turkey": "Türkiye",
        "russia": "Rusya",
        "data_source": "Veri: Yahoo Finance, MOEX ISS API ve kürasyonlu TÜFE snapshot'ları",
        "built_with": "Streamlit ile geliştirilmiştir",
        "current_metrics": "📈 Güncel Metrikler",
        "tr_period_change": "TR Dönem Değişimi",
        "ru_period_change": "RU Dönem Değişimi",
        "sim_label": "(Sim)",
        "normalized_performance": "📊 Normalize Edilmiş Performans",
        "correlation_analysis": "🔗 Korelasyon Analizi",
        "pearson_correlation": "Pearson Korelasyon Katsayısı",
        "interpretation_guide": "📝 Yorumlama Kılavuzu",
        "interpretation_text": """Pearson korelasyon katsayısı, her iki varlığın günlük getirileri arasındaki doğrusal ilişkiyi ölçer.
        <br><br>
        <strong>Değerler -1 ile +1 arasında değişir:</strong><br>
        • <strong>+0.7 ile +1.0:</strong> Güçlü pozitif — varlıklar birlikte hareket etme eğilimindedir<br>
        • <strong>+0.4 ile +0.7:</strong> Orta pozitif — bir miktar birlikte hareket vardır<br>
        • <strong>-0.4 ile +0.4:</strong> Zayıf veya korelasyon yok — bağımsız hareketler<br>
        • <strong>-0.7 ile -0.4:</strong> Orta negatif — varlıklar genellikle zıt yönde hareket eder<br>
        • <strong>-1.0 ile -0.7:</strong> Güçlü negatif — ters ilişki""",
        "footer_title": "Avrasya Köprüsü Analizörü | Karşılaştırmalı Finansal Analiz Aracı",
        "footer_disclaimer": "Veriler sadece gösterim amaçlıdır. Yatırım tavsiyesi değildir.",
        "fetching_data": "Piyasa verileri alınıyor...",
        "error_timeout": "⏱️ Bağlantı zaman aşımına uğradı. Lütfen tekrar deneyin.",
        "error_connection": "🔌 Bağlantı hatası. İnternet bağlantınızı veya borsa durumunu kontrol edin.",
        "error_schema": "⚠️ Yukarı akış veri formatı değişti. Lütfen daha sonra tekrar deneyin.",
        "error_no_data": "📉 {ticker} için bu dönemde işlem verisi bulunamadı (tatil/kota dışı olabilir).",
        "error_insufficient": "⚠️ {ticker} için analiz yapmaya yetecek kadar veri yok.",
        "error_unsupported_window": "⚠️ Seçilen tarih aralığı desteklenmiyor.",
        "error_conversion_incomplete": "⚠️ Her iki kur serisi seçilen pencereyi güvenli biçimde kapsamadığı için USD karşılaştırması kullanılamıyor.",
        "error_inflation_incomplete": "⚠️ Reel karşılaştırma, TÜFE kapsamı seçilen pencereyi güvenli biçimde kapsamadığı için kullanılamıyor.",
        "data_unavailable": "⚠️ {ticker} için veri mevcut değil. Daha erken bir bitiş tarihi seçin (MOEX verileri 1-2 gün gecikmeli gelir).",
        "date_adjusted": "⚠️ {actual_date} tarihine kadar veri kullanılıyor (seçili: {requested_date}) - mevcut en son veri",
        "moex_live": "✅ MOEX ISS API'den canlı veri",
        "bist_live": "✅ Yahoo Finance'den canlı veri",
        "no_data_error": "Veri yüklenemedi. Lütfen tarih aralığını değiştirin.",
        "metric_unavailable": "Kullanılamıyor",
        "chart_title": "Normalize Edilmiş Performans Karşılaştırması (100'e Endeksli)",
        "date_axis": "Tarih",
        "value_axis": "Normalize Değer",
        "base_label": "Baz = 100",
        "usd_conversion_partial": "⚠️ USD karşılaştırması, kur verisinin ortak kapsadığı pencereyle sınırlandı: {start_date} - {end_date}.",
        "comparison_window_partial": "⚠️ Karşılaştırma yalnızca ortak işlem penceresiyle sınırlandı: {start_date} - {end_date}.",
        "comparison_window_unavailable": "⚠️ Ortak USD-kapsamlı geçmiş güvenli karşılaştırma için çok kısa.",
        "comparison_window_unavailable_local": "⚠️ İki varlık güvenli karşılaştırma için yeterli ortak işlem günü paylaşmıyor.",
        "correlation_unavailable": "⚠️ Bu pencere için korelasyon güvenli şekilde hesaplanamadı.",
        "chart_unavailable": "⚠️ Normalize karşılaştırma grafiği bu pencere için kullanılamıyor.",
        "language": "🌐 Dil",
        "start_price_label": "Başlangıç: {currency}{price} ({date})",
        "date_error": "⚠️ Başlangıç tarihi bitiş tarihinden önce olmalıdır. Lütfen tarih aralığını düzeltin.",
        "analysis_mode": "Karşılaştırma Modu",
        "analysis_mode_help": "Nominal yerel fiyat, USD dönüşümü veya TÜFE ile düzeltilmiş reel fiyat karşılaştırması seçin.",
        "mode_local": "Yerel Para Birimi",
        "mode_usd": "USD",
        "mode_real": "Reel (TÜFE düzeltilmiş)",
        # Sector names
        "sector_aviation": "Havacılık",
        "sector_energy": "Enerji",
        "sector_banking": "Bankacılık",
        "sector_retail": "Perakende",
        "sector_steel": "Çelik",
        # Sector descriptions
        "aviation_desc": "Jeopolitik Riskler ve Turizm",
        "energy_desc": "Tedarik Zinciri ve Rafinaj",
        "banking_desc": "Faiz Oranları ve Para Politikası",
        "retail_desc": "Enflasyon ve Tüketici Davranışı",
        "steel_desc": "Küresel Endüstriyel Döngüler",
        # Correlation interpretations
        "strong_positive": "Güçlü Pozitif Korelasyon",
        "moderate_positive": "Orta Pozitif Korelasyon",
        "weak_positive": "Zayıf Pozitif Korelasyon",
        "no_correlation": "Anlamlı Korelasyon Yok",
        "weak_negative": "Zayıf Negatif Korelasyon",
        "moderate_negative": "Orta Negatif Korelasyon",
        "strong_negative": "Güçlü Negatif Korelasyon",
        "insufficient_data": "Yetersiz veri",
        # Risk metrics
        "volatility": "Volatilite (Yıllık)",
        "sharpe_ratio": "Sharpe Oranı",
        "max_drawdown": "Maksimum Düşüş",
        "cagr": "Bileşik Yıllık Büyüme",
        # Risk metrics section
        "risk_metrics": "Risk Metrikleri",
        "risk_summary_title": "Risk Metrikleri Kısa Rehberi",
        "risk_summary_intro": "Bu metrikler, manşet getirinin yanında oynaklık, aşağı yönlü risk ve getiri kalitesini de gösterir.",
        "volatility_summary": "Getirilerin yıllıklandırılmış dağılımı. Daha yüksek değerler daha sert fiyat hareketleri ve daha düşük istikrar anlamına gelir.",
        "sharpe_ratio_summary": "Bir birim volatilite başına risk ayarlı getiri. Daha yüksek değerler genelde daha verimli performansa işaret eder.",
        "max_drawdown_summary": "Seçilen dönemdeki en büyük zirve-dip kaybı. Daha negatif değerler daha derin aşağı yönlü riski gösterir.",
        "cagr_summary": "İlk ve son gözlem arasındaki yumuşatılmış yıllık büyüme oranı. Uzun dönemli karşılaştırmalar için kullanışlıdır.",
        # USD conversion
        "show_usd": "Fiyatları Dolar ($) Cinsinden Göster",
        "show_usd_help": "Adil karşılaştırma için fiyatları USD'ye çevir (enflasyon-düzeltilmiş görünüm)",
        "usd_conversion_active": "USD Dönüşümü Aktif - Tüm değerler USD cinsinden",
        "general_overview": "Genel Bakış",
        "usd_conversion_unavailable": "Bir veya daha fazla döviz kuru serisi yüklenemediği için USD dönüşümü uygulanamadı. Yerel para birimi görünümü gösteriliyor.",
        "real_conversion_active": "Reel mod aktif - Değerler {base_month} satın alma gücüyle gösteriliyor.",
        "real_conversion_partial": "⚠️ Reel karşılaştırma, TÜFE kapsamlı pencereyle sınırlandı: {start_date} - {end_date} ({base_month} satın alma gücü).",
        "real_conversion_unavailable": "⚠️ Reel karşılaştırma, kürasyonlu TÜFE snapshot'ı seçilen pencereyi tam kapsamadığı için kullanılamıyor.",
        "market_cap_comparison": "Piyasa Değeri Karşılaştırması",
        "market_cap_source_note": "Kaynak: config.yaml içindeki kürasyonlu snapshot ({as_of} itibarıyla).",
        "market_cap_snapshot_disclaimer": "Snapshot tabanlı değerler sunum tutarlılığı için kullanılır; canlı borsa verilerinden farklı olabilir.",
        "market_cap_unavailable": "Eksik piyasa değeri verisi nedeniyle karşılaştırma gösterilemiyor.",
        "market_cap_leader": "{market}, {multiple} farkla önde.",
        "ytd_performance": "YBB Performansı ({year})",
        "leader_label": "Lider",
        "tie_label": "Berabere",
        "methodology_title": "Metodoloji ve Sınırlamalar",
        "methodology_point_1": "Günlük kapanış fiyatları BIST için Yahoo Finance, MOEX için resmi MOEX ISS REST API üzerinden alınır.",
        "methodology_point_2": "MOEX verisi seçilen bitiş tarihini 1-2 işlem günü gecikmeli yansıtabilir.",
        "methodology_point_3": "USD modu, kur serilerini işlem günlerine hizalar ve eksik kur gözlemlerini ileri taşıyarak doldurur.",
        "methodology_point_4": "Karşılaştırma grafiği, analiz penceresindeki ilk uygun noktada her varlığı 100 bazına endeksler.",
        "methodology_point_5": "Reel mod, günlük fiyatları kürasyonlu aylık TÜFE değişim snapshot'larıyla deflate eder ve son ortak yayımlanmış ayı satın alma gücü çıpası olarak kullanır.",
        "methodology_point_6": "Korelasyon günlük getiriler üzerinden hesaplanır; piyasa değeri verileri ise sunum tutarlılığı için snapshot kullanır.",
    },
    "ru": {
        "app_title": "🌉 Евразийский Мост",
        "app_subtitle": "BIST (Турция) vs. MOEX (Россия) | Межрыночный Секторный Анализ",
        "sector_analysis": "Анализ Секторов",
        "select_sector": "📊 Выберите Сектор",
        "sector_help": "Выберите сектор для сравнения лидеров турецкого и российского рынков",
        "analysis_options": "💱 Настройки Валюты",
        "analysis_period": "📅 Период Анализа",
        "start": "Начало",
        "end": "Конец",
        "current_pair": "ТЕКУЩАЯ ПАРА",
        "turkey": "Турция",
        "russia": "Россия",
        "data_source": "Данные: Yahoo Finance, MOEX ISS API и подготовленные CPI snapshots",
        "built_with": "Создано с помощью Streamlit",
        "current_metrics": "📈 Текущие Показатели",
        "tr_period_change": "Изменение TR за период",
        "ru_period_change": "Изменение RU за период",
        "sim_label": "(Сим)",
        "normalized_performance": "📊 Нормализованная Производительность",
        "correlation_analysis": "🔗 Корреляционный Анализ",
        "pearson_correlation": "Коэффициент Корреляции Пирсона",
        "interpretation_guide": "📝 Руководство по Интерпретации",
        "interpretation_text": """Коэффициент корреляции Пирсона измеряет линейную связь между дневной доходностью обоих активов.
        <br><br>
        <strong>Значения варьируются от -1 до +1:</strong><br>
        • <strong>+0.7 до +1.0:</strong> Сильная положительная — активы движутся вместе<br>
        • <strong>+0.4 до +0.7:</strong> Умеренная положительная — есть некоторое совместное движение<br>
        • <strong>-0.4 до +0.4:</strong> Слабая или нет корреляции — независимые движения<br>
        • <strong>-0.7 до -0.4:</strong> Умеренная отрицательная — активы часто движутся в противоположных направлениях<br>
        • <strong>-1.0 до -0.7:</strong> Сильная отрицательная — обратная зависимость""",
        "footer_title": "Анализатор Евразийский Мост | Инструмент Сравнительного Финансового Анализа",
        "footer_disclaimer": "Данные только для демонстрационных целей. Не является финансовой рекомендацией.",
        "fetching_data": "Загрузка рыночных данных...",
        "general_overview": "Общий Обзор",
        "error_timeout": "⏱️ Время ожидания истекло. Попробуйте еще раз.",
        "error_connection": "🔌 Ошибка подключения. Проверьте интернет или статус биржи.",
        "error_schema": "⚠️ Формат ответа внешнего источника изменился. Попробуйте позже.",
        "error_no_data": "📉 Нет данных торгов по {ticker} за этот период (возможно праздник/делистинг).",
        "error_insufficient": "⚠️ Недостаточно данных по {ticker} для анализа.",
        "error_unsupported_window": "⚠️ Выбранный диапазон дат не поддерживается.",
        "error_conversion_incomplete": "⚠️ Сравнение в USD недоступно, потому что оба валютных ряда не покрыли окно безопасным образом.",
        "error_inflation_incomplete": "⚠️ Реальное сравнение недоступно, потому что покрытие CPI не охватило выбранное окно безопасным образом.",
        "data_unavailable": "⚠️ Данные недоступны для {ticker}. Выберите более раннюю дату окончания (данные MOEX имеют задержку 1-2 дня).",
        "date_adjusted": "⚠️ Используются данные до {actual_date} (выбрано: {requested_date}) - последние доступные данные",
        "moex_live": "✅ Живые данные из MOEX ISS API",
        "bist_live": "✅ Живые данные из Yahoo Finance",
        "no_data_error": "Не удалось загрузить данные. Измените диапазон дат.",
        "metric_unavailable": "Недоступно",
        "chart_title": "Сравнение Нормализованной Производительности (База = 100)",
        "date_axis": "Дата",
        "value_axis": "Нормализованное Значение",
        "base_label": "База = 100",
        "usd_conversion_partial": "⚠️ Сравнение в USD ограничено общим окном покрытия FX: {start_date} - {end_date}.",
        "comparison_window_partial": "⚠️ Сравнение ограничено только общим торговым окном: {start_date} - {end_date}.",
        "comparison_window_unavailable": "⚠️ Общая история с покрытием FX слишком короткая для безопасного сравнения.",
        "comparison_window_unavailable_local": "⚠️ У этих активов недостаточно общих торговых дней для безопасного сравнения.",
        "correlation_unavailable": "⚠️ Корреляцию для этого окна нельзя безопасно рассчитать.",
        "chart_unavailable": "⚠️ Нормализованный сравнительный график недоступен для этого окна.",
        "language": "🌐 Язык",
        "start_price_label": "Начало: {currency}{price} ({date})",
        "date_error": "⚠️ Дата начала должна быть раньше даты окончания. Пожалуйста, измените диапазон дат.",
        "analysis_mode": "Режим Сравнения",
        "analysis_mode_help": "Выберите сравнение в локальной валюте, в USD или в реальных ценах с поправкой на CPI.",
        "mode_local": "Локальная Валюта",
        "mode_usd": "USD",
        "mode_real": "Реальные (CPI-adjusted)",
        # Sector names
        "sector_aviation": "Авиация",
        "sector_energy": "Энергетика",
        "sector_banking": "Банковское дело",
        "sector_retail": "Розничная торговля",
        "sector_steel": "Сталь",
        # Sector descriptions
        "aviation_desc": "Геополитические Риски и Туризм",
        "energy_desc": "Цепочка Поставок и Нефтепереработка",
        "banking_desc": "Процентные Ставки и Денежно-кредитная Политика",
        "retail_desc": "Инфляция и Потребительское Поведение",
        "steel_desc": "Глобальные Промышленные Циклы",
        # Correlation interpretations
        "strong_positive": "Сильная Положительная Корреляция",
        "moderate_positive": "Умеренная Положительная Корреляция",
        "weak_positive": "Слабая Положительная Корреляция",
        "no_correlation": "Значимой Корреляции Нет",
        "weak_negative": "Слабая Отрицательная Корреляция",
        "moderate_negative": "Умеренная Отрицательная Корреляция",
        "strong_negative": "Сильная Отрицательная Корреляция",
        "insufficient_data": "Недостаточно данных",
        # Risk metrics
        "volatility": "Волатильность (год.)",
        "sharpe_ratio": "Коэффициент Шарпа",
        "max_drawdown": "Максимальная просадка",
        "cagr": "Среднегодовой темп роста",
        # Risk metrics section
        "risk_metrics": "Показатели Риска",
        "risk_summary_title": "Краткий Гид по Риск-Метрикам",
        "risk_summary_intro": "Эти метрики дополняют итоговую доходность, показывая волатильность, глубину просадки и качество доходности.",
        "volatility_summary": "Годовая дисперсия доходности. Более высокие значения означают более резкие движения цены и меньшую стабильность.",
        "sharpe_ratio_summary": "Доходность с поправкой на риск на единицу волатильности. Более высокие значения обычно означают лучшую эффективность.",
        "max_drawdown_summary": "Наибольшее падение от пика до минимума за выбранный период. Более отрицательные значения указывают на более глубокий риск снижения.",
        "cagr_summary": "Сглаженный среднегодовой темп роста между первым и последним наблюдением. Удобен для долгосрочного сравнения.",
        # USD conversion
        "show_usd": "Показать цены в долларах ($)",
        "show_usd_help": "Конвертировать цены в USD для справедливого сравнения (с учетом инфляции)",
        "usd_conversion_active": "Конвертация в USD активна - Все значения в USD",
        "usd_conversion_unavailable": "Конвертация в USD недоступна, потому что не удалось загрузить один или несколько валютных рядов. Вместо этого показаны локальные валюты.",
        "real_conversion_active": "Реальный режим активен - значения показаны в покупательной способности {base_month}.",
        "real_conversion_partial": "⚠️ Реальное сравнение ограничено окном с покрытием CPI: {start_date} - {end_date} (покупательная способность {base_month}).",
        "real_conversion_unavailable": "⚠️ Реальное сравнение недоступно, потому что подготовленный CPI snapshot не покрывает выбранное окно полностью.",
        "market_cap_comparison": "Сравнение Рыночной Капитализации",
        "market_cap_source_note": "Источник: подготовленный snapshot из config.yaml (по состоянию на {as_of}).",
        "market_cap_snapshot_disclaimer": "Значения snapshot используются для консистентной презентации и могут отличаться от живых биржевых значений.",
        "market_cap_unavailable": "Сравнение недоступно из-за отсутствия данных по капитализации.",
        "market_cap_leader": "{market} лидирует с преимуществом {multiple}.",
        "ytd_performance": "Доходность С Начала Года ({year})",
        "leader_label": "Лидер",
        "tie_label": "Ничья",
        "methodology_title": "Методология и Ограничения",
        "methodology_point_1": "Дневные цены закрытия берутся из Yahoo Finance для BIST и из официального MOEX ISS REST API для MOEX.",
        "methodology_point_2": "Данные MOEX могут отставать от выбранной конечной даты на 1-2 торговых дня.",
        "methodology_point_3": "В режиме USD валютные ряды выравниваются по торговым дням, а пропуски курсов заполняются предыдущими значениями.",
        "methodology_point_4": "Сравнительный график переводит каждый актив к базе 100 в первой доступной точке анализируемого окна.",
        "methodology_point_5": "Реальный режим дефлирует дневные цены с помощью подготовленных месячных snapshot'ов изменения CPI и использует последний общий опубликованный месяц как якорь покупательной способности.",
        "methodology_point_6": "Корреляция считается по дневной доходности, а значения капитализации берутся из snapshot для консистентной презентации.",
    }
}

LANGUAGE_OPTIONS = {
    "English": "en",
    "Türkçe": "tr",
    "Русский": "ru"
}


def get_text(key: str, lang: str = "en", **kwargs: Any) -> str:
    """Get translated text for a given key."""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_sector_display_name(sector_id: str, lang: str = "en") -> str:
    """Get the localized display name for a sector with its icon."""
    icon = SECTORS[sector_id].get("icon", "")
    name = get_text(f"sector_{sector_id}", lang)
    return f"{name} {icon}"


def get_sector_options(lang: str = "en") -> dict:
    """Get a dictionary mapping display names to sector IDs for the current language."""
    return {get_sector_display_name(sid, lang): sid for sid in SECTORS.keys()}


def get_macro_events_in_range(
    start_date: date | datetime,
    end_date: date | datetime,
    lang: str = "en",
) -> list[dict[str, object]]:
    """
    Get macro events within a date range.
    
    Args:
        start_date: Start date
        end_date: End date
        lang: Language code
    
    Returns:
        List of events with localized titles
    """
    events: list[dict[str, object]] = []
    # Convert to date if datetime is passed
    start_day = start_date.date() if isinstance(start_date, datetime) else start_date
    end_day = end_date.date() if isinstance(end_date, datetime) else end_date
    
    for event in MACRO_EVENTS:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        if start_day <= event_date <= end_day:
            title_key = f"title_{lang}"
            events.append({
                "date": event_date,
                "title": event.get(title_key, event.get("title_en", "Event")),
                "type": event.get("type", "other")
            })
    return events
