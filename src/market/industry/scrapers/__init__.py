"""Scraper implementations for industry report sources.

This sub-package provides the ``BaseScraper`` abstract base class
and source-specific scraper implementations.

Scrapers
--------
BaseScraper
    Abstract base class with 2-layer fallback (curl_cffi -> Playwright).
ConsultingScraper
    Base class for consulting firm report scrapers.
McKinseyScraper
    Scraper for McKinsey Insights.
BCGScraper
    Scraper for BCG Publications.
DeloitteScraper
    Scraper for Deloitte Insights.
PwCScraper
    Scraper for PwC Strategy&.
BainScraper
    Scraper for Bain Insights.
AccentureScraper
    Scraper for Accenture Insights.
EYScraper
    Scraper for EY Insights.
KPMGScraper
    Scraper for KPMG Insights.
InvestmentBankScraper
    Base class for investment bank report scrapers.
GoldmanSachsScraper
    Scraper for Goldman Sachs Insights.
MorganStanleyScraper
    Scraper for Morgan Stanley Ideas.
JPMorganScraper
    Scraper for JP Morgan Research.

See Also
--------
market.etfcom.session : ETFComSession (curl_cffi + Cloudflare bypass reference).
market.etfcom.client : ETFComClient (API client reference).
"""
