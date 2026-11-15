#!/usr/bin/env python3
"""Sends a prompt to an OpenAI-compatible chat endpoint and prints the reply.

Written for reviewkit.reviewCmd and reviewkit.verifyCmd: it reads the prompt
on stdin (or from --prompt-file, for `{prompt_file}`), and prints only the
model's answer, so local_review.py can find the report markers in it. Any
OpenAI-compatible server works: a litellm proxy, vLLM, Ollama's /v1, or a
hosted API.

Usage:
  llm_chat.py --model NAME [--base-url URL] [--key-env VAR]
              [--env-file PATH] [--fallback NAME] [--timeout S]
              [--max-tokens N] [--prompt-file PATH]

The key is the environment variable --key-env names (default
REVIEWKIT_LLM_KEY); with --env-file, a `VAR=value` line in that file is used
when the variable is unset, so the key stays in the file it already lives
in. --base-url defaults to REVIEWKIT_LLM_BASE_URL, else
http://127.0.0.1:4000/v1. --fallback names a second model tried once when
the first fails with a rate limit (429), an overload (503/529) or a timeout.

Exit codes:
  0  a reply was printed
  1  the request failed (the error is on stderr)
  2  bad arguments, or no prompt
"""
import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request



def retryable_status(code):
    """Whether an HTTP status is worth one try on the fallback model: rate
    limited (429) or any server-side failure (5xx, including the 52x codes
    proxies such as Cloudflare return on a slow generation)."""
    return code == 429 or 500 <= code < 600


class RequestFailed(Exception):
    """The endpoint answered with an error, or did not answer."""

    def __init__(self, message, retryable):
        super().__init__(message)
        self.retryable = retryable


def read_key(var, env_file):
    """The API key from the environment, else from `var=` in env_file."""
    value = os.environ.get(var)
    if value:
        return value
    if env_file:
        try:
            with open(os.path.expanduser(env_file), encoding="utf-8") as fh:
                for line in fh:
                    name, sep, rest = line.strip().partition("=")
                    name = name.strip()
                    if name.startswith("export "):
                        name = name[len("export "):].strip()
                    if sep and name == var:
                        return rest.strip().strip("'\"")
        except OSError as exc:
            print("llm_chat: cannot read %s: %s" % (env_file, exc),
                  file=sys.stderr)
    return ""


def chat(base_url, key, model, prompt, timeout, max_tokens):
    """The assistant's text for one prompt; raises RequestFailed."""
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}]}
    if max_tokens:
        body["max_tokens"] = max_tokens
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + (key or "none")})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RequestFailed("%s: HTTP %d: %s" % (model, exc.code, detail),
                            retryable_status(exc.code))
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise RequestFailed("%s: %s" % (model, getattr(exc, "reason", exc)),
                            True)
    except ValueError as exc:
        raise RequestFailed("%s: reply is not JSON (%s)" % (model, exc), False)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RequestFailed("%s: reply has no message: %s"
                            % (model, json.dumps(data)[:300]), False)
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content
                          if isinstance(part, dict))
    return content or ""


def main(argv):
    parser = argparse.ArgumentParser(
        description="Prompt an OpenAI-compatible chat endpoint.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--fallback")
    parser.add_argument("--base-url",
                        default=os.environ.get("REVIEWKIT_LLM_BASE_URL",
                                               "http://127.0.0.1:4000/v1"))
    parser.add_argument("--key-env", default="REVIEWKIT_LLM_KEY")
    parser.add_argument("--env-file")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--max-tokens", type=int, default=0)
    parser.add_argument("--prompt-file")
    args = parser.parse_args(argv)
    if args.prompt_file:
        try:
            with open(args.prompt_file, encoding="utf-8") as fh:
                prompt = fh.read()
        except OSError as exc:
            print("llm_chat: %s" % exc, file=sys.stderr)
            return 2
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        print("llm_chat: empty prompt", file=sys.stderr)
        return 2
    key = read_key(args.key_env, args.env_file)
    models = [args.model] + ([args.fallback] if args.fallback else [])
    for index, model in enumerate(models):
        try:
            print(chat(args.base_url, key, model, prompt, args.timeout,
                       args.max_tokens))
            return 0
        except RequestFailed as exc:
            last = index == len(models) - 1
            print("llm_chat: %s%s" % (exc, "" if last or not exc.retryable
                                       else "; trying " + models[index + 1]),
                  file=sys.stderr)
            if last or not exc.retryable:
                return 1
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
