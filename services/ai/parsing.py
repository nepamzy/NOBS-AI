"""Shared handling for the AI's structured replies.

`client.messages.parse()` hands back `parsed_output = None` when the reply could
not be read as the requested structure — most often because it was CUT OFF at
the output-token limit, or because the model declined. Code that went straight
to `parsed.title` then died with "'NoneType' object has no attribute 'title'",
which says nothing about the real cause (and the failed call was still billed).
This turns that into an error that says what actually happened.
"""


class ModelOutputError(RuntimeError):
    """The AI answered, but not with something usable. Retrying the identical
    request is pointless (and bills again), so the auto-retry skips it."""


def parsed_or_raise(response, what: str):
    parsed = getattr(response, "parsed_output", None)
    if parsed is not None:
        return parsed

    reason = getattr(response, "stop_reason", None)
    if reason == "max_tokens":
        raise ModelOutputError(
            f"The AI's reply for {what} was cut off before it finished (it hit the output "
            "limit), so it could not be read. The request was too big for one reply."
        )
    if reason == "refusal":
        raise ModelOutputError(
            f"The AI declined to write {what}. Try rewording the topic."
        )
    raise ModelOutputError(
        f"The AI's reply for {what} could not be read as the expected format "
        f"(stop reason: {reason or 'unknown'})."
    )
