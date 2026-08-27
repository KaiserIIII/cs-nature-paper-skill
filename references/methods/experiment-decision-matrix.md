# Claim-driven experiment decision matrix

Each proposed experiment gets one row:

| Field | Required content |
|---|---|
| Claim | claim ID and exact bounded wording |
| Threat | alternative explanation or validity threat |
| Design | units, treatment/comparison, outcome, estimand, dependence |
| Prediction | what the mechanism predicts |
| Decision change | what positive, negative, or null result changes |
| Evidence label | discovery, pilot, formal, post-hoc, replication, reproduction |
| Cost | compute, time, money, access, ethics and license |
| Priority | decision value and feasibility, not prestige |
| Provenance | inputs, command, commit, config, environment, hash |

Delete an experiment when no outcome would change the paper. If the author asks
for extra experiments for venue signaling, preserve the request but state that
it does not add inferential evidence.
