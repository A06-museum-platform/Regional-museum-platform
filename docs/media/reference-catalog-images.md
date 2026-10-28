# Reference collection images

These 13 images illustrate subjects in the demonstration catalog. They are not photographs of the accessioned objects. Existing original-catalog media remains unchanged. The website labels these immutable uploads as **Reference photo** and links their source and license. A replacement upload has a different key and does not inherit this label.

Images use Wikimedia-generated previews (960 px maximum width, or the smaller original). The Kaurna-language book uses scan page 7. No other edits were made. CSS may crop card previews; the collection detail shows the full image. Share-alike images retain their stated license.

| Collection ID | Image / context | Creator | Source and license |
|---|---|---|---|
| 1 | Malachite-bearing ore at Burra, South Australia. | Geomartin | [Source](https://commons.wikimedia.org/wiki/File:Burra_erz.jpg) · [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) |
| 2 | A Victorian Telegraph Service key and relay from the 1860s; a related Australian telegraph instrument. | Museums Victoria | [Source](https://commons.wikimedia.org/wiki/File:Telegraph_Key_%26_Relay_-_Victorian_Telegraph_Service,_1860s.jpg) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) |
| 3 | A German ledger from 1828, illustrating historical bookkeeping. | RaphaelQS | [Source](https://commons.wikimedia.org/wiki/File:Ledger.png) · [CC0](https://creativecommons.org/publicdomain/zero/1.0/deed.en) |
| 4 | William Duke’s 1848 painting of the whaling ship Pacific; a historical whaling reference. | William Duke | [Source](https://commons.wikimedia.org/wiki/File:The_Whaling_Ship_Pacific_by_William_Duke_1848_Art_Gallery_of_South_Australia_20065P29.jpg) · [Public domain](https://creativecommons.org/publicdomain/mark/1.0/) |
| 5 | The B engine flywheel at Claymills Victorian Pumping Station, England; an example of steam machinery. | David Dixon | [Source](https://commons.wikimedia.org/wiki/File:Claymills_Victorian_Pumping_Station,_B_Engine_Flywheel_-_geograph.org.uk_-_5394815.jpg) · [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0) |
| 6 | An azurite specimen from Burra Mine, South Australia; the catalogued record is from Moonta. | JJ Harrison ( https://www.jjharrison.com.au/ ) | [Source](https://commons.wikimedia.org/wiki/File:Azurite,_Burra_Mine,_South_Australia.jpg) · [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) |
| 7 | A Morse sounder with a wooden resonator box. | ArnoldReinhold | [Source](https://commons.wikimedia.org/wiki/File:Morse_sounder_at_MIT_flea.jpg) · [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| 8 | A historical map of Australia’s Overland Telegraph route, held by the State Library of South Australia. | Telecom Australia | [Source](https://commons.wikimedia.org/wiki/File:Map_of_Australia%27s_Overland_Telegraph_Line_(SLSA_B_78437).png) · [Public domain](https://creativecommons.org/publicdomain/mark/1.0/) |
| 9 | A Beyer, Peacock builders plate from NSW locomotive 6029, dated 1953; a related railway artefact. | Christine Lynch | [Source](https://commons.wikimedia.org/wiki/File:Beyer,_Peacock_%26_Co._Ltd_builder%27s_plate_on_NSWGR_AD60_class_no._6029_(Christine_Lynch).jpg) · [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) |
| 10 | A historical view of Burra mines based on a watercolour by S. T. Gill, circa 1850. | Ernest Gall | [Source](https://commons.wikimedia.org/wiki/File:Photo_of_ST_Gill%27s_watercolour_sketch_of_Burra_mines_by_Ernest_Gall,_ca_1850_(SLSA_PRG-631-2-1400).jpg) · [Public domain](https://creativecommons.org/publicdomain/mark/1.0/) |
| 11 | A marine chronometer in the British Museum; a related navigation instrument. | BabelStone; edited by Fæ | [Source](https://commons.wikimedia.org/wiki/File:British_Museum_Marine_Chronometer.jpg) · [CC0](https://creativecommons.org/publicdomain/zero/1.0/deed.en) |
| 12 | Title page of Teichelmann and Schürmann’s 1840 grammar and vocabulary of the Adelaide / Kaurna language (scan page 7). | C. G. Teichelmann and C. W. Schürmann; scan via Internet Archive / Wikimedia Commons | [Source](https://commons.wikimedia.org/wiki/File:Outlines_of_a_grammar,_vocabulary,_and_phraseology,_of_the_aboriginal_language_of_South_Australia_-_spoken_by_the_natives_in_and_for_some_distance_around_Adelaide_(IA_b33096156).pdf) · [Public domain](https://creativecommons.org/publicdomain/mark/1.0/) |
| 13 | A winding drum at Sir Francis Level, England; an example of mining machinery. | b3tarev3 from England | [Source](https://commons.wikimedia.org/wiki/File:Winding_Drum_(13652034865).jpg) · [Public domain](https://creativecommons.org/publicdomain/mark/1.0/) |

## Release order

1. Stage immutable uploads in Supabase and byte-check their R2 mirrors. Do not attach them to catalog rows yet.
2. Merge and deploy the attribution UI after approval and green CI.
3. Back up the hosted database. In one guarded transaction, attach only these images to the expected collection IDs/titles that still have no images. Preserve existing media, descriptions, publication state, accounts and roles. Keep item 13 as a draft.
4. Verify public detail credits, images and browser fallback. Do not claim activation until these checks pass.

The private audit under ignored `backups/catalog-photos-20261028/` records source metadata, local file hashes, staged URLs and the proposed associations. The public credit map is `frontend/src/data/catalogPhotoCredits.js`.
