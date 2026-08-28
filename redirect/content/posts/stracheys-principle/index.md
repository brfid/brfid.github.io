---
title: "Strachey's lesson: commit to the workflow"
date: 2026-02-23
substack_url: https://brfid.substack.com/p/stracheys-principle-the-discipline
draft: false
description: "What Strachey's decision to write a compiler through macros suggests about working with LLMs."
tags: ["history", "computing", "llm", "programming"]
---

I’ve been thinking about Christopher Strachey’s work on macros in 1965, and what it suggests about the benefits of LLM workflows.

Strachey developed the General Purpose Macrogenerator (GPM) to help build a compiler for the Combined Programming Language (CPL). GPM let the team mix machine instructions with macro calls, which expanded into instruction sequences. Eventually they decided to put every machine-code section behind a macro, even one they would call only once.[^1]

That's the moment that caught my attention in his 1965 paper:

{{< figure src="strachey-1965-macro-policy.png" alt="Strachey describes how saving repetitive work became a policy of putting every machine-code section behind a macro, even one used only once." caption="From page 229 of Strachey’s 1965 paper. Highlighting in the source copy." >}}

Changing the macro definitions let them choose between compact subroutine calls and faster inline code. They could also add instructions to count how often parts of the program ran, then use those counts to decide where speed mattered.

One example makes the advantage of using macros throughout especially clear. The generator tracked whether the stack’s top value was in the accumulator or memory. Each operation checked that record, inserted a transfer if needed, and updated the record for the next operation. A handwritten instruction that moved the value without updating the record could leave the next macro working from a false assumption.

The bookkeeping depended on every operation keeping it accurate.

## Working with LLMs

I think there’s a reason to take LLM workflows seriously here. In a coding project, the model needs access to the requirements and the reasons behind earlier decisions. Its changes need tests and review. Decisions made during that review need to find their way back into the project’s records. Human contributions need the same treatment.

Putting that together takes effort. An occasional prompt won’t tell you whether the effort is worthwhile; you have to work with the process long enough to judge the quality of the results and the time they cost you.

[^1]: Strachey, C. (1965). [“A general purpose macrogenerator.”](https://doi.org/10.1093/comjnl/8.3.225) *The Computer Journal*, 8(3), pp. 225–241. See §3, pp. 228–230.
