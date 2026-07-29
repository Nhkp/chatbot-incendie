# Candidate data sources

This registry qualifies sources before ingestion. A source must not be automated until
its legal and technical status is clear.

| Source | Type | V1 use | Status |
| --- | --- | --- | --- |
| data.gouv.fr | API / open datasets | Events, orders, useful public data | To validate |
| Gironde Prefecture | Official website | Local press releases and instructions | To validate |
| Landes Prefecture | Official website | Local press releases and instructions | To validate |
| SDIS 33 | Official website / releases | Public operational information | To validate |
| SDIS 40 | Official website / releases | Public operational information | To validate |
| Meteo-France vigilance | Public data / API | Weather and vigilance context | To validate |
| Meteo-France Météo des forêts archive | Open data / CSV | Wildfire danger prevention context | Approved for offline connector |
| Meteo-France Météo des forêts realtime | API | Current wildfire danger prevention context | Connector implemented |
| Meteo-France Vigilance API | API | Weather vigilance context | To validate |
| Meteo-France Forecast API | API | Forecast weather context | To validate |
| Meteo-France Observations API | API | Nearby weather-station observations | To validate |
| meteo.data.gouv.fr | Open data | Public weather datasets and archives | To validate |
| Vigicrues | Public API | Contextual hydrological risks | Optional |
| NASA FIRMS Area API | API | Satellite active fire and hotspot detections | To validate |
| Géorisques API | API | Commune-level risk and regulatory context | To validate |
| BDIFF | Open data | Historical wildfire database | To validate |
| Atmo Nouvelle-Aquitaine Open Data | Open data | Smoke and air-quality context | To validate |
| Actu.fr Gironde | Web news | Local articles | To validate |
| Actu.fr Landes | Web news | Local articles | To validate |
| France Bleu Gironde | Web news | Local articles | To validate |
| France Bleu Gascogne | Web news | Local articles | To validate |
| France 3 Gironde | Web news | Local public-service articles | To validate |
| France 3 Landes | Web news | Local public-service articles | To validate |
| Sud Ouest Gironde | Web news | Local articles | To validate |
| Sud Ouest Landes | Web news | Local articles | To validate |

## API keys

- `METEO_FRANCE_API_KEY`: required for Météo des forêts realtime, Vigilance, Forecast,
  and Observations APIs.
- `NASA_FIRMS_MAP_KEY`: required for NASA FIRMS Area API.
- No key is currently expected for Géorisques, BDIFF, Atmo Nouvelle-Aquitaine public
  datasets, or web-news scraping candidates.

## Evaluation rules

- Check usage terms.
- Prefer APIs over scrapers.
- Respect rate limits.
- Record the collection date and canonical URL.
- Deduplicate by canonical URL and content fingerprint.
