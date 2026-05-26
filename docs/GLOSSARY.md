# Glossary

*For readers — auditors, DPOs, downstream pipeline authors — who want a single source for every abbreviation, term of art, and regulatory acronym used in this project.*

Terms are alphabetized. Each entry expands the abbreviation, gives a one-line gloss, and points to the primary doc that uses it. The [PII vs PHI](#pii-vs-phi) section is called out separately because the distinction governs scope decisions.

## PII vs PHI

These are often conflated. They are not the same.

| Term | Origin | What it covers | Reversible? |
|---|---|---|---|
| **Personal data** | EU GDPR Art. 4(1) | Any information relating to an identified or identifiable natural person. Broader than US "PII" — includes online identifiers, location data, genetic data. | GDPR-defined (Art. 4(5) pseudonymization is reversible by design) |
| **PII — Personally Identifiable Information** | US (NIST SP 800-122) | Information that can be used to identify, contact, or locate a person — name, SSN, email, phone, address, biometric. | Depends on implementation |
| **PHI — Protected Health Information** | US HIPAA 45 CFR 164.514 | The **18 HIPAA identifier categories** when held by a covered entity *and* tied to health information: names, dates (except year), phone, fax, email, SSN, **medical record numbers**, **health plan beneficiary numbers**, **account numbers**, certificate/license numbers, vehicle identifiers, **device identifiers**, URLs, IPs, biometric identifiers, **full-face photos**, "any other unique identifying number". | Depends on implementation |

Background reading: <https://www.hipaajournal.com/phi-vs-pii/> · <https://gdprlocal.com/pii-vs-phi/>

### What this tool detects

- **Targets the GDPR notion of "personal data" and the PII overlap with PHI** — names, SSN, phone, email, IBAN, credit card, and (via optional NER) organizations and locations.
- **Does not target PHI-only identifiers** — medical record numbers (MRN), health plan IDs, device identifiers, biometric identifiers, full-face photos, license/certificate numbers, account numbers. These are out of scope at v0.1.
- **For HIPAA Safe Harbor de-identification of clinical notes**, prefer [philter](https://github.com/BCHSI/philter-ucsf) or Microsoft Presidio's medical recognizers — see [Related projects](landscape/de-identification.md). A PHI-detector extension is not currently on the [roadmap](roadmap.md); track interest at [github.com/qte77/pseudonymize-text/issues](https://github.com/qte77/pseudonymize-text/issues).

## Abbreviations

| Term | Expansion | Gloss | Primary use |
|---|---|---|---|
| **ADR** | Architecture Decision Record | Markdown record of an architecturally significant decision; [MADR](https://adr.github.io/madr/) format. | [docs/decisions/](decisions/) |
| **AEPD** | Agencia Española de Protección de Datos | Spanish data-protection authority; co-authored the EDPS hash-paper cited in our compliance posture. | [COMPLIANCE.md](COMPLIANCE.md) |
| **ARC** | Authenticated Received Chain | Email-authentication header; stripped on rewrite because pseudonymization invalidates the signature. | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **CC** | Credit Card | A payment-card number; validated via Luhn (mod-10). | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **CLI** | Command-Line Interface | The `pseudonymize` executable; `detect` and `apply` subcommands. | [USAGE.md](USAGE.md) |
| **CSPRNG** | Cryptographically Secure Pseudo-Random Number Generator | Source of HMAC key bytes; `openssl rand` is acceptable. | [SECURITY.md](SECURITY.md) |
| **DKIM** | DomainKeys Identified Mail | Email-signing header; stripped on rewrite. | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **DPO** | Data Protection Officer | GDPR Art. 37 role; primary audience of [COMPLIANCE.md](COMPLIANCE.md). | [COMPLIANCE.md](COMPLIANCE.md) |
| **EDPB** | European Data Protection Board | EU body issuing binding guidance under GDPR; published the 01/2025 pseudonymisation guidelines we map to. | [COMPLIANCE.md](COMPLIANCE.md) |
| **EDPS** | European Data Protection Supervisor | EU institution overseeing GDPR compliance of EU bodies; co-author of the hash-paper. | [COMPLIANCE.md](COMPLIANCE.md) |
| **ENISA** | European Union Agency for Cybersecurity | Publishes technical guidance on pseudonymization techniques. | [COMPLIANCE.md](COMPLIANCE.md) |
| **FIPS** | Federal Information Processing Standards | US federal cryptographic standards (FIPS 180-4 specifies SHA-256). | [COMPLIANCE.md](COMPLIANCE.md) |
| **GDPR** | General Data Protection Regulation | EU Regulation 2016/679 on the processing of personal data. | [COMPLIANCE.md](COMPLIANCE.md) |
| **GLiNER** | Generalist Lightweight model for Named Entity Recognition | NER backend planned for 2.0.0. | [roadmap.md](roadmap.md) |
| **HIPAA** | Health Insurance Portability and Accountability Act | US law (1996) governing PHI; Safe Harbor (45 CFR 164.514(b)(2)) is the rule philter targets. | [PII vs PHI](#pii-vs-phi) |
| **HMAC** | Hash-based Message Authentication Code | Keyed pseudo-random function (RFC 2104); we use HMAC-SHA256 for token derivation. | [HASHING.md](HASHING.md) |
| **IBAN** | International Bank Account Number | ISO 13616; validated via mod-97. | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **IETF** | Internet Engineering Task Force | Publisher of RFCs (e.g. RFC 2104 for HMAC). | [COMPLIANCE.md](COMPLIANCE.md) |
| **JSONL** | JSON Lines | Newline-delimited JSON; the format of `pseudonymize-report.jsonl` and `--plan` input. | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **KDF** | Key Derivation Function | Function that derives keys from a secret; we deliberately do **not** use one (HMAC's PRF property suffices). | [SECURITY.md](SECURITY.md) |
| **LLM** | Large Language Model | Downstream consumer of pseudonymized output; security caveats in [SECURITY.md § LLM and downstream consumption](SECURITY.md#llm-and-downstream-consumption). | [SECURITY.md](SECURITY.md) |
| **MAC** | Message Authentication Code | Generic term for a keyed integrity primitive; HMAC is the construction we use. | [SECURITY.md](SECURITY.md) |
| **MADR** | Markdown Architecture Decision Record | The ADR template format used in [docs/decisions/](decisions/). | [docs/decisions/](decisions/) |
| **MIME** | Multipurpose Internet Mail Extensions | Email content-type system; `.eml`/`.mbox` parts are dispatched per MIME type. | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **MRN** | Medical Record Number | PHI identifier category; **not detected** by this tool. | [PII vs PHI](#pii-vs-phi) |
| **NER** | Named Entity Recognition | spaCy-based detection of PERSON/ORG/LOC; optional via `[ner]` extra. | [ner-install.md](ner-install.md) |
| **NFKC** | Normalization Form Compatibility Composition | Unicode normalization applied to `--ignore` entries to prevent zero-width-character bypass. | [SECURITY.md](SECURITY.md) |
| **NIST** | National Institute of Standards and Technology | US standards body; SP 800-188 (de-identification), SP 800-107 (hash truncation), FIPS 180-4 (SHA-256). | [COMPLIANCE.md](COMPLIANCE.md) |
| **NPI** | National Provider Identifier | US healthcare-provider ID; PHI-only, **not detected**. | [PII vs PHI](#pii-vs-phi) |
| **PBKDF2** | Password-Based Key Derivation Function 2 | Password-stretching KDF (RFC 8018); deliberately **not** used (our input is a key, not a password). | [SECURITY.md](SECURITY.md) |
| **PHI** | Protected Health Information | See [PII vs PHI](#pii-vs-phi). | [PII vs PHI](#pii-vs-phi) |
| **PII** | Personally Identifiable Information | See [PII vs PHI](#pii-vs-phi). | [PII vs PHI](#pii-vs-phi) |
| **PRF** | Pseudo-Random Function | Cryptographic primitive HMAC realizes; the property that makes HMAC suitable here without a KDF. | [SECURITY.md](SECURITY.md) |
| **RAG** | Retrieval-Augmented Generation | LLM pattern; pseudonymized corpora are a common RAG input. | [SECURITY.md](SECURITY.md) |
| **ReDoS** | Regular-Expression Denial of Service | Attack via catastrophic regex backtracking; guarded against in `terms.csv` loader. | [SECURITY.md](SECURITY.md) |
| **RFC** | Request for Comments | IETF specification series (e.g. RFC 2104 HMAC, RFC 2047 encoded-words). | [COMPLIANCE.md](COMPLIANCE.md) |
| **SARIF** | Static Analysis Results Interchange Format | Planned alternative report format for 2.0.0. | [roadmap.md](roadmap.md) |
| **SHA-256** | Secure Hash Algorithm 256-bit | FIPS 180-4; the hash inside our HMAC. | [HASHING.md](HASHING.md) |
| **S/MIME** | Secure/Multipurpose Internet Mail Extensions | Encrypted/signed email parts; dropped on rewrite (treated as binary attachments). | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **SSN** | Social Security Number | US national identifier; detected in `NNN-NN-NNNN` format only. | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **TDD** | Test-Driven Development | Red→Green per-behaviour cycle followed in this project. | [ARCHITECTURE.md § TDD per-behaviour discipline](ARCHITECTURE.md#tdd-per-behaviour-discipline) |
| **TSV** | Tab-Separated Values | Alternative report format. | [USAGE.md](USAGE.md) |
| **UTF-8** | Unicode Transformation Format, 8-bit | Required encoding for all read/written text files. | [ARCHITECTURE.md](ARCHITECTURE.md) |

## See also

- [COMPLIANCE.md](COMPLIANCE.md) — regulatory mapping and references.
- [SECURITY.md](SECURITY.md) — threat model and operational rules.
- [landscape/de-identification.md](landscape/de-identification.md) — alternative tools (Presidio, philter) and when to pick them.
