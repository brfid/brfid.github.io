---
title: "When the Name Settles Before the Architecture Does (Gateways and Agents)"
date: 2026-03-03
draft: true
tags: ["internet history", "AI", "language", "architecture", "naming"]
---

## I. The vocabulary is settling

The word "agent" is everywhere in AI right now. Engineers and marketing departments are using it for things that differ by orders of magnitude in autonomy and design intent. A naming decision is being made, mostly by accident, mostly by whoever talks loudest. The engineering community is pushing back — the term "agent washing" has started circulating — but the vocabulary is settling faster than the architecture is.

## II. How a word forecloses a design

When vocabulary settles around a technology before the architecture does, the word tends to answer design questions that should stay open. The questions stop being asked because the word already seems to answer them. The clearest example in networking history is still with us, in name at least.

## III. What gateways were built for

Read the RFCs and IENs in order — the IENs carried experimental internet notes before concepts were mainstream enough to enter the RFC stream — and something interesting happens in the late 1970s. Gateways, the devices that bridged heterogeneous networks for hosts to connect over, slowly disappeared. We kept the name in our protocol names as a kind of echo: Border Gateway Protocol. But gateways faded away just when routers appeared. What happened? My research through the primary sources of early internet design and governance decisions brought me to John Day, a computer scientist who, among other things, contributed to the Open Systems Interconnect (OSI) standard.

John Day's *Patterns in Network Architecture: A Return to Fundamentals* had alerted me to look for this: Day argues that the internet's architecture collapsed layers that should have remained distinct. The primary record shows how that happened — and how the vocabulary change followed, burying the architectural decision under a word that made it seem inevitable.

Early internet devices were called gateways. The word was accurate. A gateway connected heterogeneous networks — networks built by different institutions, running different protocols, with different internal addressing schemes. Translation was its central function. Louis Pouzin, the French computer scientist behind the CYCLADES network and one of the architects of early internetworking, understood the internet's design problem as fundamentally one of heterogeneity. Network interconnection, he wrote in 1973, "will have to work around peculiar, possibly weird features, embedded in local artwork."[^pouzin] The gateway was the device that did that work.

The vision was of an internet layer that sat atop genuinely diverse local networks — networks that would remain different from each other, with a thin shared layer handling interconnection between them. Gateways were the hinge. They made the heterogeneity workable without eliminating it. All the work on the Transmission Control Protocol (TCP) prior to DARPA engineers splitting out IP either assumed diverse underlying networks or put the question off.

## IV. How the gateway became a router

A series of design decisions — driven largely by requirements from the federal government for a planned military backbone network — pushed toward a universal protocol. The Internet Protocol expanded to handle not just internetwork addressing but local network addressing as well. Once IP was everywhere, translation became unnecessary. The gateway's core function was gone.

The device that remained did one thing: forward packets between networks that already spoke the same language. Engineers called it a router. The word was accurate for what the device now did. But the design space the gateway had represented — the genuinely heterogeneous internet, where local networks could remain architecturally distinct — was now not just unrealized. It was unnamed.

The transition from "gateway" to "router" was "an unnoticed linguistic shift with major technical and institutional significance."[^fidler] Unnoticed is the key word. No one announced that the heterogeneous internet was no longer on the table. (There were announcements of policy that sealed the fate of alternate approaches, but they weren't obvious at the time.) It became unavailable gradually, through accumulated decisions. The vocabulary followed those decisions and settled over them. You cannot easily advocate for a design you have no word for — and once "router" was the word, the design the gateway had represented stopped being part of the conversation.
stream disconnected before completion: Incomplete response returned, reason: content_filter
The vocabulary arrived late. By the time "router" became standard, the major decisions had already been made — DARPA's requirements for a military backbone, the institutional choices that left TCP/IP dominant and OSI sidelined. The word did not shape those outcomes. What it did was seal them. "Router" gave the decisions the appearance of inevitability they had not necessarily earned. Every engineer who came after learned networking in router terms, not because the gateway was considered and rejected, but because the question had stopped being askable.

[^pouzin]: Pouzin, L. (1973). Interconnection of Packet Switching Networks (No. 42). Reseau Cyclades. [^fidler]: Fidler, B. (2019). The Evolution of Internet Routing: Technical Roots of the Network Society. *Internet Histories*. DOI: 10.1080/24701475.2019.1661583

## V. "Agent" is inflating, not narrowing

The gateway case and the agent case move in opposite directions — and that difference is worth naming, because it shows the same structural problem operating through two distinct mechanisms.

The gateway was a rich concept narrowed by a vocabulary change. "Agent" is moving the other way: a precise technical term being stretched to cover a wide range of systems. One case closed off heterogeneity; the other is closing off specificity. In both cases, vocabulary settles before architecture does. In both cases, the settling answers design questions that should stay open.

On one end of the current range: a workflow that calls three APIs in a fixed sequence. On the other: a system that receives a goal, plans a sequence of actions, executes them, observes results, and adapts. Both are currently called agents. The word is doing too much, and in doing too much, it pre-answers the question that most needs to stay open: how much autonomy is appropriate here?

That is a design question. It has different answers depending on the stakes of the decision, the reversibility of the action, the reliability of the system, and the cost of oversight. It is answered differently for a system scheduling calendar invites and a system approving financial transactions. When everything is an agent, the question stops being asked at the design stage. The autonomy is assumed.

The engineering community has already run into this. LangChain, which became the standard framework for building "agents," found in practice that fully autonomous agents were too brittle for production use — prone to looping, to losing track of goals, to accumulating errors across steps. The response was LangGraph, which treats these systems as explicit state machines with defined transitions. The engineering reality pushed back toward structure. The marketing vocabulary did not follow.

The direction of the movement matters. When a concept narrows, you lose the ability to propose alternatives — there is no longer a word for what you might want to build. When a concept inflates, you lose the ability to make distinctions — the differences that should drive design decisions stop being nameable. The foreclosure works differently. It ends the same way.

## VI. What to ask when a word is settling

The gateway-to-router shift did not happen because anyone decided the heterogeneous internet was a bad idea. It happened through accumulated decisions made for other reasons, and the vocabulary change was the last step — the point at which the foreclosure became stable. By the time the word changed, the window for a different outcome had already closed.

With "agent," the accumulated decisions are still being made. That means there is still a design conversation to have. But having it requires vocabulary that can hold the distinction between a tool, an assistant, and a genuine agent — between a system that executes human-directed steps, one that collaborates within human-set parameters, and one that plans and acts with meaningful autonomy.

When a word is settling in around a technology, it is worth asking: what did the previous vocabulary make possible that this word does not? What questions does the new word answer before they are asked? The gateway made heterogeneity thinkable. The router made it unnecessary to think about. What does "agent" make unnecessary to think about?
