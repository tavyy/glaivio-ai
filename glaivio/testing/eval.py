import functools
from dataclasses import dataclass
from typing import Callable

# Global registry of eval functions
_EVALS: list = []


@dataclass
class EvalCase:
    input: str
    expected: str
    description: str = ""


def eval(fn: Callable):
    """
    Register a function as an evaluation test case.

    Usage:
        from glaivio.testing import eval

        @eval
        def test_booking(agent):
            return [
                EvalCase("I want Tuesday 10am", "booked", "basic booking"),
                EvalCase("Cancel my appointment", "cancelled", "cancellation"),
            ]
    """
    _EVALS.append(fn)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


def run_evals(agent):
    """Run all registered evals against an agent. Called by glaivio test."""
    if not _EVALS:
        print("No evals found. Create a tests/ folder with @eval decorated functions.")
        return

    total = 0
    passed = 0
    failed = []

    for eval_fn in _EVALS:
        cases = eval_fn(agent)
        for case in cases:
            total += 1
            # reset session between cases
            agent.reset("eval-user")
            reply = agent.reply("eval-user", case.input).lower()
            expected = case.expected.lower()

            if expected in reply:
                passed += 1
                print(f"  ✓ {case.description or case.input}")
            else:
                failed.append(case)
                print(f"  ✗ {case.description or case.input}")
                print(f"    Expected: '{case.expected}'")
                print(f"    Got:      '{reply[:100]}'")

    print(f"\n{passed}/{total} passed", end="")
    if failed:
        print(f" — {len(failed)} regression(s) detected ❌")
    else:
        print(" ✅")

    return passed == total
