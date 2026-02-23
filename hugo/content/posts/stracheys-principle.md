---
title: "Strachey's Principle: The Discipline That Makes Abstraction Work"
date: 2026-02-23
draft: false
tags: ["history", "computing", "llm", "programming"]
---

In 1965, Christopher Strachey changed his mind about machine code.

He was building the General Purpose Macrogenerator — the GPM — at Cambridge to help write a compiler for the Combined Programming Language (a C precursor). The original plan was simple: mix machine code with macro calls where convenient. The GPM was designed to make this possible.

He ended up abandoning the mix entirely. For the CPL compiler, all machine code would be incorporated as macro calls — even sections called only once, where defining a macro added no economy at all. It had started as a way to save effort. It became a principle.

Sixty years later, programmers and writers are asking the same questions about LLMs that Strachey's contemporaries were asking about macro systems. Whether the tools are legitimate. Whether work done through them counts.

## Wheeler's subroutine

The groundwork comes thirteen years earlier. In 1952, David Wheeler presented a short paper at the ACM national meeting: "The Use of Sub-Routines in Programmes."[^1] Wheeler had been part of the EDSAC team at Cambridge — the group that built the first stored-program computer to run a practical program.

His paper introduces the library subroutine as a unit of abstraction. A subroutine is self-contained, reusable, testable in isolation. You call it; control returns to the point after the call. From the outside it behaves like a single instruction, even though it may be dozens. Wheeler's summary: "All complexities should — if possible — be buried out of sight."

## The asymmetry problem

By the early 1960s, macro-assemblers were standard. You define a macro; the assembler expands it into an instruction sequence before assembly. It extends the instruction set without modifying the hardware.

Strachey identified a structural problem with all of them. A conventional macro takes text as parameters — register names, addresses, literal values, arbitrary strings — and produces *complete instructions* as output. The *domain* (what a function accepts as input) and *range* (what it produces as output) don't overlap — in Strachey's terms: "the domain and range of these macro-functions do not overlap."[^2] This limits composition. You cannot build complex behavior by nesting simpler behaviors, because the types don't match.

GPM eliminates this by making everything a character stream. Input is a stream of characters. Output is a stream of characters. A macro call is a pattern in the stream; its expansion is substituted back into the stream. That re-entry is the key step: if the expansion contains another macro call, that call gets expanded too. The system processes its own results. Because domain and range are now the same type, a macro call can appear anywhere a string can appear — as a parameter to another macro call, in the name position of a macro call, inside a macro's own definition. Recursion, conditionals, and higher-order behavior follow directly from the unification. Strachey notes they "appeared in the wash."

This is also why the all-macros discipline was a structural requirement, not a preference. Allow raw machine code anywhere in the stream alongside macro calls and you have introduced a second type: patterns to be expanded, and instructions to be left alone. GPM would need rules to tell them apart. The uniformity breaks down, and with it the recursive model. The decision Strachey arrived at — no machine code in the source, only macro calls, even where defining a macro added no economy — was not aesthetic. It was the condition the system required.

The CPL compiler was written entirely in macro calls; the programmer never touched opcodes. Strachey noted the consequence: "even very experienced programmers indeed tend to spend hours simulating its action when one of their macro definitions goes wrong." Power and opacity arrived together.

## The pattern

Every major abstraction layer in computing has produced the same debate. Is this real programming? Do you understand what the machine is actually doing?

Subroutines raised it. Macro systems raised it. FORTRAN raised it — John Backus's team spent years arguing that compiled code could match hand-written machine code and therefore be trusted. High-level languages raised it. Each time, the layer was legitimized. Each time, the locus of required skill shifted upward.

The machine kept receding. The question kept returning.

## What is different about LLMs

The question is back. Whether LLM-assisted code is real programming. Whether text written with LLM help is real writing.

The legitimacy debate will resolve itself — not because history mandates it, but because using the best available tool and understanding its properties is good engineering. The interesting question is not whether the layer counts. It is what the layer actually is.

Every previous abstraction layer was deterministic and traceable. A macro expansion has a defined structure — given a name and the current state, you can compute the result by hand. A compiler's transformation of source to object code is, in principle, auditable. The failure modes are structural — unmatched brackets, undefined names — and they are reported precisely.

LLMs are not like this. The binding between a prompt and its output is not a defined rule you can look up. It is distributed across a weight matrix — a large table of numerical values produced by training on text you did not write and cannot inspect. The output is not deterministic. The failure modes are not structural — they are probabilistic. The model can fail silently, plausibly, confidently. There is no `Find` routine you can call to check the current state.

This is not an argument against the layer. It is a description of the layer's properties. Strachey never stated it as a principle — but one can be distilled from what he built and decided: the power of an abstraction layer comes from committing to it entirely. Partial adoption breaks the model.

Strachey was not alone in finding it. Dijkstra hit the same constraint with structured programming: full commitment to provable control structures was the condition for formal reasoning, and IBM's reduction of it to "abolish goto" lost that property entirely. Kay hit it with OOP — the real innovation was message-passing, not objects, and most languages adopted the lesser idea. Each discovered it independently.

I work this way too. The failure modes are real. The discipline is learning what they are.

The longer question is what that discipline evolves into. Strachey's commitment became infrastructure we now take for granted. The LLM equivalent is being designed now: verification practices, workflow conventions, the points where human judgment belongs.

That remains the right question.

---

[^1]: Wheeler, D.J. (1952). "The Use of Sub-Routines in Programmes." *Proceedings of the ACM national meeting*, Pittsburgh, pp. 235–236.

[^2]: Strachey, C. (1965). "A General Purpose Macrogenerator." *The Computer Journal*, 8(3), pp. 225–241.
