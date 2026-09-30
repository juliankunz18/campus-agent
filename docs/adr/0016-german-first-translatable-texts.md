# 16. German first, translatable texts

Date: 2026-09-30 · Status: Accepted

## Context

Members of the first groups write in German, but partner groups may prefer English.
Tool descriptions steer the model and must match the language of the requests.

## Decision

* Code, comments and docstrings are English.
* User-visible texts - tool descriptions and parameter texts, prompt fragments, card
  texts, error messages - live in `locales/<lang>/messages.yaml` of each package.
  German is the default and fallback; English is maintained from the start.
* Each tool description says in one sentence when the tool fits and when it does not.
* The module loader refuses to start if a required text is missing in any supported
  language.

## Consequences

* Adding a language means adding locale files, not changing code.
* Administrative CLI output is English.
