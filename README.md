# Pindrop

## Vision

Pindrop is a self-hosted, open-source personal knowledge archive — an internet archaeology tool for collecting, preserving, and rediscovering the web content that matters to you. It captures bookmarks, pages, images, notes, and any other content type via a plugin system, enriches them with AI-generated summaries, tags, and semantic search, and surfaces them through a fluid, visual interface.

The core philosophy: your data is yours. Pindrop works without AI, without a subscription, and without an internet connection. AI is an enhancement layer, not a dependency. Every artifact you save is exportable, readable, and usable outside the application.

---

## Design Principles

**Modularity over monolith.** Every content type, auth strategy, ingestion source, and AI provider is a plugin. The core system is type-agnostic. New capabilities are added without touching existing code.

**Data sovereignty.** All content is stored locally. Export is a first-class feature, not an afterthought. Open formats wherever possible.

**Graceful degradation.** The full experience is available with AI. A complete and useful experience is available without it. Users choose their level of complexity.

**Zero new habits required.** Ingestion meets users where they already are — email, browser, Reddit saves, Twitter bookmarks. The system comes to the user.

**Built for others.** Opinionated enough to have a clear identity, configurable enough to serve different users and deployment contexts.

## Pindrop Spec

[Pindrop Spec sheet](../blob/main/docs/pindrop-spec.md)
