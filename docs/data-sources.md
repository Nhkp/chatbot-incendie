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
| Vigicrues | Public API | Contextual hydrological risks | Optional |
| Actu.fr Gironde | Web news | Local articles | To validate |
| Actu.fr Landes | Web news | Local articles | To validate |
| France Bleu Gironde | Web news | Local articles | To validate |
| France Bleu Gascogne | Web news | Local articles | To validate |
| Sud Ouest Gironde | Web news | Local articles | To validate |
| Sud Ouest Landes | Web news | Local articles | To validate |

## Evaluation rules

- Check usage terms.
- Prefer APIs over scrapers.
- Respect rate limits.
- Record the collection date and canonical URL.
- Deduplicate by canonical URL and content fingerprint.
