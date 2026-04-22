---
title: "Wireword: Agent Control Words Should Be Hard to Misread"
date: 2026-04-21
draft: true
tags: ["llm", "agents", "history", "workflow"]
---

This is a research note for [Wireword](https://github.com/brfid/wireword), a small tool I am building to lint LLM agent control words.

By control words, I mean short labels that can change what an agent does:

- route names
- tool names
- prompt macro names
- environment targets
- approval targets
- exact enum values the model must emit

The goal is narrow: make labels that control agent behavior harder to misread, miscopy, or misroute.

## Of words and tokens being expensive

This started with [caveman-style LLM output](https://github.com/juliusbrussee/caveman). The useful comparison is not really cavemen. It is telegraphese: compressed language for an expensive channel.

Western Union did not bill like an LLM API, but the pressure was similar. Ordinary domestic telegrams were billed by chargeable body word, usually with a ten-word minimum; address, signature, and date were free, while extra body words cost more.[^ross] A ten-word sentence from New York to Boston could cost 30 cents.[^wu1869]

That maps to LLM work in two basic ways:

- **Token cost:** shorter turns are cheaper.
- **Context quality:** shorter turns leave less low-information text in the conversation history.

The second point is not just aesthetic. Long histories are not used perfectly. Irrelevant text can distract the model or bury the useful constraint.

But compression has a failure mode. If compressed labels become too similar, the model has less redundancy to recover the intended control word.

## Learning from telegraphy

I looked at other telegraph practices to see what might apply to LLM agents. Could Victorian engineers provide fresh insights for our changing world? No, except for one thing, sort of.

Most parallels are useful but general:

| Telegraph practice | General pattern | LLM-agent version |
|---|---|---|
| `STOP` and spelled punctuation | delimiters | source/task boundaries |
| repeat-back | confirmation | human approval gates |
| service classes | priority and cost tiers | model routing / effort levels |
| codebooks | macros | prompt libraries |
| word-count checks | validation | output checks |
| operators | review and observability | linters / traces |
| private codes | substitution | PII masking |

These are durable information-management practices. They are worth remembering, but they do not justify a new tool by themselves.

The more specific lead was codeword design.

## Compression with redundancy

Commercial telegraph codebooks had to balance compression and recoverability. A codeword had to be short enough to save money, but distinct enough that a damaged word did not silently become another valid word.

E. L. Bentley described the rule directly: good codewords should differ by at least two letters. Then a one-letter mutilation produces an invalid codeword, not the wrong valid codeword.[^bentley]

The ABC Code used the same principle. John McVey's index quotes the 1920 sixth edition saying its five-letter codewords were built with at least a two-letter difference. The same note says the compilers considered Morse similarities and removed risky words.[^abc]

Useful rule:

> Good compression leaves enough redundancy to detect mistakes.

## The LLM agent version

This problem is not unique to LLMs. Similar issues appear in APIs, command-line flags, protocol enums, medication names, service names, and airport codes.

LLM agents make the problem newly common because they combine:

- probabilistic language generation
- exact symbolic control
- natural-language prompts around short labels
- tool calls and routes with real side effects

Example labels:

```text
A1
AI
Al
prod
production
live
docs.api
doc.api
FACTCHECK_API
FACT_CHECK_API
```

These are not just strings. In an agent system, they may route work, call tools, select environments, expand macros, approve targets, or satisfy exact enum values.

The risk boundary is narrow. Similar labels matter when three conditions hold:

- the label is visible to the model or copied through natural language
- the model or a human can choose or emit the label
- downstream code treats the label as an exact control input

A wrong valid label is worse than an invalid label. Invalid labels can fail validation. Wrong valid labels can pass validation and trigger the wrong action.

This matters less when routing is deterministic, internal IDs are hidden from the model, schemas constrain the choice, or a UI forces selection from canonical options.

So Wireword should not only ask whether two strings are similar. It should ask:

- What kind of label is this?
- Can the model emit it?
- Does a parser require an exact match?
- What happens if the wrong label is chosen?
- Does it target production or another external system?

### Generic check vs agent-aware check

Generic similarity check:

```text
docs.api / doc.api
Reason: edit distance 1.
```

Agent-aware check:

```text
CRITICAL docs.api / doc.api
Reason: route-name collision across different effects.
Risk: read-only route is one edit away from external-write route.
Fix: rename to ROUTE_DOCS_REVIEW and ROUTE_DOCS_PUBLISH.
```

Generic similarity check:

```text
prod / production / live
Reason: related strings.
```

Agent-aware check:

```text
CRITICAL prod / production / live
Reason: multiple production-like environment labels.
Risk: agent may choose an inconsistent deployment target.
Fix: use ENV_PRODUCTION as the only valid production label.
```

That is the product line: do not only lint strings. Lint control words by the action they can trigger.

### V1 plan

The tool is [Wireword](https://github.com/brfid/wireword). V1 should stay small.

It should lint two layers:

- **raw labels:** visual confusables, edit-distance-one pairs, case-only differences, punctuation-only differences, plural/stem collisions, and production-like aliases
- **agent-aware labels:** routes, tools, environments, approval targets, and exact enum values, with severity based on the effect of choosing the wrong label

The useful output is not just `these strings are similar`. It is `these strings are similar, the model can see or emit them, and confusing them could call the wrong tool, route work to the wrong place, or target the wrong environment`.

Representative targets:

- MCP servers with model-visible tools
- router or handoff agents
- graph-based agent workflows
- skill/plugin systems with named routes
- exact enum outputs consumed by parsers

The repo should carry the detailed CLI examples, fixtures, and tests. This note only needs the argument.

### What Wireword is not

Wireword is not:

- an agent framework
- a prompt framework
- a general security scanner
- a replacement for schemas or constrained decoding
- a proof that LLMs confuse every similar label
- necessary when labels are hidden behind deterministic routing, internal IDs, or strict UI selection

It is a narrow lint pass for labels that become model-visible or human-visible control inputs.

## Conclusion

Telegraph codebooks might inspire useful linting for LLM agent control identifiers.

## Sources

[^bentley]: E. L. Bentley, ["Codes: Their Nature and Manipulation"](https://www.jmcvey.net/cable/harmsworth_2.htm), transcribed by John McVey. Bentley describes the two-letter-difference rule and explains that it prevents a one-letter mutilation from silently becoming another valid codeword.

[^abc]: John McVey, ["A.B.C. Telegraphic Codes, seven editions 1873-1936"](https://jmcvey.net/cable/scans/ABC.htm). The page quotes the 1920 sixth edition on five-letter codewords built with at least a two-letter difference and notes the code's attention to Morse similarities.

[^crowther]: Mary Owens Crowther, [_How to Write Letters_](https://www.gutenberg.org/ebooks/22222.html.images) (1922), telegram section. Crowther summarizes the ten-word minimum, the 50-word Night Letter, and the 50-word Day Letter.

[^histstats]: U.S. Bureau of the Census, [_Historical Statistics of the United States, Colonial Times to 1957_](https://www2.census.gov/library/publications/1960/compendia/hist_stats_colonial-1957/hist_stats_colonial-1957-chR.pdf), Series R 68-71 and notes to Series R 53-67. The tables list domestic telegraph message rates from New York to selected cities and describe private-line telegraph service as leased facilities billed by contractual periodic rent.

[^ross]: Nelson E. Ross, [_How to Write Telegrams Properly_](https://en.wikisource.org/wiki/How_to_Write_Telegrams_Properly) (1928), "How Tolls Are Computed" and "Punctuation Marks." Ross explains domestic body-word billing, cable/radiogram address billing, and the rule that requested punctuation marks were counted and charged as words.

[^wu1869]: Western Union Telegraph Company, [_The Proposed Union of the Telegraph and Postal Systems_](https://www.gutenberg.org/ebooks/62214.html.images) (1869). Western Union gives the 1866 New York-to-Boston tariff as 30 cents for ten words, exclusive of address and signature.
