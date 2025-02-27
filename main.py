"""
Execution entrypoint for the github-slack-bot project.

Sets up a `bottle` server with three endpoints: "/", "/github/events" and "/slack/commands".

"/" is used for testing and status checks.

"/github/events" is provided to GitHub Webhooks to POST event info at.
Triggers `manage_github_events` which uses `GitHubPayloadParser.parse` and `SlackBot.inform`.

"/slack/commands" is provided to Slack to POST slash command info at.
Triggers `manage_slack_commands` which uses `SlackBot.run`.
"""

import os
from pathlib import Path
from typing import Any

import sentry_sdk
from bottle import get, post, request, run
from dotenv import load_dotenv
from sentry_sdk.integrations.bottle import BottleIntegration

from bot.github.github_parsers import GitHubPayloadParser
from bot.models.github.event import GitHubEvent
from bot.slack import SlackBot
from bot.utils.log import Logger


@get("/")
def test_get() -> str:
    """
    First test endpoint.
    :return: Plaintext confirming server status.
    """
    return "This server is running!"


@post("/")
def test_post() -> str:
    """
    Second test endpoint.
    :return: Status confirmation plaintext containing name supplied in request body.
    """
    try:
        name: str = request.json["name"]
    except KeyError:
        name: str = "(empty JSON)"
    except TypeError:
        name: str = "(invalid JSON)"
    return (f"This server is working, and to prove it to you, "
            f"I'll guess your name!\nYour name is... {name}!")


@post("/github/events")
def manage_github_events():
    """
    Uses `GitHubPayloadParser` to parse and cast the payload into a `GitHubEvent`.
    Then uses an instance of `SlackBot` to send appropriate messages to appropriate channels.
    """
    event: GitHubEvent | None = GitHubPayloadParser.parse(
        event_type=request.headers["X-GitHub-Event"],
        raw_json=request.json,
    )
    if event is not None:
        bot.inform(event)


@post("/slack/commands")
def manage_slack_commands() -> dict | None:
    """
    Uses a `SlackBot` instance to run the slash command triggered by the user.
    Optionally returns a Slack message dict as a reply.
    :return: Appropriate response for received slash command in Slack block format.
    """
    # Unlike GitHub webhooks, Slack does not send the data in `requests.json`.
    # Instead, the data is passed in `request.forms`.
    response: dict[str, Any] | None = bot.run(raw_json=request.forms)
    return response


if __name__ == "__main__":
    load_dotenv(Path(".") / ".env")
    debug: bool = os.environ["DEBUG"] == "1"

    if not debug:
        sentry_sdk.init(
            dsn=os.environ["SENTRY_DSN"],
            integrations=[BottleIntegration()],
        )

    bot: SlackBot = SlackBot(
        token=os.environ["SLACK_OAUTH_TOKEN"],
        logger=Logger(int(os.environ["LOG_LAST_N_COMMANDS"] or 100)),
    )
    run(host="", port=5556, debug=debug)
