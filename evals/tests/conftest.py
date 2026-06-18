"""Shared pytest fixtures for evals unit tests.

Evals tests must not require Neo4j/ChromaDB to run. Any fixture defined here
should be in-memory only.
"""


class FakeLLM:
    """Scripted async chat double. Each call pops the next response; an
    Exception instance in the script is raised instead of returned."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []  # list of (system_prompt, user_prompt, kwargs)

    async def chat(self, system_prompt, user_prompt, **kwargs):
        self.calls.append((system_prompt, user_prompt, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
