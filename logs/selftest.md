# Matcher self-test

Library: 716 tracks · data curves: 597 · N=200, band=±10


**Test 1: 50/50 · Test 2: 20/20** · 190s

Calibration: 5,000 random pairs, median distance 0.954, 5th pct 0.457


## Top-1 reuse across all 597 curves (no penalty)

Distinct #1 tracks: 138 of 716. Most reused:

- km_spazzmatica_polka: 130 (21.8%)
- mo_grieg_peer_gynt_suite_no__1__op__46___iv__in_the_hall_ae5099: 22 (3.7%)
- km_ghost_story: 17 (2.8%)
- cl_saint_saens_carnival_11___pianistes__pianists: 17 (2.8%)
- mo_grieg_peer_gynt_suite_no__1__op__46___i__morning: 15 (2.5%)
- mo_mozart_symphony_no__40_in_g_minor__k__550___iii__menu_e4e1db: 14 (2.3%)
- mo_brahms_symphony_no__4_in_e_minor__op__98___iv__allegr_ecb50d: 12 (2.0%)
- mo_grieg_peer_gynt_suite_no__1__op__46___ii__aase_s_death: 11 (1.8%)
- mo_tchaikovsky_symphony_no__6_in_b_minor__op__74___pathe_14dd0f: 10 (1.7%)
- km_confused_state: 10 (1.7%)

Flagged (> 5%): km_spazzmatica_polka 21.8%
Popularity penalty applied: {'cl_saint_saens_carnival_11___pianistes__pianists': 0.1242, 'km_spazzmatica_polka': 0.3971, 'km_we_wish_you_a_merry_christmas': 0.0021, 'mo_grieg_peer_gynt_suite_no__1__op__46___iv__in_the_hall_ae5099': 0.1861, 'mo_tchaikovsky_symphony_no__6_in_b_minor__op__74___pathe_14dd0f': 0.1839}. After penalty: distinct #1 = 144, max share = 4.9% (mo_tchaikovsky_symphony_no__6_in_b_minor__op__74___pathe_14dd0f)

## Test 1: track's own energy curve as data (top-3)

- PASS km_funky_one -> km_funky_one (0.000), km_cheery_monday (0.044), km_funk_game_loop (0.045)
- PASS km_journey_to_ascend -> km_journey_to_ascend (0.000), km_dvorak_polka (0.028), km_protofunk (0.036)
- PASS km_half_mystery -> km_half_mystery (0.000), km_no_spam_polka (0.048), km_retrofuture_dirty (0.056)
- PASS cl_verdi_traviata_la_traviata___brindisi___act_1__no__3_d7fb08 -> cl_verdi_traviata_la_traviata___brindisi___act_1__no__3_d7fb08 (0.000), km_sugar_plum_dark_mix (0.108), km_impromptu_in_blue (0.112)
- PASS km_stoic_morning -> km_stoic_morning (0.000), km_psychedelic_crater (0.116), km_dark_pad (0.117)
- PASS mo_grieg_peer_gynt_suite_no__1__op__46___i__morning -> mo_grieg_peer_gynt_suite_no__1__op__46___i__morning (0.000), mo_brahms_symphony_no__3_in_f_major__op__90___iv__allegro (0.186), cl_saint_saens_carnival_13___le_cygne__the_swan (0.224)
- PASS km_organic_grunge -> km_organic_grunge (0.000), km_fireflies_and_stardust (0.071), km_dentaneosuchus_hunt (0.078)
- PASS km_rising_tide -> km_rising_tide (0.000), km_rising_tide__faster (0.060), km_celebration (0.111)
- PASS km_dead_drop -> km_dead_drop (0.000), km_raw (0.027), km_malt_shop_bop (0.032)
- PASS km_heavy_heart -> km_heavy_heart (0.000), cl_wagner_valkyrie_wagner___ride_of_the_valkyries___arra_886004 (0.154), km_night_on_the_docks___piano (0.155)
- PASS km_farting_around -> km_farting_around (0.000), km_organic_grunge (0.080), km_fireflies_and_stardust (0.092)
- PASS km_realizer -> km_realizer (0.000), km_retrofuture_dirty (0.058), km_smash__sketch (0.078)
- PASS km_glee_club_polka -> km_glee_club_polka (0.000), km_super_power_cool_dude (0.030), km_blue_ska (0.033)
- PASS cl_saint_saens_carnival_14___finale -> cl_saint_saens_carnival_14___finale (0.000), km_ritual (0.183), km_what_child_is_this (0.222)
- PASS km_slow_jam -> km_slow_jam (0.000), km_sugar_plum_breakdown (0.142), km_monkoto (0.165)
- PASS km_krampus_workshop -> km_krampus_workshop (0.000), km_ghost_dance (0.057), km_zombie_hoodoo (0.087)
- PASS km_it_came_upon_a_midnight_clear -> km_it_came_upon_a_midnight_clear (0.000), km_angels_we_have_heard_on_high (0.118), km_ritual (0.125)
- PASS mo_mozart_symphony_no__40_in_g_minor__k__550___ii__andante -> mo_mozart_symphony_no__40_in_g_minor__k__550___ii__andante (0.000), mo_brahms_symphony_no__2_in_d_major__op__73___ii__adagio_ad6c58 (0.185), km_right_behind_you (0.211)
- PASS km_canon_in_d_interstellar_mix -> km_canon_in_d_interstellar_mix (0.000), km_floating_cities (0.080), km_frogs_legs_rag (0.082)
- PASS km_suvaco_do_cristo -> km_suvaco_do_cristo (0.000), km_angels_we_have_heard_on_high (0.127), km_tea_roots (0.137)
- PASS km_meatball_parade -> km_meatball_parade (0.000), km_on_the_passing_of_time (0.207), mo_brahms_symphony_no__1_in_c_minor__op__68___i__un_poco_d91225 (0.233)
- PASS km_suonatore_di_liuto -> km_suonatore_di_liuto (0.000), km_chill (0.142), km_pulse (0.151)
- PASS km_blown_away___no_percussion -> km_blown_away___no_percussion (0.000), km_shadowlands_1___horizon (0.086), km_enter_the_party (0.098)
- PASS km_prelude_in_c__bwv_846 -> km_prelude_in_c__bwv_846 (0.000), km_malt_shop_bop (0.030), km_funk_game_loop (0.033)
- PASS km_valse_gymnopedie -> km_valse_gymnopedie (0.000), cl_fucik_gladiators_julius_fucik___entry_of_the_gladiato_7cf03a (0.101), cl_satie_gymnopedies_gnossiennes_satie___gymnopedie_no__1 (0.107)
- PASS km_wah_game_loop -> km_wah_game_loop (0.000), km_brightly_fancy (0.046), km_motivator (0.052)
- PASS km_gonna_start -> km_gonna_start (0.000), km_gonna_start_v2 (0.009), km_dark_hallway__clean (0.065)
- PASS cl_vivaldi_seasons_summer___2__movement___adagio__john_harrison -> cl_vivaldi_seasons_summer___2__movement___adagio__john_harrison (0.000), cl_vivaldi_seasons_spring___2__movement___largo__john_harrison (0.185), cl_elgar_op12_salut_d_amour___op__12__arranged_for_piano (0.191)
- PASS km_symmetry -> km_symmetry (0.000), cl_saint_saens_carnival_08___personnages_a_longues_oreil_f8f96f (0.085), cl_saint_saens_carnival_04___tortues__tortoises (0.100)
- PASS km_waltz__tschikovsky_op__40 -> km_waltz__tschikovsky_op__40 (0.000), km_magic_forest (0.166), km_decline (0.195)
- PASS mo_mozart_marriage_of_figaro__marriage_of_figaro -> mo_mozart_marriage_of_figaro__marriage_of_figaro (0.000), mo_mendelssohn_hebrides_overture_fingal_s_cave (0.132), cl_saint_saens_carnival_12___fossiles__fossils (0.155)
- PASS km_old_road -> km_old_road (0.000), cl_saint_saens_carnival_07___aquarium (0.133), km_gymnopedie_no__3 (0.145)
- PASS km_robo_western -> km_robo_western (0.000), km_oh__christmas_tree (0.102), km_mourning_song (0.119)
- PASS km_happy_bee___surf -> km_happy_bee___surf (0.000), km_hackbeat (0.039), km_super_power_cool_dude (0.048)
- PASS km_zombie_chase -> km_zombie_chase (0.000), cl_wagner_valkyrie_wagner___ride_of_the_valkyries___wwv_86b (0.038), cl_saint_saens_carnival_10___volieres__aviary (0.120)
- PASS km_retrofuture_clean -> km_retrofuture_clean (0.000), km_retrofuture_dirty (0.080), km_pilot_error (0.102)
- PASS cl_saint_saens_carnival_10___volieres__aviary -> cl_saint_saens_carnival_10___volieres__aviary (0.000), km_dance_of_the_tuba_plum_fairy (0.035), km_dance_of_the_sugar_plum_fairy (0.063)
- PASS mo_brahms_symphony_no__3_in_f_major__op__90___ii__andante -> mo_brahms_symphony_no__3_in_f_major__op__90___ii__andante (0.000), mo_brahms_symphony_no__2_in_d_major__op__73___iii__alleg_2fa819 (0.151), cl_rimsky_korsakov_scheherazade_rimsky_korsakov___schehe_86b411 (0.174)
- PASS mo_mendelssohn_hebrides_overture_fingal_s_cave -> mo_mendelssohn_hebrides_overture_fingal_s_cave (0.000), mo_mozart_marriage_of_figaro__marriage_of_figaro (0.132), cl_vivaldi_seasons_summer___1__movement___allegro_non_mo_d0aa5f (0.157)
- PASS km_toccata_and_fugue_in_d_minor -> km_toccata_and_fugue_in_d_minor (0.000), mo_mozart_symphony_no_40_in_g_minor__1st_mov_molto_allegro (0.205), km_as_i_figure (0.226)
- PASS km_mandeville -> km_mandeville (0.000), km_flying_kerfuffle (0.101), km_night_in_venice (0.104)
- PASS km_classic_horror_2 -> km_classic_horror_2 (0.000), km_cello_suite__1_in_g___prelude (0.127), cl_massenet_meditation_massenet__jules___meditation___th_b273fa (0.147)
- PASS cl_tchaikovsky_symphony_no5_tchaikovsky___symphony_no__5_7ca793 -> cl_tchaikovsky_symphony_no5_tchaikovsky___symphony_no__5_7ca793 (0.000), cl_wagner_valkyrie_wagner___ride_of_the_valkyries___arra_886004 (0.186), km_brandenburg_concerto_no__4_in_g__movement_i__allegro___bwv_1 (0.191)
- PASS km_snare_bounce_polka -> km_snare_bounce_polka (0.000), km_hustle (0.029), km_super_power_cool_dude (0.034)
- PASS km_seven_off -> km_seven_off (0.000), km_stealth_groover (0.032), km_private_eye (0.057)
- PASS km_broken_reality -> km_broken_reality (0.000), km_stealth_groover (0.105), km_screen_saver (0.119)
- PASS km_fig_leaf_rag -> km_fig_leaf_rag (0.000), km_fig_leaf_rag___distressed (0.040), km_hit_the_streets (0.142)
- PASS km_arroz_con_pollo -> km_arroz_con_pollo (0.000), km_big_rock (0.058), km_cheery_monday (0.066)
- PASS cl_vivaldi_seasons_summer___1__movement___allegro_non_mo_d0aa5f -> cl_vivaldi_seasons_summer___1__movement___allegro_non_mo_d0aa5f (0.000), mo_mendelssohn_hebrides_overture_fingal_s_cave (0.157), km_quinn_s_song__a_new_man (0.181)
- PASS km_tea_roots -> km_tea_roots (0.000), km_dub_eastern (0.073), km_bicycle (0.079)

## Test 2: data curve fed in reverse (top-3)

- PASS machine_engine_013 -> machine_engine_013 (0.000), machine_engine_038 (0.000), machine_engine_011 (0.000)
- PASS hdfcbank_2018_drama -> hdfcbank_2018_drama (0.000), reliance_2024_drama (0.169), sbin_2014_drama (0.199)
- PASS hdfcbank_2013_shape -> hdfcbank_2013_shape (0.000), icicibank_2013_shape (0.110), nifty50_2013_shape (0.120)
- PASS adanient_2022_drama -> adanient_2022_drama (0.000), sbin_2022_drama (0.114), itc_2022_drama (0.122)
- PASS energy_week_2024-12-09 -> energy_week_2024-12-09 (0.000), infy_2014_shape (0.154), adanient_2020_shape (0.170)
- PASS nifty50_2018_drama -> nifty50_2018_drama (0.000), itc_2021_shape (0.066), tcs_2008_drama (0.105)
- PASS energy_week_2024-11-18 -> energy_week_2024-11-18 (0.000), nifty50_2019_shape (0.148), sbin_2017_shape (0.175)
- PASS crop_can_1961_2024 -> crop_can_1961_2024 (0.000), crop_tur_1961_2024 (0.168), itc_2015_drama (0.175)
- PASS nifty50_2016_shape -> nifty50_2016_shape (0.000), hdfcbank_2016_shape (0.012), itc_2016_shape (0.023)
- PASS infy_2022_shape -> infy_2022_shape (0.000), tcs_2022_shape (0.031), energy_week_2024-05-13 (0.154)
- PASS nifty50_2014_drama -> nifty50_2014_drama (0.000), icicibank_2014_drama (0.177), reliance_2014_drama (0.208)
- PASS adanient_2023q1_shape -> adanient_2023q1_shape (0.000), tcs_last12_shape (0.050), infy_2012_shape (0.074)
- PASS nifty50_2025_shape -> nifty50_2025_shape (0.000), reliance_2025_shape (0.025), hdfcbank_2009_shape (0.027)
- PASS bhartiartl_2017_drama -> bhartiartl_2017_drama (0.000), bhartiartl_2008_drama (0.149), tcs_2008_drama (0.170)
- PASS crop_rus_1992_2024 -> crop_rus_1992_2024 (0.000), crop_bgd_1961_2024 (0.162), energy_week_2024-06-10 (0.168)
- PASS itc_2025_shape -> itc_2025_shape (0.000), adanient_2008_shape (0.209), tcs_2025_shape (0.235)
- PASS machine_engine_030 -> machine_engine_030 (0.000), machine_engine_005 (0.000), machine_engine_033 (0.000)
- PASS nifty50_2014_shape -> nifty50_2014_shape (0.000), icicibank_2014_shape (0.010), hdfcbank_2014_shape (0.013)
- PASS icicibank_2025_drama -> icicibank_2025_drama (0.000), reliance_2025_drama (0.159), crop_nga_1961_2024 (0.178)
- PASS gdp_usa_1955_1969 -> gdp_usa_1955_1969 (0.000), nifty50_2022_drama (0.185), tcs_2020_drama (0.188)

## Test 3: synthetic shapes (top-3)

- slow build: We Wish you a Merry Christmas (99.0% match), Peer Gynt Suite No. 1, Op. 46 - IV. In the Hall Of The Mountain King (97.7% match), Divertissement - Pizzicato (from the ballet Sylvia) (95.3% match)
- explosive start: Ghost Story (92.3% match), Confused State (91.3% match), Villainous Treachery (79.6% match)
- rollercoaster: Cowboy Sting (100.0% match), Groundwork (99.9% match), Honey Bee (99.9% match)
- flat: unmatchable (flat curve) - expected