---
title: "Doc rot: the maintenance gap the end-to-end argument leaves open"
date: 2026-07-11
draft: false
description: "Documentation can pass every existing check while losing fit with the product. Keeping it current requires both the right evidence and a maintained path back after change."
tags: ["documentation", "docs-as-code", "software-maintenance", "testing"]
---

Documentation does not have to change to become stale because the product (or the world) can move around it.

Software research described this maintenance problem decades ago. Lehman showed that a static program can become less useful as the reality it reflects changes.[^lehman-1980] Parnas described software that had aged "even though nobody has touched it" and documentation that becomes "increasingly inaccurate" when updates are deferred.[^parnas-1994]

A page can keep passing every existing check while losing that fit with the product, or its fit with the product in the world. The neglected failure is not that a check returns the wrong verdict. It is that the person or check able to answer is never called again after change.

## Two questions

A docs pipeline combines automated checks, review tasks, and people. Each can answer some questions and not others. A Markdown linter can report whether a file follows its rules. A live contract test can report observed API behavior. Choosing the current integration path requires product and user evidence.

Two questions expose the difference:

1. Can this person or check answer the claim with current evidence?
2. What will make that person or check look again over time, and who is responsible for acting on the result?

The end-to-end argument explains the first question. Saltzer, Reed, and Clark show that complete implementation depends on knowledge held by the application at the endpoints, although a partial lower-level version may still improve performance.[^saltzer-1984] Applied to documentation, the person or check must be able to reach the evidence the claim requires. A live contract test can answer a narrow question about endpoint behavior. A recommendation about when to use that endpoint needs current product and user evidence.

The second question adds time. An engineer can verify behavior during launch and never be asked again after release. A linter can run on every release while checking only form. The first has an answer without a return path; the second returns without an answer. A maintained path needs both a reliable trigger or cadence and someone responsible for the result.

## The grid

Carry one machine-testable claim through all four cells: "`GET /foo?mode=summary` returns HTTP `200` in the supported release environment."

{{< maintenance-grid >}}

The bottom row is useful when its scope is explicit. A recurring linter keeps reporting on form; it does not report the endpoint's current response. A change trigger also cannot answer the claim. It becomes useful by routing the page to a test or reviewer that can. The trigger and the reviewer together create the maintained path.

The grid uses a contract claim because a machine can answer it. A recommendation is harder. Deciding which integration path readers should use requires current product and user evidence. The same maintenance question applies: what event or schedule returns that recommendation to someone who can reassess it?

## The known failure and the quiet one

The familiar failure comes from reading a bounded green result as a broader verdict. For code, a mismatch sometimes announces itself through a test, type check, or runtime failure already operating for another reason. Many documentation claims have no executable consequence. A link checker reports whether it could reach a link when it ran. A linter reports rule conformance. A schema validator reports structural validity. All can be green while a product claim is false. Each result says only what that tool measured.

The quieter failure is orphaned knowledge. Someone can answer the relevant question and does so once, but no maintained path returns the page for review. The page remains in CI while the decisive review disappears.

A green build can coexist with either failure. One assigns broad meaning to a narrow result. The other fails to ask the right person or check again.

Swanson calls maintenance in response to a changed environment adaptive maintenance.[^swanson-1976] Orphaned knowledge is an adaptive-maintenance failure: the means to answer exists, but no standing process invokes it after change.

## When docs become machine input

Automated readers make stale guidance travel faster. When a retrieval system, coding agent, or support workflow uses an orphaned page as source material, the same claim can appear in repeated answers or edits. A coherent page can produce working but outdated guidance.

LLMs do not create the maintenance gap. They can increase its reach when a workflow selects a stale page and gives it authority. The source still needs an owner and a trigger.

## What to do

Start with the material claims on a page. For "`GET /foo?mode=summary` returns HTTP `200` in the supported release environment," a contract test can supply current evidence. Run it when the handler or contract changes and on a schedule, and assign responsibility for maintaining the test and acting on its result.

Guidance needs a broader mapping. Give each page or feature a responsible maintainer and connect it to the product area it describes. A mapping to existing dependencies can miss a newly introduced alternative, so the trigger must also cover the product capability or release area. A scheduled review provides a backstop for changes that no existing dependency can anticipate. Changes to source, schema, release state, deprecation status, or team ownership can then create a review task.

This routing creates maintenance and triage work. Use claim-level automation for material assertions a machine can check; page- or feature-level ownership can carry the rest. Event-driven triggers should fire only for changes that can plausibly affect the guidance.

Run the two questions on each material page or claim. A missing first answer is a knowledge gap. A missing second answer is an ownership gap. The end-to-end argument shows where an answer can be found; maintenance gives it a return path. Knowledge becomes orphaned when the system could answer a claim but has no way to ask again.

## Notes

[^saltzer-1984]: Saltzer, J.H., Reed, D.P., and Clark, D.D. "End-to-End Arguments in System Design." *ACM Transactions on Computer Systems* 2, no. 4 (November 1984): 277–288. The knowledge condition and performance-enhancement qualification appear on p. 278. <https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf>

[^lehman-1980]: Lehman, M.M. "Programs, Life Cycles, and Laws of Software Evolution." *Proceedings of the IEEE* 68, no. 9 (September 1980): 1060–1076. The statement that software does not deteriorate spontaneously appears on p. 1061. E-programs mechanize a human or societal activity (p. 1062), and an installed program becomes part of the world it models (p. 1063). Law I applies to a used program that reflects another reality: it undergoes continual change or becomes progressively less useful (p. 1068). <https://users.ece.utexas.edu/~perry/education/SE-Intro/lehman.pdf>

[^parnas-1994]: Parnas, D.L. "Software Aging." Invited plenary talk, *Proceedings of the 16th International Conference on Software Engineering* (ICSE), 1994: 279–287. Parnas distinguishes aging caused by failure to meet changing needs from aging caused by changes themselves (p. 279). The untouched-software and documentation passages appear in §§2.1–2.2, p. 280. <https://www.eecs.yorku.ca/course_archive/2009-10/W/6431/Parnas.pdf>

[^swanson-1976]: Swanson, E.B. "The Dimensions of Maintenance." *Proceedings of the 2nd International Conference on Software Engineering* (ICSE '76), 1976: 492–497. Corrective maintenance is defined on p. 492; adaptive and perfective maintenance, with the summary table, appear on p. 493. <https://dl.acm.org/doi/10.5555/800253.807723>
