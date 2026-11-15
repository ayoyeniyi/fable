# Fonts for translations the headset cannot show as text

Downloaded by `tools/fetch_fonts.py` (not committed: 36.5 MB, kept on the Mac and copied to the hosted service by
`deploy/deploy.sh` with the rest of `content/`). Used only by the preparation service (`interpreter/internal/textimg`)
to draw Translate's answers in scripts that TextMeshPro on the headset cannot shape or lay out right to left, and by
`fable-interpreter render-names` to draw the language picker's native names into
`unity/Fable/Assets/Fable/Resources/LanguageNames.png` (56 kB, the only part that ships in the app).

All are from the Noto project, copyright The Noto Project Authors, under the **SIL Open Font License 1.1**
(`OFL.txt` here). Fetched 2026-11-14, pinned to commits `cfa91e36c7240b622fa7fcd3a90eeff15e28ae1c` of
https://github.com/notofonts/notofonts.github.io (hinted TTF) and `f8d157532fbfaeda587e826d4cd5b21a49186f7c` of
https://github.com/notofonts/noto-cjk (Serif/SubsetOTF).

| file | script, languages | SHA-256 |
|---|---|---|
| NotoSerif-Regular.ttf | Latin, Cyrillic, Greek fallback; Yoruba | 19e72cd8d595fae5bd74a5206f5d938512e1183d4fed7abb1ec1be1d7efa5f88 |
| NotoNaskhArabic-Regular.ttf | Arabic, Persian | 6f0a92031367b2f5a2078fe9d24f3433122b61a0bad57c423aad8f3c39aa2e6e |
| NotoNastaliqUrdu-Regular.ttf | Urdu | 4d05b6821862ca1f3c80c47c80a352b47dd349ab73814f60e377eea311e0e42c |
| NotoSerifHebrew-Regular.ttf | Hebrew | dfd5a6aefe97a99f68fe43388342913d50bb9fbf6d3afc4d2c7725661bc4a2b1 |
| NotoSerifDevanagari-Regular.ttf | Hindi, Marathi, Nepali | e272d11d271c61a8d5d0f65764fd368ae53b9f9dabcce244a8941aa8f32ccc70 |
| NotoSerifBengali-Regular.ttf | Bengali | c1743dce480147e4563e479ddc31d5ff6544372437428622a54c7c867c50f55b |
| NotoSerifGurmukhi-Regular.ttf | Punjabi | 5ef2d04a6d6fd22959989d14148dcf0ffbb970cc35e6316ba63cd5c146f32667 |
| NotoSerifGujarati-Regular.ttf | Gujarati | b8961ff6faf8e5561e3d0109953c4a9798e9bb8e8d48f66c3d1ef038fe45c940 |
| NotoSerifTamil-Regular.ttf | Tamil | 8a8cb015a3afec2998e01aabcb42fb365994132d95dbc2150208b4fefd8dc2e4 |
| NotoSerifTelugu-Regular.ttf | Telugu | 2b376e0351fb140f2edad9c54e8977f4f1effc4fe72443e152b3f6ad392c6f5f |
| NotoSerifKannada-Regular.ttf | Kannada | 95a78c95359dc59b9ec56bdc5bdf8a9642394d2ef87ded945fb3885893b3eac6 |
| NotoSerifMalayalam-Regular.ttf | Malayalam | 45c34ac8c169a37a4fbb5b8fbf507def328bbf36180b08095726d460d577ec1d |
| NotoSerifThai-Regular.ttf | Thai | 747b5bb1fdd329850ddd3218d872a3d2a96ab0dd544f51e5300c6d1b12071b62 |
| NotoSerifEthiopic-Regular.ttf | Amharic | 4d14f10b7436e762d41ddd9486acdc708744bf377a575d855b81b847b9590779 |
| NotoSerifSC-Regular.otf | Chinese (Simplified) | e8f396decc1f0963a016a989c3d8852e863d1350996f573860a80767c83a1cd3 |
| NotoSerifTC-Regular.otf | Chinese (Traditional) | 63515eb0622d589a2f4062e8757c598b3da3bffd053f69abd181c210158ef10c |
| NotoSerifJP-Regular.otf | Japanese | 2c9a12dbd4f2408c4610c7ee84a108b62d7236c3775baed618c64d9cb44b2f04 |
| NotoSerifKR-Regular.otf | Korean | 5ea012e15cb7eacc1f680aee1703f3b164791b1443ea3e52b65080cca5d179cf |
