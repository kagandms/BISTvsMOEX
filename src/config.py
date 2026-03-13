"""
Configuration module for The Eurasian Bridge application.
Loads settings from config.yaml and provides constants.
"""

from __future__ import annotations

import os
import yaml
from datetime import datetime
from pathlib import Path



def load_config() -> dict:
    """Load configuration from config.yaml file and apply environment overrides."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Apply environment variable overrides (Security hardening)
    # BM_TIMEOUT -> api.finam.timeout_seconds
    if "BM_TIMEOUT" in os.environ:
        try:
            timeout = int(os.environ["BM_TIMEOUT"])
            if "api" in config and "finam" in config["api"]:
                config["api"]["finam"]["timeout_seconds"] = timeout
        except ValueError:
            pass # Invalid env var, ignore

    # BM_MOEX_DELAY -> data.moex_delay_days
    if "BM_MOEX_DELAY" in os.environ:
        try:
            delay = int(os.environ["BM_MOEX_DELAY"])
            if "data" in config:
                config["data"]["moex_delay_days"] = delay
        except ValueError:
            pass

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
        "data_source": "Data: Yahoo Finance & Finam Export",
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
        "error_api": "⚠️ API Error: {error}",
        "error_no_data": "📉 No trading data found for {ticker} in this period (possible holiday/delisting).",
        "error_insufficient": "⚠️ Insufficient data points for {ticker} to perform analysis.",
        "data_unavailable": "⚠️ Data unavailable for {ticker}. Try selecting an earlier end date (MOEX data has 1-2 day delay).",
        "date_adjusted": "⚠️ Using data until {actual_date} (selected: {requested_date}) - latest available data",
        "moex_live": "✅ Live data from Finam Export API",
        "bist_live": "✅ Live data from Yahoo Finance",
        "no_data_error": "Unable to load data. Please adjust date range.",
        "chart_title": "Normalized Performance Comparison (Rebased to 100)",
        "date_axis": "Date",
        "value_axis": "Normalized Value",
        "base_label": "Base = 100",
        "language": "🌐 Language",
        "start_price_label": "Start: {currency}{price} ({date})",
        "date_error": "⚠️ Start date must be before end date. Please adjust the date range.",
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
        # USD conversion
        "show_usd": "Show Prices in USD ($)",
        "show_usd_help": "Convert prices to USD for fair comparison (enables inflation-adjusted view)",
        "usd_conversion_active": "USD Conversion Active - All values in USD",
        "general_overview": "General Overview",
        "usd_conversion_unavailable": "USD conversion unavailable because one or more FX series could not be loaded. Local currency view is shown instead.",
        "market_cap_comparison": "Market Cap Comparison",
        "market_cap_source_note": "Source: curated snapshot from config.yaml (as of {as_of}).",
        "market_cap_snapshot_disclaimer": "Snapshot-based values support presentation consistency and may differ from live exchange values.",
        "market_cap_unavailable": "Comparison unavailable due to missing market-cap data.",
        "market_cap_leader": "{market} leads by {multiple}.",
        "ytd_performance": "YTD Performance ({year})",
        "leader_label": "Leader",
        "tie_label": "Tie",
        "methodology_title": "Methodology & Limitations",
        "methodology_point_1": "Daily close prices are fetched from Yahoo Finance for BIST and Finam Export for MOEX.",
        "methodology_point_2": "MOEX data can lag the selected end date by 1-2 trading days.",
        "methodology_point_3": "USD mode aligns FX series to trading days and forward-fills missing exchange-rate observations.",
        "methodology_point_4": "The comparison chart rebases each asset to 100 on the first available point in the analysis window.",
        "methodology_point_5": "Correlation is calculated on daily returns, while market-cap values use a curated snapshot for presentation consistency.",
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
        "data_source": "Veri: Yahoo Finance & Finam Export",
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
        "error_api": "⚠️ API Hatası: {error}",
        "error_no_data": "📉 {ticker} için bu dönemde işlem verisi bulunamadı (tatil/kota dışı olabilir).",
        "error_insufficient": "⚠️ {ticker} için analiz yapmaya yetecek kadar veri yok.",
        "data_unavailable": "⚠️ {ticker} için veri mevcut değil. Daha erken bir bitiş tarihi seçin (MOEX verileri 1-2 gün gecikmeli gelir).",
        "date_adjusted": "⚠️ {actual_date} tarihine kadar veri kullanılıyor (seçili: {requested_date}) - mevcut en son veri",
        "moex_live": "✅ Finam Export API'den canlı veri",
        "bist_live": "✅ Yahoo Finance'den canlı veri",
        "no_data_error": "Veri yüklenemedi. Lütfen tarih aralığını değiştirin.",
        "chart_title": "Normalize Edilmiş Performans Karşılaştırması (100'e Endeksli)",
        "date_axis": "Tarih",
        "value_axis": "Normalize Değer",
        "base_label": "Baz = 100",
        "language": "🌐 Dil",
        "start_price_label": "Başlangıç: {currency}{price} ({date})",
        "date_error": "⚠️ Başlangıç tarihi bitiş tarihinden önce olmalıdır. Lütfen tarih aralığını düzeltin.",
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
        # USD conversion
        "show_usd": "Fiyatları Dolar ($) Cinsinden Göster",
        "show_usd_help": "Adil karşılaştırma için fiyatları USD'ye çevir (enflasyon-düzeltilmiş görünüm)",
        "usd_conversion_active": "USD Dönüşümü Aktif - Tüm değerler USD cinsinden",
        "general_overview": "Genel Bakış",
        "usd_conversion_unavailable": "Bir veya daha fazla döviz kuru serisi yüklenemediği için USD dönüşümü uygulanamadı. Yerel para birimi görünümü gösteriliyor.",
        "market_cap_comparison": "Piyasa Değeri Karşılaştırması",
        "market_cap_source_note": "Kaynak: config.yaml içindeki kürasyonlu snapshot ({as_of} itibarıyla).",
        "market_cap_snapshot_disclaimer": "Snapshot tabanlı değerler sunum tutarlılığı için kullanılır; canlı borsa verilerinden farklı olabilir.",
        "market_cap_unavailable": "Eksik piyasa değeri verisi nedeniyle karşılaştırma gösterilemiyor.",
        "market_cap_leader": "{market}, {multiple} farkla önde.",
        "ytd_performance": "YBB Performansı ({year})",
        "leader_label": "Lider",
        "tie_label": "Berabere",
        "methodology_title": "Metodoloji ve Sınırlamalar",
        "methodology_point_1": "Günlük kapanış fiyatları BIST için Yahoo Finance, MOEX için Finam Export üzerinden alınır.",
        "methodology_point_2": "MOEX verisi seçilen bitiş tarihini 1-2 işlem günü gecikmeli yansıtabilir.",
        "methodology_point_3": "USD modu, kur serilerini işlem günlerine hizalar ve eksik kur gözlemlerini ileri taşıyarak doldurur.",
        "methodology_point_4": "Karşılaştırma grafiği, analiz penceresindeki ilk uygun noktada her varlığı 100 bazına endeksler.",
        "methodology_point_5": "Korelasyon günlük getiriler üzerinden hesaplanır; piyasa değeri verileri ise sunum tutarlılığı için snapshot kullanır.",
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
        "data_source": "Данные: Yahoo Finance & Finam Export",
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
        "error_api": "⚠️ Ошибка API: {error}",
        "error_no_data": "📉 Нет данных торгов по {ticker} за этот период (возможно праздник/делистинг).",
        "error_insufficient": "⚠️ Недостаточно данных по {ticker} для анализа.",
        "data_unavailable": "⚠️ Данные недоступны для {ticker}. Выберите более раннюю дату окончания (данные MOEX имеют задержку 1-2 дня).",
        "date_adjusted": "⚠️ Используются данные до {actual_date} (выбрано: {requested_date}) - последние доступные данные",
        "moex_live": "✅ Живые данные из Finam Export API",
        "bist_live": "✅ Живые данные из Yahoo Finance",
        "no_data_error": "Не удалось загрузить данные. Измените диапазон дат.",
        "chart_title": "Сравнение Нормализованной Производительности (База = 100)",
        "date_axis": "Дата",
        "value_axis": "Нормализованное Значение",
        "base_label": "База = 100",
        "language": "🌐 Язык",
        "start_price_label": "Начало: {currency}{price} ({date})",
        "date_error": "⚠️ Дата начала должна быть раньше даты окончания. Пожалуйста, измените диапазон дат.",
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
        # USD conversion
        "show_usd": "Показать цены в долларах ($)",
        "show_usd_help": "Конвертировать цены в USD для справедливого сравнения (с учетом инфляции)",
        "usd_conversion_active": "Конвертация в USD активна - Все значения в USD",
        "usd_conversion_unavailable": "Конвертация в USD недоступна, потому что не удалось загрузить один или несколько валютных рядов. Вместо этого показаны локальные валюты.",
        "market_cap_comparison": "Сравнение Рыночной Капитализации",
        "market_cap_source_note": "Источник: подготовленный snapshot из config.yaml (по состоянию на {as_of}).",
        "market_cap_snapshot_disclaimer": "Значения snapshot используются для консистентной презентации и могут отличаться от живых биржевых значений.",
        "market_cap_unavailable": "Сравнение недоступно из-за отсутствия данных по капитализации.",
        "market_cap_leader": "{market} лидирует с преимуществом {multiple}.",
        "ytd_performance": "Доходность С Начала Года ({year})",
        "leader_label": "Лидер",
        "tie_label": "Ничья",
        "methodology_title": "Методология и Ограничения",
        "methodology_point_1": "Дневные цены закрытия берутся из Yahoo Finance для BIST и из Finam Export для MOEX.",
        "methodology_point_2": "Данные MOEX могут отставать от выбранной конечной даты на 1-2 торговых дня.",
        "methodology_point_3": "В режиме USD валютные ряды выравниваются по торговым дням, а пропуски курсов заполняются предыдущими значениями.",
        "methodology_point_4": "Сравнительный график переводит каждый актив к базе 100 в первой доступной точке анализируемого окна.",
        "methodology_point_5": "Корреляция считается по дневной доходности, а значения капитализации берутся из snapshot для консистентной презентации.",
    }
}

LANGUAGE_OPTIONS = {
    "English": "en",
    "Türkçe": "tr",
    "Русский": "ru"
}


def get_text(key: str, lang: str = "en", **kwargs) -> str:
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


def get_macro_events_in_range(start_date: datetime, end_date: datetime, lang: str = "en") -> list:
    """
    Get macro events within a date range.
    
    Args:
        start_date: Start date
        end_date: End date
        lang: Language code
    
    Returns:
        List of events with localized titles
    """
    events = []
    # Convert to date if datetime is passed
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    
    for event in MACRO_EVENTS:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        if start_date <= event_date <= end_date:
            title_key = f"title_{lang}"
            events.append({
                "date": event_date,
                "title": event.get(title_key, event.get("title_en", "Event")),
                "type": event.get("type", "other")
            })
    return events
