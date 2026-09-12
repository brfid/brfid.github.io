---
title: "Doc rot and the end-to-end argument"
slug: "doc-rot-e2e"
aliases: ["/posts/doc-rot-maintenance-gap/"]
date: 2026-07-11
draft: false
description: "End-to-end reasoning helps identify the evidence a documentation check needs. Keeping guidance useful also requires review as the product changes."
tags: ["documentation", "docs-as-code", "software-maintenance", "testing"]
---

## Introduction

I was thinking about how documentation pipelines can be, and ought to be, organized. I ended up engaging a lot with the *end to end argument*, the *e2e*. I found it useful for reasoning about where verification belongs and what information it needs.

The end to end argument is a reasoned approach to placing functions in certain kinds of systems. It shows up under very specific technical conditions.[^e2e-conditions] Most famously for networking and software-based cohorts, it shows up at MIT about a half-century ago as an argument about networked computer systems.

We can use the e2e argument to locate the functions that verify documents to keep them updated amidst a vast array of potential breaking events. Keeping documents updated with realistically finite resources requires an efficiency that the e2e can help us get.

Technical documentation ages with time, inescapably, in a way that dimly recalls our own bodies. Except that tech docs age even when maintained systems keep them *exactly the same* over swaths of human-scale time. The world changes around technical documentation. The software gets revisions and breaking changes, and so does all the other software that the software works with. The reason for the software to exist will change, or at the very least drift. Eventually the rules of compliance, procurement, engagement are going to change on you.

There's a *lot* you can test against mechanically, but the category of things you can't test for is literally *everything else that can happen*.

## Summary

1. **Place verification where the required evidence is available.** Saltzer, Reed, and Clark's file-transfer argument supplies the principle; the hypothetical API omission applies it to the published instructions and prerequisites. A shared pipeline can perform the check if it has the necessary information.

2. **Renew evidence within its stated scope.** The maintenance grid separates a check's relevance from its recurrence. Repeated execution remains useful only while the check matches the page and supported conditions; an HTTP status check still leaves the response content unverified.

3. **Revisit the reasons for recommending a procedure.** The hypothetical new integration changes the available alternatives while the old procedure still works. Lehman and Parnas explain the pressure from changing circumstances and expectations. Such advice has no fixed original against which to check it.

4. **Match the maintenance commitment to available capacity.** Tests, change triggers, and periodic review need someone with information, time, and authority to respond. Priorities follow the consequences of stale guidance; narrowing or retiring claims reduces work the team cannot sustain.

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

[^e2e-conditions]: In writing this essay, I wanted to understand the particular technical systems and problems that led people to end-to-end reasoning, and what survives when we apply that reasoning elsewhere. Similar arrangements can arise from quite different concerns about correctness, secrecy, and responsibility.

    Saltzer, Reed, and Clark formalized the argument in 1981 and revised it in 1984. Its condition is that complete correctness requires knowledge and help available only at the application endpoints. The communication subsystem cannot independently complete that function, although a partial implementation can improve performance. Their file-transfer example requires checking the file stored at the destination because packet checks leave host and storage failures uncovered. Their ARPANET example distinguishes delivery to a Host from confirmation that its application acted on the message. They identify MIT’s CTSS command acknowledgment as an early example they themselves noticed. These are identifiable systems behind the reasoning. See J. H. Saltzer, D. P. Reed, and D. D. Clark, “[End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf),” *ACM Transactions on Computer Systems* 2, no. 4 (1984): 277–288, especially the sections on file transfer, performance, delivery guarantees, and history; the linked author copy has its own pagination.

    Ashby supplies an epistemic analogue. His law of requisite variety constrains how much variation in outcomes a regulator can eliminate with its available responses. Effective regulation needs sufficient distinctions and responses to counter the relevant disturbances; this is more precise than saying that a regulator must somehow reproduce the entire complexity of whatever it regulates. The analogy concerns the information and response capacity needed to accomplish a task. The theorem does not itself locate a correctness function at application endpoints or supply Saltzer, Reed, and Clark’s argument about redundant mechanisms and performance. See W. Ross Ashby, [*An Introduction to Cybernetics*](https://pespmc1.vub.ac.be/books/IntroCyb.pdf) (Chapman & Hall, 1956), ch. 11, §§11/5–11/7, pp. 204–207.

    Chappe’s semaphore illustrates operator ignorance maintained as a security property. Lakanal defended republishing an account of the machinery on the ground that the Committee of Public Safety could communicate with its representatives at Lille without the operators understanding the messages. Operating the apparatus and interpreting its traffic were deliberately separated. His argument concerns whom the state must trust with meaning, rather than an inherent inability of intermediate machinery or its operators to perform a computation. The motion establishes that security rationale; it does not itself describe the precise distribution of codebooks. See Joseph Lakanal, [motion concerning his report on the Chappe telegraph](https://www.persee.fr/doc/arcpa_0000-0000_1987_num_95_1_22392_t1_0442_0000_1), 8 fructidor an II (25 August 1794), *Archives parlementaires*, first series, vol. 95 (1987), p. 442.

    Electrical telegraphy accumulated arrangements for hop-by-hop custody, content opacity, mechanized retransmission, and legal responsibility. Their combination varied between services and periods. Operators could read ordinary messages; commercial codebooks could obscure their meaning while leaving transmitted symbols available for checking. Even codebook use did not necessarily confine interpretation to the original correspondents: some services decoded messages at an intermediate office and forwarded the plaintext. Steven M. Bellovin discusses these distinctions retrospectively in “[Compression, Correction, Confidentiality, and Comprehension: A Modern Look at Telegraph Codebooks](https://www.cs.columbia.edu/~smb/papers/codebooks.pdf),” author-posted draft of the 2025 *Cryptologia* article, especially §§4 and 6, pp. 12–13 and 29–31; [publication DOI](https://doi.org/10.1080/01611194.2025.2457084).

    The technical custody arrangement is particularly clear in a 1944 Army tape-relay procedure. An intermediate station acknowledges the originating station’s message, then forwards the recorded tape under a new call and preamble and receives a separate acknowledgment from the next station. Mechanization preserves the message body through retransmission while operators manage its routing and receipt. Those acknowledgments concern station-to-station transfer, without establishing that the ultimate addressee understood or acted on the message. See U.S. War Department, [*Teletypewriter Switching and Relay Procedure*](https://digital.library.unt.edu/ark:/67531/metadc9813/), FM 24-14, 19 September 1944, §III, paragraphs 6–8, pp. 21–23.

    Legal responsibility followed its own reasoning. In *Primrose*, the Supreme Court upheld a limitation of recovery to the transmission charge for an unrepeated message under the contract before it; repetition meant sending the text back to the originating office for comparison, at an additional half-rate charge. The Court also distinguished telegraph companies from common carriers of goods and their liabilities. This was an allocation of contractual risk, including the consequences of an undisclosed business transaction, rather than a finding that the carrier could not check transmitted text. See [*Primrose v. Western Union Telegraph Co.*](https://tile.loc.gov/storage-services/service/ll/usrep/usrep154/usrep154001/usrep154001.pdf), 154 U.S. 1 (1894), especially the syllabus and pp. 14–16. Together, these sources document an accumulated regime of transmission and responsibility, not a stated end-to-end systems-design principle.

    BBN’s 1968 IMP proposal makes an organizational and governance argument grounded in technical circumstances. Hosts changed frequently, handled storage and timing differently, could endanger network operation through control of IMP programs, and would be expensive for the network contractor to master individually. BBN therefore proposed initially separating IMP operation from Hosts and Host programmers. It recommended restricting Host programmers “legislatively,” without special technical barriers, and explicitly contemplated later authorized participation by programmers who acquired the necessary expertise. The boundary managed reliability, expertise, and authority; it was not an assertion of permanent technical incapacity. See Bolt Beranek and Newman Inc., [*Proposal: Interface Message Processors for the ARPA Computer Network*](https://www.walden-family.com/bbn/arpanet-prop-ocr.pdf), Proposal No. IMP P69-IST-5, 6 September 1968, pp. II-3–II-7 (PDF pp. 15–19).

    The ownership arguments in modern DevOps, SRE, and platform engineering are often closer to BBN’s question about who should control and maintain a system. Their answers differ. Skelton and Pais assign each subsystem an owning team and constrain responsibilities by the team’s cognitive capacity. The *SRE Workbook* describes default developer ownership and shared responsibility when SRE participates. Both concern the organization of expertise, authority, and continuing care; neither arrangement alone establishes that correctness requires information confined to application endpoints. See Matthew Skelton and Manuel Pais, *Team Topologies: Organizing Business and Technology Teams for Fast Flow* (IT Revolution, 2019), ch. 3, especially pp. 36–41, checked in the publisher excerpt archived with this essay’s research; and Google, “[How SRE Relates to DevOps](https://sre.google/workbook/how-sre-relates/),” *The Site Reliability Workbook* (2018), especially “Share Ownership with Developers.”

    A closer epistemic case appears when verification requires evidence from the deployed application. Alex Perry and Max Luebbe explain that a production probe can exercise a combination of frontend, backend, and independently released components that earlier tests never assembled. A passing test against substitutes cannot establish that this actual combination works. That supports an end-to-end argument for a specified claim whose necessary runtime evidence remains outside the earlier test’s reach; it does not make a production probe a complete proof of service correctness. See “[Testing for Reliability](https://sre.google/sre-book/testing-reliability/),” *Site Reliability Engineering* (2016), ch. 17, especially “Configuration test” and “Production Probes.” Cindy Sridharan’s “[Testing in Production, the safe way](https://copyconstruct.medium.com/testing-in-production-the-safe-way-18ca102d0ef1)” (March 2018) and Charity Majors’s “[I test in prod](https://increment.com/testing/i-test-in-production/)” (*Increment*, 2019) similarly explain why actual workloads, configurations, and interactions supply evidence absent from earlier tests. Both retain a role for testing before production.

    Hermetic builds show why an information argument need not favor the author’s workstation. Making inputs and tools explicit, and isolating a build from undeclared host state, can make the same computation reproducible on local or remote machinery. This can remove a dependence on otherwise unavailable information rather than demonstrate that the function belongs at an endpoint. See Bazel, “[Hermeticity](https://bazel.build/versions/9.0.0/basics/hermeticity),” version 9.0.0 documentation.

    Not every thin middle, decentralized design, local check, ownership boundary, “shift left” practice, or endpoint-like topology instantiates the end-to-end argument. It applies when the correctness of a particular function requires information the proposed middle cannot possess or reach. If the necessary evidence can be supplied to a shared pipeline, its position in the middle does not disqualify it. The comparisons with other traditions are retrospective structural analogies; resemblance and chronological succession do not establish historical influence.

[^saltzer-1984]: J. H. Saltzer, D. P. Reed, and D. D. Clark, "[End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf)," *ACM Transactions on Computer Systems* 2, no. 4 (1984): 277–288. See the opening statement of the argument and the sections "End-to-end caretaking," "Performance aspects," and "Identifying the ends."

[^lehman-1980]: M. M. Lehman, "[Programs, Life Cycles, and Laws of Software Evolution](https://users.ece.utexas.edu/~perry/education/SE-Intro/lehman.pdf)," *Proceedings of the IEEE* 68, no. 9 (1980): 1060–1076. See the discussion of E-programs and the first law of software evolution, especially p. 1068. The application to documentation here is mine.

[^parnas-1994]: D. L. Parnas, "[Software Aging](https://www.eecs.yorku.ca/course_archive/2009-10/W/6431/Parnas.pdf)," *Proceedings of the 16th International Conference on Software Engineering* (1994): 279–287. See §§2.1–2.2, p. 280, on changing expectations, modifications, and deferred documentation updates.
