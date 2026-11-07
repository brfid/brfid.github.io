# Font sources

The site serves fonts from `hugo/static/fonts/`. Preserve the original font bytes and license when replacing a vendored font.

The Newsreader and IBM Plex Mono source mappings below were recovered through byte-for-byte comparisons with versioned Google Fonts downloads; their original download transactions were not recorded. Those files embed the SIL Open Font License URL.

## Source Serif 4

The variable roman and italic fonts come from Adobe's [Source Serif 4.005 release](https://github.com/adobe-fonts/source-serif/releases/tag/4.005R), tag `4.005R`, pinned to commit [`2823e993c53fca27c5c8749f529b56a5a7c77b6b`](https://github.com/adobe-fonts/source-serif/commit/2823e993c53fca27c5c8749f529b56a5a7c77b6b). The files are renamed locally without modifying their contents. The upstream [SIL Open Font License](licenses/source-serif4.txt) is retained from `LICENSE.md` at that commit, with trailing whitespace removed.

| Local file | Upstream file at the pinned commit | SHA-256 |
|---|---|---|
| `hugo/static/fonts/source-serif4-roman.woff2` | [`WOFF2/VAR/SourceSerif4Variable-Roman.ttf.woff2`](https://raw.githubusercontent.com/adobe-fonts/source-serif/2823e993c53fca27c5c8749f529b56a5a7c77b6b/WOFF2/VAR/SourceSerif4Variable-Roman.ttf.woff2) | `940a76eda1388de39d38c8e7a79bf6ea058a387faee0a9f33c8d25c6ba05e1be` |
| `hugo/static/fonts/source-serif4-italic.woff2` | [`WOFF2/VAR/SourceSerif4Variable-Italic.ttf.woff2`](https://raw.githubusercontent.com/adobe-fonts/source-serif/2823e993c53fca27c5c8749f529b56a5a7c77b6b/WOFF2/VAR/SourceSerif4Variable-Italic.ttf.woff2) | `9d28b5749a1ad096a295cb607c521bd1af4cd9979b6f37332daf70143149fb44` |
| `docs/licenses/source-serif4.txt` | [`LICENSE.md`](https://raw.githubusercontent.com/adobe-fonts/source-serif/2823e993c53fca27c5c8749f529b56a5a7c77b6b/LICENSE.md) | `c21d7293d87b6d7ab1d0229a2f55b77f33a7613a6a4e66f6693d68d7d8d09464` |

## Newsreader

The roman variable files identify themselves as Newsreader version 1.003, copyright 2020 The Newsreader Project Authors. Both contain weight (`wght`) values from 200 to 800 and optical-size (`opsz`) values from 6 to 72.

| Local file | Verified upstream source | SHA-256 |
|---|---|---|
| `hugo/static/fonts/newsreader-latin.woff2` | [v26 Latin](https://fonts.gstatic.com/s/newsreader/v26/cY9AfjOCX1hbuyalUrK4397yjIJFJpc.woff2) | `01817351be3edfc1714fe6d60ddea6a22a169a5ebd033b50c7f9495e5d9c386a` |
| `hugo/static/fonts/newsreader-latin-ext.woff2` | [v26 Latin extended](https://fonts.gstatic.com/s/newsreader/v26/cY9AfjOCX1hbuyalUrK439DyjIJFJpeBZQ.woff2) | `cbca001188852d514d8654be7ddc97868f039bdf986b926ec5c985c117853cfd` |
| `docs/licenses/newsreader.txt` | [`ofl/newsreader/OFL.txt`](https://raw.githubusercontent.com/google/fonts/991ce1de6075188e6b8977a5aa9fcd3610a4e946/ofl/newsreader/OFL.txt) | `865f0949b59fab5925506f80102dff3d12e8666412daf52d212db969d40adc25` |

The [retained license](licenses/newsreader.txt) comes from Google Fonts commit `991ce1de6075188e6b8977a5aa9fcd3610a4e946`, with trailing whitespace removed and a final newline added.

## IBM Plex Mono

The regular (400) and medium (500) files identify themselves as IBM Plex Mono version 2.3, copyright 2017 IBM Corp.

| Local file | Verified upstream source | SHA-256 |
|---|---|---|
| `hugo/static/fonts/plex-mono-400-latin.woff2` | [v20 regular Latin](https://fonts.gstatic.com/s/ibmplexmono/v20/-F63fjptAgt5VM-kVkqdyU8n1i8q131nj-o.woff2) | `c36f509c0a8f9f85f29cb44bc8701d8a9e0b14c499e77a884f789ead7093a7ac` |
| `hugo/static/fonts/plex-mono-400-latin-ext.woff2` | [v20 regular Latin extended](https://fonts.gstatic.com/s/ibmplexmono/v20/-F63fjptAgt5VM-kVkqdyU8n1iEq131nj-otFQ.woff2) | `f1050dc5317b43434c0aeda599d4624c774ffc162e87a8cf204b949b6a85816d` |
| `hugo/static/fonts/plex-mono-500-latin.woff2` | [v20 medium Latin](https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3twJwlBFgsAXHNk.woff2) | `a76f53ca6612e7b3828eec2311098675b7f9849ae4169a8bcef6302aec02a6c0` |
| `hugo/static/fonts/plex-mono-500-latin-ext.woff2` | [v20 medium Latin extended](https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3twJwl5FgsAXHNlYzg.woff2) | `77f03e26f981c582bdba3a7abed4baa2d3149211c01366bb3ab3ba7622ec4ae5` |
| `docs/licenses/ibm-plex-mono.txt` | [`ofl/ibmplexmono/OFL.txt`](https://raw.githubusercontent.com/google/fonts/465b90c97b4de569e0b546bb2536900194cf7187/ofl/ibmplexmono/OFL.txt) | `d741e57d5f865e294df801f96b7b5161a88b211df65887e4358d271c9fc5fb4f` |

The [retained license](licenses/ibm-plex-mono.txt) comes from Google Fonts commit `465b90c97b4de569e0b546bb2536900194cf7187`, with CRLF line endings normalized to LF and trailing whitespace removed.
