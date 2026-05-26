---
status: accepted
date: 2026-05-25
---

# Mail-part handling: pseudonymize text/*, drop non-text parts

## Context and Problem Statement

When v0.1.0 adds `.eml` / `.mbox` support, each MIME part needs an explicit
fate. Headers and `text/plain` bodies clearly require pseudonymization.
`text/html` alternates carry the same PII through different markup. Binary
parts (attachments, inline images, S/MIME blobs) cannot be pseudonymized
without per-format parsers, and silently passing them into a documented
**distributable** [`<out_dir>`](../SECURITY.md#artifacts-produced-by-a-run)
would leak the data the tool exists to remove.

## Decision Drivers

* `<out_dir>` is the only "Distributable" artefact per
  [SECURITY.md](../SECURITY.md); nothing PII-bearing may pass through
  unprocessed.
* Per-format binary parsers (PDF, Office, archives) are deferred to 2.0.0 per
  [roadmap.md](../roadmap.md). v0.1.0 must not block on them.
* Output must remain parseable by stdlib `email` and by mail clients.

## Considered Options

* **A. Pseudonymize `text/plain` + `text/html`; drop non-text parts.**
* **B. Pseudonymize `text/plain` only; byte-copy everything else.**
* **C. Pseudonymize `text/plain` + `text/html`; byte-copy non-text parts.**

## Decision Outcome

Chosen: **A — text/\* in, non-text dropped.**

Per message, the formats layer:

1. Decodes and pseudonymizes the headers `From`, `To`, `Cc`, `Bcc`, `Subject`,
   `Reply-To`, and their RFC 2047 encoded variants.
2. Decodes and pseudonymizes every `text/plain` and `text/html` part.
3. **Drops** every other part, replacing it with a `text/plain` stub:
   `[part removed by pseudonymize: <Content-Type>; <N> bytes]`.
4. Strips `DKIM-Signature`, `ARC-Seal`, `ARC-Message-Signature`, and
   `ARC-Authentication-Results` headers (their signatures are invalidated by
   step 1).
5. For `.mbox` inputs, fans out one `.eml` per message to
   `<out_dir>/<basename>/<seq>.eml`. No mbox re-assembly.

### Consequences

* Good — `<out_dir>` remains distributable; no manual review of attachments.
* Good — no binary-format parsers needed; v0.1.0 scope stays bounded.
* Good — drop-stubs make removed parts visible rather than silently missing.
* Bad — recipients lose attachments. **Intended.** Users who need attachments
  must pseudonymize the attachment text separately and re-attach.
* Bad — HTML detection runs against marked-up text; quality depends on the
  detector strategy chosen in
  [#11](https://github.com/qte77/pseudonymize-text/issues/11). This ADR fixes
  *that* HTML is in scope, not *how*.
* Bad — `.mbox` fan-out flattens to one file per message; round-trip mbox
  re-assembly is the user's responsibility.

### Confirmation

E2E fixture in
[#14](https://github.com/qte77/pseudonymize-text/issues/14): a multipart
`.eml` containing `text/plain` + `text/html` + a PDF attachment. Asserts (a)
both text parts carry tokens, (b) the PDF part is replaced by the stub, (c)
output parses with `email.message_from_file` under `policy.default`, (d) no
`DKIM-Signature` header remains.

## More Information

* [ARCHITECTURE.md §Mail-format support](../ARCHITECTURE.md#mail-format-support)
  — current-state reference.
* [SECURITY.md §Artifacts produced by a run](../SECURITY.md#artifacts-produced-by-a-run)
  — `<out_dir>` sensitivity classification.
