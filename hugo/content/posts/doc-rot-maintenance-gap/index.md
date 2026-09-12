---
title: "Doc rot and the end-to-end argument"
date: 2026-07-11
draft: false
description: "End-to-end reasoning helps identify the evidence a documentation check needs. Keeping guidance useful also requires review as the product changes."
tags: ["documentation", "docs-as-code", "software-maintenance", "testing"]
---

I began reconsidering how documentation pipelines should be organized. The end-to-end principle helped me reason about where functions belong within a pipeline.

Keeping documentation useful requires both evidence for what a page says and a way to reconsider it as the product changes. A successful build can tell us that links resolve and examples run under the test conditions. Assessing the procedure a page recommends may require further information about its instructions, its readers, and the alternatives available to them.

## Verification needs the right information

Saltzer, Reed, and Clark's end-to-end argument concerns the placement of functions in a system. When a function requires knowledge and help from the application at the endpoints, mechanisms inside the communication system can provide only part of it.[^saltzer-1984]

Their file-transfer example explains why the scope of verification matters. Checking packets as they cross a network can catch transmission errors. Errors can also occur while the hosts read, copy, or store the data. The application therefore checks the file stored at the destination against the original, using a checksum, and handles a failed comparison. Network checks remain useful because they can reduce the frequency and cost of repeating the transfer.

For a documented procedure, the relevant claim is that a reader with the stated prerequisites can follow the published steps and obtain the described result. Consider a guide to retrieving a summary through an API. One testable claim is that the documented request, `GET /foo?mode=summary`, returns HTTP `200` in a specified supported version and environment.

A test of that request can miss an error in the instructions if it relies on setup the page does not describe. Suppose shared test code adds a required authorization header, while the published procedure omits it. The test establishes that the complete request succeeds in its environment. A reader following the page sends an incomplete request and cannot obtain the promised result.

Verifying the procedure requires bringing the published instructions, their stated prerequisites, and the product's behavior into the same assessment. A test that follows those instructions can expose the omission. A reviewer can also find it by working through the procedure from the stated starting conditions.

This is a limited application of the end-to-end argument. A documentation pipeline combines tools and judgments that need not form the same hierarchy as a communication system. The comparison helps identify verification that needs knowledge of the whole procedure. That verification could run alongside the linters in the existing pipeline; its adequacy depends on the information it uses and the claim it assesses.

## Testing a procedure over time

Evidence gathered while drafting applies to the conditions in which it was gathered. Once the guide includes the required header and a test follows those instructions, running it again can help detect later changes in the API. The following table separates a check's relevance to the HTTP response claim from whether it recurs after publication.

{{< maintenance-grid >}}

The recurring contract test supplies fresh evidence about the response, provided its inputs still match the page and its environment still represents the supported conditions. Returning HTTP `200` is one part of the guide's promise; the contents of the returned summary need a separate check. The layout and structure checks supply evidence about their own properties, independently of how often they run.

## Reconsidering a recommendation

A working procedure can become a less useful recommendation as the product changes. Suppose the API guide is now complete and its test is reliable. The product later gains a direct integration that reduces the setup needed for the same task. The original procedure continues to work, so its test keeps passing, while the guide continues to present it as the default approach.

The new integration gives us reason to reassess that advice. The choice may depend on which readers can use the integration, what it costs to adopt, and whether it supports their requirements. Successful execution of the original procedure establishes that it remains available. Comparing the alternatives requires evidence suited to that decision.

The file-transfer analogy has a limit here. A transferred file has a fixed original against which to check it. A recommendation depends on the available alternatives and the reader's circumstances, and there may be no single conclusive test. Keeping that judgment current requires a way to revisit both the recommendation and the reasons for it.

Software maintenance research describes a related dependence on changing circumstances. Lehman described how programs that reflect an external reality can become less useful unless they evolve with it.[^lehman-1980] Parnas distinguished aging caused by changing expectations from deterioration introduced through modifications. He also explained how deferred documentation updates make later modifications harder to carry out.[^parnas-1994] Applied to this guide, the maintenance problem includes noticing changes outside the documented procedure that could alter the reasons for recommending it.

## Making review sustainable

Review arrangements need to make relevant changes visible to someone who can act on them. Connecting the guide to a product area or a release review could flag the arrival of the new integration. A trigger tied only to modifications of the original endpoint would miss that change. A periodic review provides another opportunity to notice developments that existing dependencies fail to capture.

The person or team responsible for review needs access to current product information, time to assess the guide, and authority to revise or retire it. A recurring test whose failures wait indefinitely for investigation leaves the maintenance work unfinished.

The consequences of stale guidance can help a team decide where to concentrate this work. For behavior that materially affects a reader's task and can be tested, record the relevant conditions, connect the test to the published instructions, and decide how to respond when its result changes. For recommendations, assigning responsibility at the page or product level may be more practical than tracking every sentence. The frequency of review should reflect both the consequences of stale advice and the time available to examine it.

These arrangements have continuing costs. Tests drift from the instructions they exercise, product mappings become outdated, and review requests compete with other work. Narrowing a claim, stating its version or conditions, or retiring guidance can reduce a maintenance commitment the team can no longer sustain.

For this guide, the commitment has two parts: a recurring test of the documented behavior under stated conditions, and a way to reconsider the recommendation as the product changes. End-to-end reasoning helps identify the information verification needs. The maintenance discussion adds the work required to keep that evidence and judgment current. Publishing the guide makes both part of the team's continuing responsibility.

## Notes

[^saltzer-1984]: J. H. Saltzer, D. P. Reed, and D. D. Clark, "[End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf)," *ACM Transactions on Computer Systems* 2, no. 4 (1984): 277–288. See the opening statement of the argument and the sections "End-to-end caretaking," "Performance aspects," and "Identifying the ends."

[^lehman-1980]: M. M. Lehman, "[Programs, Life Cycles, and Laws of Software Evolution](https://users.ece.utexas.edu/~perry/education/SE-Intro/lehman.pdf)," *Proceedings of the IEEE* 68, no. 9 (1980): 1060–1076. See the discussion of E-programs and the first law of software evolution, especially p. 1068. The application to documentation here is mine.

[^parnas-1994]: D. L. Parnas, "[Software Aging](https://www.eecs.yorku.ca/course_archive/2009-10/W/6431/Parnas.pdf)," *Proceedings of the 16th International Conference on Software Engineering* (1994): 279–287. See §§2.1–2.2, p. 280, on changing expectations, modifications, and deferred documentation updates.
