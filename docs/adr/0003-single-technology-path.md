# 3. One technology path: Teams, SharePoint, Azure OpenAI

Date: 2026-09-30 · Status: Accepted

## Context

Student groups have little time for operations. Supporting several chat platforms,
data stores or model providers would multiply setup, documentation and support effort.
Non-profit groups with their own Microsoft 365 tenant get licenses and Azure credit
through Microsoft for Nonprofits.

## Decision

campus-agent supports exactly one path in v1: Microsoft Teams as channel, SharePoint
(via Microsoft Graph) for business data, Entra ID for roles and Azure OpenAI as model,
all in the group's own tenant and Azure subscription. Other channels are not planned.

## Consequences

* Groups that only exist inside their university's tenant need their own tenant first.
* Each group runs its own instance and remains the owner of its data.
* Everything else can come later as a module or adapter behind the existing ports.
