# Stitched vs single-track (Checkpoint 5)

| curve | single best DTW | stitched DTW (k) | winner | moment-sync err single / stitched (s) | xfade click ratio | length (s) |
|---|---|---|---|---|---|---|
| Nifty 50 through the COVID crash · drama | 0.123 | 0.053 (2) | stitched | 0.01 / 0.00 | 0.82 | 191.1 (plan 191.1) |
| Reliance 2008 · drama | 0.262 | 0.077 (3) | stitched | 0.00 / 0.14 | 0.93 | 194.6 (plan 194.6) |
| Infosys, Jul 2019 - Jun 2020 · drama | 0.282 | 0.094 (3) | stitched | 0.01 / 0.09 | 0.88 | 195.5 (plan 195.5) |
| Adani Enterprises, Jan - Mar 2023 · drama | 0.197 | 0.029 (2) | stitched | 0.15 / 0.01 | 0.97 | 191.7 (plan 191.7) |
| TCS, last 12 months · shape | 0.265 | 0.059 (3) | stitched | 0.06 / 0.05 | 0.55 | 197.1 (plan 197.1) |
| Reliance, last 12 months · shape | 0.289 | 0.054 (2) | stitched | 0.12 / 0.10 | 1.01 | 194.5 (plan 194.5) |
| HDFC Bank, last 12 months · shape | 0.300 | 0.075 (2) | stitched | 0.04 / 0.06 | 0.56 | 194.0 (plan 194.0) |
| Mumbai rain, 2005-07-25 to 2005-07-28 | 0.147 | 0.047 (3) | stitched | 0.05 / 0.05 | 0.92 | 195.6 (plan 195.6) |
| Chennai rain, 2015-11-30 to 2015-12-03 | 0.229 | 0.081 (2) | stitched | 0.11 / 0.10 | 1.07 | 191.0 (plan 191.0) |
| Delhi rain, 2023-07-07 to 2023-07-13 | 0.357 | 0.146 (3) | stitched | 0.13 / 0.12 | 0.75 | 198.0 (plan 198.0) |
| Kochi rain, 2018-08-14 to 2018-08-18 | 0.186 | 0.051 (3) | stitched | 0.00 / 0.09 | 0.89 | 194.8 (plan 194.8) |

**Stitched beats single on DTW cost in 11/11 showcase curves.**
Click ratio = max sample jump within ±0.5 s of each crossfade edge / the file's 99.9th-pct jump; <= 1 means no click.