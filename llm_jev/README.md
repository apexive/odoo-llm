# TypeSafe Jev LLM Integration

This addon adds the TypeSafe Jev decision API to the LLM framework.
It evaluates named predicates against structured JSON state.
It returns one finite probability from zero through one for each predicate.

## Installation and configuration

Install `llm_jev` with the stock `llm` addon and the Python `requests` package.
The addon creates a TypeSafe publisher, a provider, and a default decision model.
The default model name is `jev-1.14.0`.
The provider belongs to the company that installs the addon.
Configure the provider API key as an LLM Manager.
The addon preserves provider and model settings during upgrades.

The default API host is `https://api.typesafe.ai`.
The API base can contain the host, `/v1`, or `/v1/systemone`.
Requests use a five-second timeout by default.
Set `timeout` to a finite positive number of seconds when required.
The transport uses `requests` directly.

## Usage

```python
provider = env.ref("llm_jev.llm_provider_jev")
probabilities = provider.decide(
    {"values": [1, 2, 3]},
    {
        "positive": {
            "type": "noul",
            "instructions": "Are all values positive?",
            "criteria": {"true": "All positive", "false": "Otherwise"},
        },
        "empty": "Is the list empty?",
    },
    timeout=5.0,
)
# Example result: {"positive": 0.99, "empty": 0.01}
```

Predicates accept a dictionary or a list of dictionaries with a `name`.
List entries can also use `id` or `key` for the name.
Instructions must contain a non-empty string.
Only the `noul` question type is supported.
Optional `criteria` must contain a dictionary.
The addon rejects duplicate names after it removes surrounding spaces.

The `model` argument accepts an active decision model from this provider.
It also accepts a non-empty model name string for a service model.
Without this argument, the addon selects an active decision model from the provider.
It uses `jev-1.14.0` if no active decision model exists.
There is no model-level `decide` operation.

The addon rejects missing answers, unexpected answer keys, and invalid probabilities.
Boolean values are invalid probabilities.
Chat, streaming, embeddings, content generation, and tool calling raise `UserError`.

## Data handling

The caller must filter personal data before it calls `provider.decide`.
The addon sends the supplied state and predicates to the configured API endpoint.
It does not anonymize or filter those values.
Transport errors omit the API key and the request body.
The caller must also control its own logs and API endpoint settings.

This addon inherits the stock provider access rules.
Those rules allow internal users to read providers across companies.
The stock API key field has no field-level group restriction.
Resolve key access in a separate base-module change before production use.

## Tests

The tests use Odoo `TransactionCase` and mock all HTTP requests.
Run the tests with only the stock framework, `llm`, and this addon available.

```bash
./run_tests.sh llm_jev jev_disposable_test 8179
pre-commit run --files llm_jev/* llm_jev/models/* llm_jev/tests/* llm_jev/data/*
```

The upstream runner expects its documented checkout and Python environment layout.
Use a disposable database and a free HTTP port.
The tests require no live service key.

## Author and license

Author: Lijo Antony.
License: LGPL-3.

See the [TypeSafe documentation](https://docs.typesafe.ai/introduction)
and the [LLM project](https://github.com/apexive/odoo-llm).
