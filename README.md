# Supply Chain Copilot

NL-to-QuerySpec conversational analytics over a synthetic GCC distributor dataset
(Mawarid Distribution, fictional). A model fills a typed spec; deterministic code
compiles it to SQL. This repo is currently **pre-build, eval-first**: the frozen
spec grammar ([docs/SPEC.md](docs/SPEC.md)), the 80-entry golden set, the
normalizer equivalence pairs, and hand-math fixtures all exist *before* any
implementation they measure. No generator, no tests, no Python yet — the
evaluation bar comes first.
