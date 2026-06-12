---
title: AI / LLM bot policy
description: Which AI training and search crawlers are allowed to index the django-components documentation, and why.
---

# AI / LLM bot policy

We allow the major AI training and search crawlers to index this documentation:

- GPTBot (OpenAI)
- ClaudeBot (Anthropic)
- anthropic-ai (Anthropic - legacy)
- Google-Extended (Google AI training)
- PerplexityBot (Perplexity search)
- CCBot (Common Crawl - feeds many models)

Reason: this is a community-maintained library, and the more discoverable our docs are
to AI-based search and AI-based authoring tools, the easier it is for users to find us
and write components correctly the first time.

If you maintain a downstream tool that relies on django-components and want to verify
your bot is allowed, see [robots.txt](/robots.txt). We update the allow-list on a
rolling basis as new well-behaved crawlers appear.

To request that a specific bot be added or removed,
[file an issue](https://github.com/django-components/django-components/issues).
