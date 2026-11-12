# Matcher self-test

Library: 596 tracks · data curves: 363 · N=200, band=±10


**Test 1: 50/50 · Test 2: 20/20** · 57s

Calibration: 5,000 random pairs, median distance 0.913, 5th pct 0.471


## Top-1 reuse across all 363 curves (no penalty)

Distinct #1 tracks: 102 of 596. Most reused:

- km_spazzmatica_polka: 45 (12.4%)
- km_overworld: 16 (4.4%)
- km_ghost_story: 15 (4.1%)
- km_we_wish_you_a_merry_christmas: 15 (4.1%)
- km_silent_night: 10 (2.8%)
- km_two_finger_johnny: 9 (2.5%)
- km_unease: 8 (2.2%)
- km_robo_western: 8 (2.2%)
- km_space_fighter_loop: 8 (2.2%)
- km_confused_state: 8 (2.2%)

Flagged (> 5%): km_spazzmatica_polka 12.4%
Popularity penalty applied: {'km_spazzmatica_polka': 0.1564, 'km_we_wish_you_a_merry_christmas': 0.0401}. After penalty: distinct #1 = 104, max share = 5.0% (km_spazzmatica_polka)

## Test 1: track's own energy curve as data (top-3)

- PASS km_grammophone_taps -> km_grammophone_taps (0.000), km_water_droplets_on_the_river (0.072), km_starry (0.116)
- PASS km_killing_time -> km_killing_time (0.000), km_blown_away (0.082), km_frogs_legs_rag (0.083)
- PASS km_hit_the_streets -> km_hit_the_streets (0.000), km_funky_one (0.064), km_last_kiss_goodnight (0.064)
- PASS km_blown_away -> km_blown_away (0.000), km_motivator (0.037), km_brightly_fancy (0.040)
- PASS km_sidewalk_shade___slower -> km_sidewalk_shade___slower (0.000), km_sidewalk_shade (0.025), km_last_kiss_goodnight (0.115)
- PASS km_water_droplets_on_the_river -> km_water_droplets_on_the_river (0.000), km_fast_talkin (0.057), km_stay_the_course (0.060)
- PASS km_oh__little_town_of_bethlehem -> km_oh__little_town_of_bethlehem (0.000), km_tenebrous_brothers_carnival___prelude (0.109), km_dark_pad (0.113)
- PASS km_quinn_s_song__a_new_man -> km_quinn_s_song__a_new_man (0.000), km_witch_hunt (0.142), km_run_amok (0.166)
- PASS km_eastern_thought -> km_eastern_thought (0.000), km_ossuary_4___animate (0.113), km_canon_in_d_for_two_renaissance_harps (0.131)
- PASS km_impact_allegretto -> km_impact_allegretto (0.000), km_bathed_in_the_light (0.076), km_dark_star (0.109)
- PASS km_funky_boxstep -> km_funky_boxstep (0.000), km_valse_gymnopedie (0.114), km_flying_kerfuffle (0.122)
- PASS km_prelude_in_c__bwv_846 -> km_prelude_in_c__bwv_846 (0.000), km_malt_shop_bop (0.030), km_funk_game_loop (0.033)
- PASS km_gymnopedie_no__3 -> km_gymnopedie_no__3 (0.000), km_somewhere_sunny (0.082), km_dirt_rhodes (0.086)
- PASS km_beach_bum -> km_beach_bum (0.000), km_beach_party (0.037), km_impact_intermezzo (0.042)
- PASS km_samba_isobel -> km_samba_isobel (0.000), km_five_card_shuffle (0.050), km_blown_away (0.054)
- PASS km_land_of_phantoms -> km_land_of_phantoms (0.000), km_one_of_them (0.186), km_zombie_chase (0.253)
- PASS km_journey_to_ascend -> km_journey_to_ascend (0.000), km_dvorak_polka (0.028), km_protofunk (0.036)
- PASS km_sax__rock__and_roll -> km_sax__rock__and_roll (0.000), km_hotrock (0.017), km_protofunk (0.053)
- PASS km_crusade -> km_crusade (0.000), km_easy_lemon (0.085), km_krampus_workshop (0.109)
- PASS km_sneaky_snitch -> km_sneaky_snitch (0.000), km_shenyang (0.108), km_george_street_shuffle (0.114)
- PASS km_meatball_parade -> km_meatball_parade (0.000), km_on_the_passing_of_time (0.207), km_cottages (0.258)
- PASS km_smooth_move -> km_smooth_move (0.000), km_chee_zee_beach (0.173), km_chee_zee_lab (0.180)
- PASS km_colorless_aura -> km_colorless_aura (0.000), km_thunder_dreams (0.143), km_starry (0.184)
- PASS km_padanaya_blokov -> km_padanaya_blokov (0.000), km_chase_pulse_faster (0.055), km_chase_pulse (0.069)
- PASS km_tea_roots -> km_tea_roots (0.000), km_dub_eastern (0.073), km_bicycle (0.079)
- PASS km_the_show_must_be_go -> km_the_show_must_be_go (0.000), km_yallahs (0.093), km_ultra_polka (0.121)
- PASS km_half_mystery -> km_half_mystery (0.000), km_no_spam_polka (0.048), km_retrofuture_dirty (0.056)
- PASS km_bossabossa -> km_bossabossa (0.000), km_nile_s_blues (0.074), km_pilot_error (0.077)
- PASS km_snare_bounce_polka -> km_snare_bounce_polka (0.000), km_hustle (0.029), km_super_power_cool_dude (0.034)
- PASS km_the_path_of_the_goblin_king -> km_the_path_of_the_goblin_king (0.000), km_echoes_of_time_v2 (0.188), km_measured_paces (0.197)
- PASS km_old_road -> km_old_road (0.000), km_gymnopedie_no__3 (0.145), km_hidden_wonders (0.146)
- PASS km_no_frills_salsa -> km_no_frills_salsa (0.000), km_limit_70 (0.162), km_jazz_brunch (0.176)
- PASS km_quasi_motion -> km_quasi_motion (0.000), km_voxel_revolution (0.043), km_disco_lounge (0.052)
- PASS km_hustle -> km_hustle (0.000), km_funin_and_sunin (0.021), km_snare_bounce_polka (0.029)
- PASS km_ultra_polka -> km_ultra_polka (0.000), km_amazing_plan___distressed (0.050), km_amazing_plan (0.061)
- PASS km_port_horizon -> km_port_horizon (0.000), km_gymnopedie_no__2 (0.133), km_sardana (0.159)
- PASS km_bathed_in_the_light -> km_bathed_in_the_light (0.000), km_impact_allegretto (0.076), km_kumasi_groove (0.084)
- PASS km_ripples -> km_ripples (0.000), km_moon_lounge_omicron_prime (0.189), km_heavy_heart (0.191)
- PASS km_holiday_weasel -> km_holiday_weasel (0.000), km_no_frills_comparsa (0.076), km_raw (0.098)
- PASS km_sunset_at_glengorm -> km_sunset_at_glengorm (0.000), km_final_count (0.171), km_slow_jam (0.195)
- PASS km_manic_polka -> km_manic_polka (0.000), km_smash__sketch (0.028), km_funin_and_sunin (0.028)
- PASS km_deck_the_halls_a -> km_deck_the_halls_a (0.000), km_sugar_plum_dark_mix (0.124), km_it_came_upon_a_midnight_clear (0.132)
- PASS km_blip_stream -> km_blip_stream (0.000), km_quasi_motion (0.105), km_canon_in_d_major (0.109)
- PASS km_scissors -> km_scissors (0.000), km_trepidation (0.130), km_dhaka (0.152)
- PASS km_rhinoceros -> km_rhinoceros (0.000), km_adding_the_sun (0.087), km_loopster (0.089)
- PASS km_cool_hard_facts -> km_cool_hard_facts (0.000), km_egmont_overture_finale (0.070), km_that_s_a_wrap (0.075)
- PASS km_funky_chunk -> km_funky_chunk (0.000), km_sunshine__version_2 (0.049), km_retrofuture_dirty (0.052)
- PASS km_casa_bossa_nova -> km_casa_bossa_nova (0.000), km_matt_s_blues (0.066), km_lobby_time (0.072)
- PASS km_blue_ska -> km_blue_ska (0.000), km_del_rio_bravo (0.031), km_glee_club_polka (0.033)
- PASS km_space_jazz -> km_space_jazz (0.000), km_sunday_dub (0.146), km_el_magicia (0.177)

## Test 2: data curve fed in reverse (top-3)

- PASS hdfcbank_2011_drama -> hdfcbank_2011_drama (0.000), reliance_2012_shape (0.159), icicibank_2018_shape (0.169)
- PASS itc_2016_shape -> itc_2016_shape (0.000), nifty50_2016_shape (0.023), hdfcbank_2016_shape (0.036)
- PASS itc_2013_shape -> itc_2013_shape (0.000), icicibank_2025_shape (0.131), itc_2023_shape (0.159)
- PASS infy_2015_shape -> infy_2015_shape (0.000), adanient_2015_shape (0.029), nifty_covid_shape (0.073)
- PASS bhartiartl_2009_shape -> bhartiartl_2009_shape (0.000), infy_2016_shape (0.053), itc_2010_shape (0.067)
- PASS reliance_2022_drama -> reliance_2022_drama (0.000), nifty50_2022_drama (0.128), icicibank_2022_drama (0.131)
- PASS bhartiartl_2008_shape -> bhartiartl_2008_shape (0.000), hdfcbank_2008_shape (0.055), icicibank_2008_shape (0.062)
- PASS rain_chennai_2023 -> rain_chennai_2023 (0.000), itc_2017_shape (0.135), rain_mumbai_2017 (0.173)
- PASS reliance_2021_shape -> reliance_2021_shape (0.000), nifty50_2021_shape (0.030), icicibank_2021_shape (0.067)
- PASS nifty_covid_drama -> nifty_covid_drama (0.000), bhartiartl_2011_shape (0.167), itc_2016_shape (0.179)
- PASS reliance_2020_drama -> reliance_2020_drama (0.000), infy_2020_drama (0.056), tcs_2020_drama (0.078)
- PASS infy_2016_shape -> infy_2016_shape (0.000), bhartiartl_2009_shape (0.053), itc_2019_shape (0.100)
- PASS reliance_last12_drama -> reliance_last12_drama (0.000), nifty50_2019_shape (0.204), bhartiartl_2019_shape (0.244)
- PASS infy_2023_drama -> infy_2023_drama (0.000), adanient_2014_drama (0.223), reliance_2023_drama (0.235)
- PASS adanient_2010_drama -> adanient_2010_drama (0.000), reliance_2009_drama (0.163), adanient_2009_drama (0.174)
- PASS reliance_2019_drama -> reliance_2019_drama (0.000), sbin_2015_drama (0.130), nifty50_2015_drama (0.149)
- PASS hdfcbank_2015_shape -> hdfcbank_2015_shape (0.000), sbin_2012_shape (0.152), hdfcbank_2008_drama (0.152)
- PASS reliance_2021_drama -> reliance_2021_drama (0.000), nifty50_2021_drama (0.147), nifty50_2016_drama (0.179)
- PASS nifty50_2018_shape -> nifty50_2018_shape (0.000), itc_2018_shape (0.101), infy_2019_shape (0.150)
- PASS bhartiartl_2019_drama -> bhartiartl_2019_drama (0.000), tcs_2019_drama (0.185), reliance_2022_shape (0.223)

## Test 3: synthetic shapes (top-3)

- slow build: Spazzmatica Polka (99.7% match), We Wish you a Merry Christmas (98.4% match), Divertissement - Pizzicato (from the ballet Sylvia) (95.9% match)
- explosive start: Ghost Story (93.1% match), Confused State (92.2% match), Villainous Treachery (78.9% match)
- rollercoaster: Cowboy Sting (100.0% match), Groundwork (99.9% match), Honey Bee (99.9% match)
- flat: unmatchable (flat curve) - expected