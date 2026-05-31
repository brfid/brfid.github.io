---
title: "Lessons from the Telegraph for LLM Agent Design"
date: 2026-04-21
lastmod: 2026-05-30
draft: false
tags: ["llm", "agents", "history", "workflow"]
---

This started as a question applied historians ask routinely: can we find lessons from history that inform current practice? The specific case was commercial telegraphy and LLM agents — two systems that compress language for expensive, noisy channels.

I went through a lot of telegraph techniques and operations asking what might be useful when working with LLMs. Almost everything survived — delimiters, confirmation, priority tiers, compression, validation, observability, access control — but as information management fundamentals, not telegraph-specific insights. They entered the general toolkit long ago. (Some comparisons are in the [appendix](#appendix-telegraph-practices-and-llm-agent-counterparts).)

But there's one area that might not have! A lessons from history? I give you: redundancy in control labels.

## What codebooks got right

Telegraph codebooks had to compress messages cheaply while ensuring a damaged codeword didn't silently become a different valid one. Bentley's rule: good codewords should differ by at least two letters.[^bentley] The ABC Code applied the same principle, screening out Morse-similar words.[^abc] Bellovin surveys the full design space — compression, error correction, confidentiality — and how codebook designers balanced all three.[^bellovin]

> Good compression leaves enough redundancy to detect mistakes.

This didn't carry forward into LLM agent design because the problem is newly common. LLM agents combine properties that make label confusability newly dangerous:

- probabilistic language generation (the model can produce near-miss strings)
- exact symbolic control (downstream code treats labels as exact inputs)
- natural-language prompts wrapped around short labels (easy to miscopy or misread)
- tool calls and routes with real side effects (wrong label → wrong action)

Recent research confirms this is not hypothetical. Qiu et al. show that LLM tool selection is sensitive to surface-level cues in tool names: assertive names, specific phrasing, and similar-looking alternatives all shift routing behavior measurably.[^toolprefs] Wang et al. demonstrate that small adversarial perturbations to tool names can reliably redirect tool calls to attacker-controlled tools.[^tooltweak]

Example labels that are too close:

```text
A1  /  AI  /  Al
prod  /  production  /  live
docs.api  /  doc.api
FACTCHECK_API  /  FACT_CHECK_API
```

In an agent system, these may route work, call tools, select environments, or satisfy exact enum values. A wrong valid label is worse than an invalid label, because invalid labels fail validation, wrong valid labels pass validation and trigger the wrong action.

## An agent-aware check

The check that matters is not just string similarity. It is string similarity weighted by what the label controls.

Generic similarity check:

```text
docs.api / doc.api — edit distance 1.
```

Agent-aware check:

```text
CRITICAL  docs.api / doc.api
route-name collision across different effects.
read-only route is one edit away from external-write route.
```

The severity boundary depends on the label's role:

- Two confusable read-only routes: annoying but low risk.
- Two confusable routes where one is destructive: critical.
- Two confusable environment labels that both mean production: critical.
- Two confusable enum values the model must emit exactly: high risk.

I am experimenting with small tools to check this: [wireword](https://github.com/brfid/wireword). The rules are simple and include visual confusables, edit-distance-one pairs, case-only and punctuation-only differences, plural/stem collisions, and production-alias overload.

## Appendix: telegraph practices and LLM-agent counterparts

| Telegraph practice | What it was | LLM-agent version | How it survived |
|---|---|---|---|
| `STOP` and spelled punctuation | Explicit delimiters in a whitespace-charged medium | Source/task boundary markers | Structured data formats (XML, JSON, protocol framing) |
| Repeat-back | Operator reads message back for sender confirmation | Human approval gates | Confirmation dialogs, two-person integrity |
| Service classes | Ordinary, urgent, night letter — priority and cost tiers | Model routing, effort levels | QoS, SLAs, tiered pricing |
| Codebooks | Substitution tables compressing phrases to single words | Prompt libraries, macros | Compression, abbreviation, lookup tables |
| Word-count checks | Validation that the received message had the expected length | Output validation, schema checks | Checksums, content-length headers, schema validation |
| Operators | Human review at relay points for accuracy and routing | Linters, traces, observability | Monitoring, logging, human-in-the-loop review |
| Private codes | Custom substitution hiding meaning from operators | PII masking, redaction | Encryption, access control, data masking |

## Sources

[^bentley]: E. L. Bentley, ["Codes: Their Nature and Manipulation"](https://www.jmcvey.net/cable/harmsworth_2.htm), transcribed by John McVey. Bentley describes the two-letter-difference rule and explains that it prevents a one-letter mutilation from silently becoming another valid codeword.

[^abc]: John McVey, ["A.B.C. Telegraphic Codes, seven editions 1873-1936"](https://jmcvey.net/cable/scans/ABC.htm). The page quotes the 1920 sixth edition on five-letter codewords built with at least a two-letter difference and notes the code's attention to Morse similarities.

[^crowther]: Mary Owens Crowther, [_How to Write Letters_](https://www.gutenberg.org/ebooks/22222.html.images) (1922), telegram section. Crowther summarizes the ten-word minimum, the 50-word Night Letter, and the 50-word Day Letter.

[^histstats]: U.S. Bureau of the Census, [_Historical Statistics of the United States, Colonial Times to 1957_](https://www2.census.gov/library/publications/1960/compendia/hist_stats_colonial-1957/hist_stats_colonial-1957-chR.pdf), Series R 68-71 and notes to Series R 53-67. The tables list domestic telegraph message rates from New York to selected cities and describe private-line telegraph service as leased facilities billed by contractual periodic rent.

[^ross]: Nelson E. Ross, [_How to Write Telegrams Properly_](https://en.wikisource.org/wiki/How_to_Write_Telegrams_Properly) (1928), "How Tolls Are Computed" and "Punctuation Marks." Ross explains domestic body-word billing, cable/radiogram address billing, and the rule that requested punctuation marks were counted and charged as words.

[^wu1869]: Western Union Telegraph Company, [_The Proposed Union of the Telegraph and Postal Systems_](https://www.gutenberg.org/ebooks/62214.html.images) (1869). Western Union gives the 1866 New York-to-Boston tariff as 30 cents for ten words, exclusive of address and signature.

[^bellovin]: Steven M. Bellovin, ["Compression, Correction, Confidentiality, and Comprehension: A Modern Look at Commercial Telegraph Codes"](https://www.usenix.org/conference/usenixsecurity09/technical-sessions/presentation/compression-correction-confidentiality), USENIX Security 2009. Surveys the design tradeoffs in commercial telegraph codebooks across compression, error resistance, and secrecy.

[^toolprefs]: Qiu et al., ["Tool Preferences in Agentic LLMs Are Unreliable"](https://arxiv.org/abs/2505.18135) (2025). Shows that LLM tool selection is measurably sensitive to surface-level cues in tool names and descriptions.

[^tooltweak]: Wang et al., ["ToolTweak: Attack on Tool Selection of Large Language Models"](https://arxiv.org/abs/2510.02554) (2025). Demonstrates that adversarial perturbations to tool names can reliably redirect LLM tool calls.
