# Stitched vs single-track (Checkpoint 5)

| curve | single best DTW | stitched DTW (k) | winner | moment-sync err single / stitched (s) | xfade click ratio | length (s) |
|---|---|---|---|---|---|---|
| Nifty 50 through the COVID crash · drama | 0.123 | 0.042 (3) | stitched | 0.01 / 0.15 | 0.90 | 194.0 (plan 194.0) |
| Reliance 2008 · drama | 0.248 | 0.081 (3) | stitched | 0.00 / 0.00 | 1.32 | 200.6 (plan 200.6) |
| Infosys, Jul 2019 - Jun 2020 · drama | 0.187 | 0.103 (3) | stitched | 0.05 / 0.10 | 1.15 | 193.1 (plan 193.1) |
| Adani Enterprises, Jan - Mar 2023 · drama | 0.145 | 0.020 (2) | stitched | 0.12 / 0.01 | 1.04 | 191.6 (plan 191.6) |
| TCS, last 12 months · shape | 0.265 | 0.059 (3) | stitched | 0.06 / 0.05 | 0.55 | 197.1 (plan 197.1) |
| Reliance, last 12 months · shape | 0.289 | 0.059 (2) | stitched | 0.12 / 0.03 | 0.53 | 194.5 (plan 194.5) |
| HDFC Bank, last 12 months · shape | 0.300 | 0.075 (2) | stitched | 0.04 / 0.06 | 0.56 | 194.0 (plan 194.0) |
| Mumbai rain, 2005-07-25 to 2005-07-28 | 0.062 | 0.039 (3) | stitched | 0.00 / 0.05 | 0.87 | 192.8 (plan 192.8) |
| Chennai rain, 2015-11-30 to 2015-12-03 | 0.217 | 0.081 (2) | stitched | 0.01 / 0.10 | 1.07 | 191.0 (plan 191.0) |
| Delhi rain, 2023-07-07 to 2023-07-13 | 0.300 | 0.159 (2) | stitched | 0.04 / 0.08 | 0.46 | 193.9 (plan 193.9) |
| Kochi rain, 2018-08-14 to 2018-08-18 | 0.094 | 0.048 (3) | stitched | 0.00 / 0.09 | 1.03 | 196.0 (plan 196.0) |
| UK wind power through Storm Ciarán | 0.236 | 0.073 (3) | stitched | 21.39 / 0.06 | 2.43 | 194.7 (plan 194.7) |
| UK wind power through Storms Isha and Jocelyn | 0.184 | 0.045 (3) | stitched | 0.04 / 0.10 | 0.98 | 193.1 (plan 193.1) |
| UK wind power in the still, freezing week of Jan 2025 | 0.166 | 0.037 (3) | stitched | 0.01 / 0.07 | 0.70 | 191.5 (plan 191.5) |
| UK wind power through Storm Éowyn | 0.161 | 0.078 (2) | stitched | 0.03 / 0.01 | 1.15 | 195.5 (plan 195.5) |
| Jet engine 39 run to failure (shortest life, 128 cycles) | 0.509 | 0.068 (2) | stitched | 0.65 / 0.18 | 1.03 | 197.0 (plan 197.0) |
| Jet engine 68 run to failure (a typical life, 199 cycles) | 0.529 | 0.043 (3) | stitched | 0.57 / 0.00 | 1.11 | 199.7 (plan 199.7) |
| Jet engine 69 run to failure (longest life, 362 cycles) | 0.488 | 0.035 (3) | stitched | 0.52 / 0.07 | 0.94 | 196.0 (plan 196.0) |
| India's cereal harvests, 1961–2024 | 0.251 | 0.105 (3) | stitched | 0.04 / 0.00 | 0.67 | 198.6 (plan 198.6) |
| Australia's cereal harvests, 1961–2024 | 0.187 | 0.071 (3) | stitched | 0.01 / 0.27 | 0.97 | 192.7 (plan 192.7) |
| US cereal harvests, 1961–2024 | 0.214 | 0.082 (3) | stitched | 0.22 / 0.08 | 0.35 | 196.5 (plan 196.5) |
| India's economy, 1960–2025 | 0.302 | 0.139 (3) | stitched | 0.29 / 0.04 | 0.33 | 193.9 (plan 193.9) |
| The US economy through the oil shocks, 1970–1985 | 0.145 | 0.070 (2) | stitched | 0.17 / 0.18 | 0.86 | 199.6 (plan 199.6) |
| The US economy through the Great Recession, 2000–2015 | 0.289 | 0.084 (2) | stitched | 0.00 / 0.00 | 0.35 | 199.1 (plan 199.1) |

**Stitched beats single on DTW cost in 24/24 showcase curves.**
Click ratio = max sample jump within ±0.5 s of each crossfade edge / the file's 99.9th-pct jump; <= 1 means no click.