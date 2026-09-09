---
title: "Doc rot: two questions for a documentation pipeline"
date: 2026-07-11
draft: false
description: "End-to-end reasoning and software maintenance suggest two questions for a docs pipeline: what evidence supports a claim, and what brings it back for review?"
tags: ["documentation", "docs-as-code", "software-maintenance", "testing"]
---

A documentation build can pass while a page gives advice that no longer fits the product. The links still resolve, the examples still compile, and the recommended approach still works. A newer approach may now serve readers better, without anything in the pipeline prompting someone to reconsider the old recommendation.

I started thinking about this as an application of the end-to-end principle to documentation pipelines. That led me to ask what a check can actually establish. Reading it alongside work on software evolution and maintenance suggested a second question: what brings a claim back for review when the circumstances supporting it change?

Together, these ideas offer a way to identify some of the maintenance work a docs pipeline needs:

1. What evidence would let a person or check assess this claim?
2. What will bring it back for reassessment, and who will act on the result?

## What can a check establish?

Saltzer, Reed, and Clark's end-to-end argument concerns the placement of functions in a system. When a function requires knowledge and help from the application at the endpoints, mechanisms inside the communication system cannot completely provide it. Those mechanisms can still be useful. In their file-transfer example, checks within the network can reduce errors, while the application still needs to verify the transferred file and handle failure.[^saltzer-1984]

For documentation, I find the useful analogy in asking what information a check needs to support the conclusion we want to draw. A Markdown linter has enough information to check its formatting rules. It has no evidence about whether a recommended integration suits the reader's task. That assessment may require current product knowledge and experience with how people use it.

The fit is partial: a docs pipeline combines tools and judgments that do not necessarily form a neat hierarchy, and a recommendation may have no single conclusive test. The end-to-end argument helps frame the question; identifying adequate evidence for a particular claim remains part of the work.

This gives routine checks a useful, bounded role. A link checker can report whether a link resolved when it ran. A test can show how an example behaved under specified conditions. Those results contribute evidence about the page. A claim about which approach readers should choose needs evidence suited to that decision.

## What brings the claim back for review?

An adequate review at publication establishes something about the conditions at that time. Keeping the page useful also means noticing when those conditions may have changed.

Software maintenance research provides a reason to ask about this. Lehman described how programs that reflect a changing external reality can become less useful unless they evolve.[^lehman-1980] Parnas distinguished aging caused by changing expectations from aging introduced through modifications, and described how deferred documentation updates make later changes harder.[^parnas-1994]

The corresponding problem in docs is easy to imagine. An engineer reviews an integration guide at launch. Later, the product gains a new integration method. The original method still works, so its tests keep passing. The recommendation needs another look, but a trigger tied only to changes in the old method may never request that review.

If we want the guide to remain current, someone needs a way to notice the relevant change, reassess the guidance, and decide what to do with it. A release review, a connection to the responsible product team, or a scheduled review could provide that opportunity. The choice depends on how the product changes and what the team can sustain.

## Following one claim through the pipeline

Consider a narrower claim: under the documented test conditions, `GET /foo?mode=summary` returns HTTP `200` in a specified supported version and environment.

We can distinguish the evidence a check supplies from whether it runs again:

{{< maintenance-grid >}}

The recurring contract test gives us a way to gather fresh evidence about the response. Its usefulness depends on whether the conditions still match the claim, whether the test continues to run, and whether anyone investigates failures. The layout and structure checks remain useful for the properties they assess.

The distinction helps locate different kinds of missing work. We may lack a check or review with relevant evidence. We may have that review available but no reason for it to happen again. Or reviews may recur while their findings wait indefinitely for attention. Ownership helps organize the response, but the responsible person or team also needs time and authority to act.

## Choosing maintenance work the team can sustain

I would start with claims whose failure would materially affect a reader's task. For a behavior that can be tested, record the relevant conditions, connect the test to the claim, and decide what should happen when the result changes. Maintaining the test is part of that commitment.

For recommendations, responsibility at the page or feature level may be more practical. Connecting a guide to a product area can help catch changes that a dependency on one endpoint would miss, including the arrival of a new alternative. A periodic review can provide another opportunity to notice changes, at a frequency that reflects both the consequences of stale advice and the available review time.

These arrangements have costs. Triggers generate triage work, mappings become outdated, and scheduled reviews compete with other tasks. Sometimes the appropriate response will be to narrow a claim, state its version or conditions, or retire guidance the team can no longer support.

For an important page, the two questions make those commitments easier to examine: what evidence supports its claims, and what will bring them back for reconsideration? The answers can help a team decide where another test would help, where review is needed, and what continuing work it is taking on by publishing the page.

## Notes

[^saltzer-1984]: J. H. Saltzer, D. P. Reed, and D. D. Clark, "[End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf)," *ACM Transactions on Computer Systems* 2, no. 4 (1984): 277–288. See the opening statement of the argument and the sections "End-to-end caretaking," "Performance aspects," and "Identifying the ends."

[^lehman-1980]: M. M. Lehman, "[Programs, Life Cycles, and Laws of Software Evolution](https://users.ece.utexas.edu/~perry/education/SE-Intro/lehman.pdf)," *Proceedings of the IEEE* 68, no. 9 (1980): 1060–1076. See the discussion of E-programs and the first law of software evolution, especially p. 1068. The application to documentation here is mine.

[^parnas-1994]: D. L. Parnas, "[Software Aging](https://www.eecs.yorku.ca/course_archive/2009-10/W/6431/Parnas.pdf)," *Proceedings of the 16th International Conference on Software Engineering* (1994): 279–287. See §§2.1–2.2, p. 280, on changing expectations, modifications, and deferred documentation updates.
