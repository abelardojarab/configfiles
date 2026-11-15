#!/usr/bin/env python3
"""Tests for the review-kit scripts, run against throwaway git repositories.

Usage (from the kit root):
  python3 -m unittest discover -s tests -v

Exit codes: 0 when every test passes, 1 otherwise (unittest's convention).
"""
import glob
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(KIT, "scripts")
HOOKS = os.path.join(KIT, "hooks")
sys.path.insert(0, SCRIPTS)

import kit  # noqa: E402
import stack_churn  # noqa: E402

ZERO = "0" * 40
PAD = ("This report lists every check the reviewer ran on the change, the "
       "files it read and the reasoning behind each conclusion it reached. ")
FAKE_REVIEWER = textwrap.dedent("""\
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    prompt = sys.stdin.read()
    with open(os.path.join(here, "stdin.txt"), "a") as handle:
        handle.write(prompt + "\\n=====\\n")
    with open(os.path.join(here, "report.txt")) as handle:
        report = handle.read()
    print("thinking...")
    print("<<<LOCAL_REVIEW_REPORT")
    print(report)
    print("LOCAL_REVIEW_REPORT>>>")
    """)


class Repo:
    """A throwaway repository with helpers to commit and run the scripts."""

    def __init__(self, path):
        self.path = path
        os.makedirs(path, exist_ok=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test Author")
        self.git("config", "user.email", "author@example.com")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args, input_text=None, check=True):
        proc = subprocess.run(["git", *args], cwd=self.path, input=input_text,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
        if check and proc.returncode != 0:
            raise AssertionError("git %s failed: %s" % (" ".join(args),
                                                        proc.stderr))
        return proc.stdout

    def write(self, rel, text):
        path = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)

    def commit(self, message, files=None, amend=False):
        for rel, text in (files or {}).items():
            if text is None:
                self.git("rm", "-q", rel)
            else:
                self.write(rel, text)
                self.git("add", rel)
        args = ["commit", "-q", "--no-verify", "--allow-empty", "-F", "-"]
        if amend:
            args.append("--amend")
        self.git(*args, input_text=message)
        return self.head()

    def head(self):
        return self.git("rev-parse", "HEAD").strip()

    def run(self, script, *args, input_text=None, env=None, cwd=None):
        return subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, script), *args],
            cwd=cwd or self.path, input=input_text,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, env=dict(os.environ, **(env or {})))

    def state(self, *parts):
        return os.path.join(self.path, ".git", "review-kit", *parts)


class KitTestCase(unittest.TestCase):
    """Isolates git and the kit's settings from the machine running tests."""

    def setUp(self):
        self._env = dict(os.environ)
        self._cwd = os.getcwd()
        for key in list(os.environ):
            if key.startswith(("REVIEWKIT_", "GIT_")):
                del os.environ[key]
        os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
        os.environ.pop("PARALLEL", None)
        os.environ.pop("TIMEOUT_S", None)
        self.tmp = tempfile.mkdtemp(prefix="review-kit-test-")
        self.repo = Repo(os.path.join(self.tmp, "repo"))
        self.repo.commit("Start the project\n", {"README.txt": "start\n"})

    def tearDown(self):
        os.chdir(self._cwd)
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def feature(self):
        self.repo.git("checkout", "-q", "-b", "feature")

    def in_repo(self):
        os.chdir(self.repo.path)

    def assertExit(self, proc, code, what=""):
        self.assertEqual(proc.returncode, code,
                         "%sexit %d, wanted %d\n--- stdout\n%s\n--- stderr\n%s"
                         % (what and "%r: " % what, proc.returncode, code,
                            proc.stdout, proc.stderr))


class FingerprintTest(KitTestCase):

    def test_rebase_and_trailer_edit_keep_it_body_and_patch_change_it(self):
        self.feature()
        self.repo.commit("Add the order total\n\nSums the line prices.\n",
                         {"order.txt": "total\nprice\n"})
        self.in_repo()
        first = kit.fingerprint_of("HEAD")

        self.repo.git("checkout", "-q", "main")
        self.repo.commit("Touch another file\n", {"other.txt": "x\n"})
        self.repo.git("checkout", "-q", "feature")
        self.repo.git("rebase", "-q", "main")
        self.assertEqual(kit.fingerprint_of("HEAD"), first)

        self.repo.commit("Add the order total\n\nSums the line prices.\n\n"
                         "Signed-off-by: Test Author <author@example.com>\n",
                         amend=True)
        self.assertEqual(kit.fingerprint_of("HEAD"), first)

        self.repo.commit("Add the order total\n\nSums every line price.\n",
                         amend=True)
        body_changed = kit.fingerprint_of("HEAD")
        self.assertNotEqual(body_changed, first)

        self.repo.commit("Add the order total\n\nSums every line price.\n",
                         {"order.txt": "total\nprice\ntax\n"}, amend=True)
        self.assertNotEqual(kit.fingerprint_of("HEAD"), body_changed)

    def test_fingerprint_is_twelve_hex_characters(self):
        self.in_repo()
        value = kit.fingerprint_of("HEAD")
        self.assertRegex(value, r"^[0-9a-f]{12}$")


class CommitMsgTest(KitTestCase):

    def check(self, text, env=None):
        path = os.path.join(self.tmp, "MSG")
        with open(path, "w") as handle:
            handle.write(text)
        return self.repo.run("commit_msg.py", path, env=env)

    def test_ai_co_author_fails(self):
        proc = self.check("Add ComputeDiscount\n\nCo-authored-by: Claude "
                          "<noreply@anthropic.com>\n")
        self.assertExit(proc, 1)
        self.assertIn("forbidMessage", proc.stdout)
        self.assertIn("Co-authored-by: Claude", proc.stdout)

    def test_other_attribution_forms_fail(self):
        for text in ("Fix rate_limit\n\nGenerated with GitHub Copilot\n",
                     "Fix rate_limit\n\nAssisted-by: some tool\n",
                     "Fix rate_limit \U0001F916\n",
                     "Fix rate_limit\n\nGenerated by AI.\n",
                     "Fix rate_limit\n\nCo-authored-by: Copilot "
                     "<bot@example.com>\n",
                     "Fix rate_limit\n\nCo-authored-by: Claude "
                     "<claude@example.com>\n",
                     "Fix rate_limit\n\nCo-Authored-By: Devin <d@x.y>\n"):
            self.assertExit(self.check(text), 1, text)

    def test_kernel_tree_allows_disclosure_but_not_ai_sign_off(self):
        for name in ("Kconfig", "MAINTAINERS"):
            self.repo.write(name, "x\n")
        disclosure = ("net: fix the queue length\n\nThe fix was drafted "
                      "with Claude Code and reviewed by hand.\n\n"
                      "Assisted-by: Claude Code\n"
                      "Signed-off-by: Test Author <author@example.com>\n")
        self.assertExit(self.check(disclosure), 0)
        for trailer in ("Signed-off-by: Claude <claude@example.com>",
                        "Co-developed-by: GitHub Copilot <bot@example.com>",
                        "Co-authored-by: Claude Code <noreply@anthropic.com>"):
            proc = self.check("net: fix the queue length\n\n" + trailer
                              + "\n")
            self.assertExit(proc, 1, trailer)
            self.assertIn("DCO trailer", proc.stdout)
        # A person at a model vendor signs off with the vendor's domain.
        self.assertExit(self.check(
            "net: fix the queue length\n\nSigned-off-by: Jane Doe "
            "<jane@anthropic.com>\nCo-developed-by: Sam Roe "
            "<sam@openai.com>\n"), 0)
        # Outside a kernel tree the same disclosure is blocked.
        os.remove(os.path.join(self.repo.path, "Kconfig"))
        self.assertExit(self.check(disclosure), 1)

    def test_human_co_author_and_sign_off_pass(self):
        proc = self.check("Add ComputeDiscount\n\nApplies the coupon rate.\n\n"
                          "Co-authored-by: Claude Martin <cm@example.com>\n"
                          "Signed-off-by: Test Author <author@example.com>\n")
        self.assertExit(proc, 0)

    def test_ordinary_wording_passes(self):
        for text in ("Fix rate_limit\n\nThe file is generated by the build "
                     "script.\n",
                     "Move the cursor handling into Order\n",
                     "Fix rate_limit\n\nReviewed-by: Devin Smith "
                     "<ds@example.com>\nCo-authored-by: Claude Martin "
                     "<cm@example.com>\nCo-authored-by: Claude Martin "
                     "<cm@example.com>\n"):
            self.assertExit(self.check(text), 0)

    def test_comments_and_scissors_are_ignored(self):
        proc = self.check("Add ComputeDiscount\n# Co-authored-by: Copilot\n"
                          "# ------------------------ >8 ------------------"
                          "------\nCo-authored-by: Copilot <x@example.com>\n")
        self.assertExit(proc, 0)

    def test_empty_subject_fails(self):
        self.assertExit(self.check("# only a comment\n"), 1)

    def test_duplicated_paragraph_fails(self):
        para = "The discount applies to every order above the threshold."
        proc = self.check("Add ComputeDiscount\n\n%s\n\n%s\n" % (para, para))
        self.assertExit(proc, 1)
        self.assertIn("repeated", proc.stdout)

    def test_missing_required_trailer_fails(self):
        env = {"REVIEWKIT_REQUIRE_TRAILERS": "Signed-off-by, Reviewed-by"}
        proc = self.check("Add ComputeDiscount\n\nApplies the rate.\n\n"
                          "Signed-off-by: Test Author <a@example.com>\n",
                          env=env)
        self.assertExit(proc, 1)
        self.assertIn("Reviewed-by", proc.stdout)
        self.assertNotIn("Signed-off-by:", proc.stdout.replace(
            "missing trailer Signed-off-by", ""))

    def test_required_trailer_from_git_config(self):
        self.repo.git("config", "reviewkit.requireTrailers", "Signed-off-by")
        self.assertExit(self.check("Add ComputeDiscount\n"), 1)
        self.assertExit(self.check("Add ComputeDiscount\n\nSigned-off-by: "
                                   "Test Author <a@example.com>\n"), 0)


ORDER_CC = textwrap.dedent("""\
    struct Order {
      double total;
    };

    double ComputeDiscount(const Order& order) {
      return order.total * 0.1;
    }
    """)


class TruthAuditTest(KitTestCase):

    def test_missing_function_is_flagged(self):
        self.feature()
        self.repo.commit("Add the discount\n", {
            "order.cc": ORDER_CC + "// Callers go through ApplyCouponRate.\n"})
        proc = self.repo.run("truth_audit.py")
        self.assertExit(proc, 1)
        self.assertIn("[symbol] `ApplyCouponRate`", proc.stdout)
        self.assertIn("== Manual checklist", proc.stdout)

    def test_function_the_commit_adds_is_not_flagged(self):
        self.feature()
        self.repo.commit("Add the discount\n\nComputeDiscount takes 10%.\n", {
            "order.cc": ORDER_CC + "// ComputeDiscount is the only entry.\n"})
        proc = self.repo.run("truth_audit.py")
        self.assertExit(proc, 0)
        self.assertIn("== Flags\n(none)", proc.stdout)
        self.assertRegex(proc.stdout, r"\n +\d+\. \[order\.cc\] "
                                      r"ComputeDiscount is the only entry\.")

    def test_symbol_found_at_merge_base_is_not_flagged(self):
        self.repo.commit("Add the order\n", {"order.cc": ORDER_CC})
        self.feature()
        self.repo.commit("Note the entry point\n",
                         {"notes.cc": "// See ComputeDiscount.\n"})
        self.assertExit(self.repo.run("truth_audit.py"), 0)

    def test_prose_files_reach_the_checklist_but_are_not_symbols(self):
        self.feature()
        self.repo.commit("Document the bridge\n", {
            "README.md": "Run `StartBridge` after `make_config`.\n",
            "stack/compose.yml": "# NetherNet needs WebRTC on UDP\n",
            "Dockerfile": "# ServiceMesh sidecar\nFROM scratch\n"})
        proc = self.repo.run("truth_audit.py")
        self.assertExit(proc, 0)
        self.assertNotIn("[symbol]", proc.stdout)
        self.assertRegex(proc.stdout, r"\[README\.md\] Run `StartBridge`")
        self.assertRegex(proc.stdout,
                         r"\[stack/compose\.yml\] NetherNet needs WebRTC")
        self.assertRegex(proc.stdout, r"\[Dockerfile\] ServiceMesh sidecar")

    def test_known_names_are_not_flagged(self):
        self.feature()
        self.repo.commit("Add the discount\n", {
            "order.cc": ORDER_CC + "// Mirrors PriceBook and ApplyCouponRate.\n"})
        proc = self.repo.run("truth_audit.py")
        self.assertExit(proc, 1)
        self.assertIn("[symbol] `PriceBook`", proc.stdout)
        self.assertIn("[symbol] `ApplyCouponRate`", proc.stdout)
        proc = self.repo.run("truth_audit.py",
                             env={"REVIEWKIT_KNOWN_NAMES":
                                  "PriceBook, ApplyCouponRate"})
        self.assertExit(proc, 0)

    def test_absent_config_claim_is_flagged(self):
        self.feature()
        self.repo.commit("Turn on throttling\n\nSets rate_limit = True for "
                         "every account.\n", {"notes.txt": "throttle\n"})
        proc = self.repo.run("truth_audit.py")
        self.assertExit(proc, 1)
        self.assertIn("[config] `rate_limit`", proc.stdout)

    def test_config_claim_in_tree_passes(self):
        self.feature()
        self.repo.commit("Turn on throttling\n\nSets rate_limit = True for "
                         "every account.\n",
                         {"settings.toml": "rate_limit = true\n"})
        self.assertExit(self.repo.run("truth_audit.py"), 0)

    def test_unknown_commit_and_issue_reference(self):
        self.feature()
        self.repo.commit("Follow up on deadbeef1234\n\nSee #42.\n",
                         {"notes.txt": "x\n"})
        proc = self.repo.run("truth_audit.py")
        self.assertExit(proc, 1)
        self.assertIn("[commit] deadbeef1234", proc.stdout)
        self.assertIn("[issue] #42", proc.stdout)

    def test_works_from_a_subdirectory(self):
        self.feature()
        self.repo.commit("Add the discount\n",
                         {"src/order.cc":
                          ORDER_CC + "// Uses MissingHelper.\n"})
        proc = self.repo.run("truth_audit.py",
                             cwd=os.path.join(self.repo.path, "src"))
        self.assertExit(proc, 1)
        self.assertIn("`MissingHelper`", proc.stdout)


def numbered(count, prefix="line"):
    return "".join("%s %d\n" % (prefix, i) for i in range(count))


class StackChurnTest(KitTestCase):

    def test_deleting_six_earlier_lines_fails(self):
        self.feature()
        lines = numbered(10).splitlines(True)
        self.repo.commit("Add the order list\n", {"list.txt": "".join(lines)})
        self.repo.commit("Trim the order list\n",
                         {"list.txt": "".join(lines[6:])})
        proc = self.repo.run("stack_churn.py")
        self.assertExit(proc, 1)
        self.assertIn("CHURN", proc.stdout)

    def test_deleting_two_earlier_lines_passes(self):
        self.feature()
        lines = numbered(10).splitlines(True)
        self.repo.commit("Add the order list\n", {"list.txt": "".join(lines)})
        self.repo.commit("Trim the order list\n",
                         {"list.txt": "".join(lines[2:])})
        self.assertExit(self.repo.run("stack_churn.py"), 0)

    def test_pure_move_commit_is_exempt(self):
        self.feature()
        lines = numbered(10).splitlines(True)
        self.repo.commit("Pure move of the order list\n",
                         {"list.txt": "".join(lines)})
        self.repo.commit("Trim the order list\n",
                         {"list.txt": "".join(lines[6:])})
        proc = self.repo.run("stack_churn.py")
        self.assertExit(proc, 0)
        self.assertIn("move-only", proc.stdout)

    def test_merge_in_range_cannot_be_checked(self):
        self.feature()
        self.repo.commit("Add the order list\n", {"list.txt": numbered(3)})
        self.repo.git("checkout", "-q", "-b", "side", "main")
        self.repo.commit("Add the rate table\n", {"rates.txt": "r\n"})
        self.repo.git("checkout", "-q", "feature")
        self.repo.git("merge", "-q", "--no-edit", "--no-ff", "side")
        proc = self.repo.run("stack_churn.py")
        self.assertExit(proc, 2)
        self.assertIn("merge", proc.stdout)

    def test_empty_stack_exits_two(self):
        self.feature()
        self.assertExit(self.repo.run("stack_churn.py"), 2)

    def test_pure_functions_carry_lines_through_hunks(self):
        first = textwrap.dedent("""\
            diff --git a/f.txt b/f.txt
            new file mode 100644
            --- /dev/null
            +++ b/f.txt
            @@ -0,0 +1,3 @@
            +one
            +two
            +three
            """)
        second = textwrap.dedent("""\
            diff --git a/f.txt b/f.txt
            --- a/f.txt
            +++ b/f.txt
            @@ -1,3 +1,3 @@
            -one
            +uno
             two
             three
            """)
        pairs, added = stack_churn.churn([("c1", first), ("c2", second)])
        self.assertEqual(added, {"c1": 3, "c2": 1})
        self.assertEqual(pairs, {("c1", "c2"): [("f.txt", "one", False)]})
        self.assertEqual(stack_churn.totals(pairs, {"c1": "x", "c2": "y"}),
                         {"c2": 1})


CLEAN_MESSAGE = "Add release notes for the next version\n\nLists the fixes.\n"


class GateTest(KitTestCase):

    def gate(self, *args, env=None, input_text=None):
        return self.repo.run("gate.py", *args, env=env,
                             input_text=input_text)

    def test_too_many_changed_lines_fail(self):
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": numbered(151)})
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("151 changed lines (limit 150)", proc.stdout)
        self.assertIn("Push blocked.", proc.stdout)

    def test_max_lines_setting_is_read(self):
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": numbered(20)})
        proc = self.gate(env={"REVIEWKIT_MAX_LINES": "10"})
        self.assertExit(proc, 1)
        self.assertIn("20 changed lines (limit 10)", proc.stdout)

    def test_max_lines_zero_disables_the_size_check(self):
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": numbered(400)})
        proc = self.gate(env={"REVIEWKIT_MAX_LINES": "0"})
        self.assertExit(proc, 0)
        self.assertNotIn("changed lines (limit", proc.stdout)
        proc = self.repo.run("cq_sweep.py", "--commit", "HEAD",
                             env={"REVIEWKIT_MAX_LINES": "0"})
        self.assertNotIn("maxLines", proc.stdout)

    def test_small_clean_commit_passes_and_writes_a_stamp(self):
        self.feature()
        commit = self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})
        proc = self.gate()
        self.assertExit(proc, 0)
        self.assertIn("NOTE: no reviewCmd configured", proc.stdout)
        self.assertIn("manual checklist", proc.stdout)
        stamps = glob.glob(self.repo.state("gate_pass", "*.json"))
        self.assertEqual(len(stamps), 1)
        with open(stamps[0]) as handle:
            stamp = json.load(handle)
        self.in_repo()
        self.assertEqual(stamp["commits"],
                         {commit: kit.fingerprint_of(commit)})
        self.assertEqual(stamp["base"], "main")

    def test_dirty_work_tree_fails(self):
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})
        self.repo.write("notes.txt", "changed\n")
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("tracked files differ from HEAD", proc.stdout)

    def test_bad_message_and_unoverridden_flag_fail_then_override(self):
        self.feature()
        self.repo.commit("Wire the rate limiter\n\nCalls ThrottleOrders.\n",
                         {"notes.txt": "x\n"})
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("truth audit flags [symbol] `ThrottleOrders`",
                      proc.stdout)
        flag = [line for line in proc.stdout.splitlines()
                if line.startswith("[symbol]")][0]
        self.in_repo()
        path = self.repo.state("truth_overrides",
                               kit.fingerprint_of("HEAD") + ".txt")
        os.makedirs(os.path.dirname(path))
        with open(path, "w") as handle:
            handle.write("%s :: short\n" % flag)
        self.assertExit(self.gate(), 1)
        with open(path, "w") as handle:
            handle.write("%s :: the helper lives in the deploy scripts\n"
                         % flag)
        proc = self.gate()
        self.assertExit(proc, 0)
        self.assertIn("OVERRIDDEN [symbol]", proc.stdout)

    def test_empty_stack_exits_two(self):
        self.feature()
        self.assertExit(self.gate(), 2)

    def test_check_push(self):
        remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", remote], check=True)
        self.repo.git("remote", "add", "origin", remote)
        self.repo.git("push", "-q", "origin", "main")
        self.repo.git("fetch", "-q", "origin")
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})

        def push_check():
            line = "refs/heads/feature %s refs/heads/feature %s\n" % (
                self.repo.head(), ZERO)
            return self.gate("--check-push", "origin", remote,
                             input_text=line)

        self.assertExit(push_check(), 1)
        self.assertExit(self.gate(), 0)
        self.assertExit(push_check(), 0)

        self.repo.git("checkout", "-q", "main")
        self.repo.commit("Touch another file\n", {"other.txt": "x\n"})
        self.repo.git("push", "-q", "origin", "main")
        self.repo.git("checkout", "-q", "feature")
        self.repo.git("rebase", "-q", "origin/main")
        self.assertExit(push_check(), 0)

        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes and more\n"},
                         amend=True)
        proc = push_check()
        self.assertExit(proc, 1)
        self.assertIn("gate.py", proc.stdout)

    def test_check_push_rechecks_message_rules(self):
        remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", remote], check=True)
        self.repo.git("remote", "add", "origin", remote)
        self.repo.git("push", "-q", "origin", "main")
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})
        self.assertExit(self.gate(), 0)
        self.repo.commit(CLEAN_MESSAGE + "\nCo-authored-by: Copilot "
                         "<bot@example.com>\n", amend=True)
        line = "refs/heads/feature %s refs/heads/feature %s\n" % (
            self.repo.head(), ZERO)
        proc = self.gate("--check-push", "origin", remote, input_text=line)
        self.assertExit(proc, 1)
        self.assertIn("forbidMessage", proc.stdout)
        self.assertNotIn("No gate pass", proc.stdout)

    def test_check_push_skips_commits_another_remote_has(self):
        fork = os.path.join(self.tmp, "fork.git")
        upstream = os.path.join(self.tmp, "upstream.git")
        for path in (fork, upstream):
            subprocess.run(["git", "init", "-q", "--bare", path], check=True)
        self.repo.git("remote", "add", "origin", fork)
        self.repo.git("remote", "add", "upstream", upstream)
        self.repo.git("push", "-q", "origin", "main")
        self.repo.commit("Add the changelog\n", {"CHANGES.txt": "one\n"})
        self.repo.git("push", "-q", "upstream", "main")
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})
        line = "refs/heads/feature %s refs/heads/feature %s\n" % (
            self.repo.head(), ZERO)

        proc = self.gate("--check-push", "origin", fork, input_text=line)
        self.assertExit(proc, 1)
        self.assertIn("Add release notes", proc.stdout)
        self.assertNotIn("Add the changelog", proc.stdout)
        self.assertExit(self.gate("--base", "upstream/main"), 0)
        self.assertExit(self.gate("--check-push", "origin", fork,
                                  input_text=line), 0)

    def test_first_push_lets_only_the_base_branch_through(self):
        line = "refs/heads/main %s refs/heads/main %s\n" % (
            self.repo.head(), ZERO)
        proc = self.gate("--check-push", "origin", "unused", input_text=line)
        self.assertExit(proc, 0)
        self.assertIn("first push (to origin)", proc.stdout)

        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})
        line = "refs/heads/feature %s refs/heads/feature %s\n" % (
            self.repo.head(), ZERO)
        proc = self.gate("--check-push", "origin", "unused", input_text=line)
        self.assertExit(proc, 1)
        self.assertIn("Add release notes", proc.stdout)
        self.assertNotIn("Start the project", proc.stdout)

    def test_check_push_ignores_deletes_and_tags(self):
        lines = ("(delete) %s refs/heads/old %s\n"
                 "refs/tags/v1 %s refs/tags/v1 %s\n"
                 % (ZERO, "1" * 40, self.repo.head(), ZERO))
        self.assertExit(self.gate("--check-push", "origin", "unused",
                                  input_text=lines), 0)

    def test_map_operator_index_read_fails_and_find_passes(self):
        header = "#include <map>\n#include <string>\n\n" \
                 "std::map<std::string, int> some_map;\n\n"
        self.repo.commit("Add the rate table\n", {"rates.cc": header})
        self.feature()
        self.repo.commit("Read the rate\n", {"rates.cc": header + (
            "int Rate(const std::string& key) {\n"
            "  const auto& x = some_map[key];\n"
            "  return x;\n"
            "}\n")})
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("operator[]", proc.stdout)
        self.assertIn("rates.cc:7 some_map[...]", proc.stdout)

        self.repo.commit("Read the rate\n", {"rates.cc": header + (
            "int Rate(const std::string& key) {\n"
            "  auto it = some_map.find(key);\n"
            "  return it == some_map.end() ? 0 : it->second;\n"
            "}\n")}, amend=True)
        self.assertExit(self.gate(), 0)

    def test_unused_proto_enum_value_fails_and_real_use_passes(self):
        proto = ("syntax = \"proto3\";\n\nenum OrderState {\n"
                 "  ORDER_STATE_UNSPECIFIED = 0;\n  ORDER_STATE_OPEN = 1;\n")
        self.repo.commit("Add the order state\n",
                         {"order.proto": proto + "}\n"})
        self.feature()
        added = {"order.proto": proto + "  ORDER_STATE_SHIPPED = 2;\n}\n"}
        self.repo.commit("Add the shipped state\n", added)
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("ORDER_STATE_SHIPPED", proc.stdout)

        self.repo.commit("Add the shipped state\n", dict(added, **{
            "ship.cc": "bool Shipped(int state) {\n"
                       "  return state == ORDER_STATE_SHIPPED;\n}\n"}),
            amend=True)
        self.assertExit(self.gate(), 1)

        self.repo.commit("Add the shipped state\n", dict(added, **{
            "ship.cc": "int Ship() {\n  int state = ORDER_STATE_SHIPPED;\n"
                       "  return state;\n}\n"}), amend=True)
        self.assertExit(self.gate(), 0)

    def test_lint_and_tidy_commands(self):
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "a\nb\n"})
        self.repo.git("config", "--add", "reviewkit.lintCmd",
                      "*.txt::test -f")
        self.assertExit(self.gate(), 0)
        self.repo.git("config", "--add", "reviewkit.lintCmd", "false")
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("lintCmd 'false' exited 1", proc.stdout)
        self.repo.git("config", "--unset-all", "reviewkit.lintCmd")

        self.repo.git("config", "reviewkit.tidyCmd",
                      "*.txt::printf 'notes.txt:9:1: old\\n' ; true")
        proc = self.gate()
        self.assertExit(proc, 0)
        self.assertIn("out of scope: notes.txt:9", proc.stdout)
        self.repo.git("config", "reviewkit.tidyCmd",
                      "printf 'notes.txt:2:1: new\\n'")
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("lines the stack adds: notes.txt:2", proc.stdout)
        self.repo.git("config", "reviewkit.tidyCmd", "exit 3")
        proc = self.gate()
        self.assertExit(proc, 1)
        self.assertIn("command failed", proc.stdout)

    def test_gate_runs_in_a_linked_worktree(self):
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})
        worktree = os.path.join(self.tmp, "wt")
        self.repo.git("worktree", "add", "-q", "-b", "other", worktree)
        proc = self.repo.run("gate.py", cwd=worktree)
        self.assertExit(proc, 0)
        self.assertTrue(glob.glob(self.repo.state("gate_pass", "*.json")))


class LocalReviewTest(KitTestCase):

    def setUp(self):
        super().setUp()
        self.reviewer = os.path.join(self.tmp, "reviewer")
        os.makedirs(self.reviewer)
        with open(os.path.join(self.reviewer, "fake.py"), "w") as handle:
            handle.write(FAKE_REVIEWER)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, "prompts"))
        os.makedirs(os.path.join(self.home, "lenses", "common"))
        os.makedirs(os.path.join(self.home, "lenses", "cpp"))
        os.makedirs(os.path.join(self.home, "lenses", "python"))
        self.write_home("prompts/review.md",
                        "Review {{SHORT}} on {{BASE}}.\n{{STACK}}\n"
                        "{{MESSAGE}}\n{{CLAIMS}}\n{{LENSES}}\n{{CHECKS}}\n"
                        "{{DIFF}}\n")
        self.write_home("prompts/verify.md", "Verify {{SHORT}}.\n{{DIFF}}\n")
        os.environ["REVIEWKIT_HOME"] = self.home
        self.repo.git("config", "reviewkit.reviewCmd",
                      "%s %s" % (sys.executable,
                                 os.path.join(self.reviewer, "fake.py")))
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})

    def write_home(self, rel, text):
        with open(os.path.join(self.home, rel), "w") as handle:
            handle.write(text)

    def set_report(self, text):
        with open(os.path.join(self.reviewer, "report.txt"), "w") as handle:
            handle.write(text)

    def stdin_seen(self):
        with open(os.path.join(self.reviewer, "stdin.txt")) as handle:
            return handle.read()

    def report_path(self):
        self.in_repo()
        return self.repo.state("reviews", kit.fingerprint_of("HEAD") + ".md")

    def test_report_saved_with_provenance(self):
        self.set_report("## Findings\nNone.\n\n" + PAD * 4)
        proc = self.repo.run("local_review.py")
        self.assertExit(proc, 0)
        self.assertIn("clean ->", proc.stdout)
        with open(self.report_path()) as handle:
            first = handle.readline().strip()
        self.assertEqual(first, kit.provenance_line(
            self.repo.head()[:12], kit.fingerprint_of("HEAD")))
        self.assertIn("(no independent verifier configured)",
                      self.stdin_seen())
        proc = self.repo.run("local_review.py")
        self.assertIn("up to date", proc.stdout)

    def test_open_high_finding_blocks_and_declined_passes(self):
        self.set_report("## Findings\n### H1 — the total ignores tax\n"
                        + PAD * 4)
        self.assertExit(self.repo.run("local_review.py"), 0)
        proc = self.repo.run("gate.py")
        self.assertExit(proc, 1)
        self.assertIn("open findings H1", proc.stdout)

        os.remove(self.report_path())
        self.set_report("## Declined\n### H1 — the total ignores tax\n"
                        "Declined: tax is added by the caller before "
                        "checkout.\n\n" + PAD * 4)
        self.assertExit(self.repo.run("local_review.py"), 0)
        self.assertExit(self.repo.run("gate.py"), 0)

    def test_short_declined_reason_blocks(self):
        self.set_report("## Summary\n" + PAD * 4
                        + "\n## Declined\n### M1 — naming\nDeclined: no.\n")
        self.assertExit(self.repo.run("local_review.py"), 0)
        proc = self.repo.run("gate.py")
        self.assertExit(proc, 1)
        self.assertIn("shorter than 20", proc.stdout)

    def test_hand_written_report_is_rejected_and_replaced(self):
        path = self.report_path()
        os.makedirs(os.path.dirname(path))
        with open(path, "w") as handle:
            handle.write("No findings.\n" + PAD * 6)
        proc = self.repo.run("gate.py")
        self.assertExit(proc, 1)
        self.assertIn("not written by local_review.py", proc.stdout)
        self.set_report("## Findings\nNone.\n\n" + PAD * 4)
        self.assertExit(self.repo.run("local_review.py"), 0)
        self.assertExit(self.repo.run("gate.py"), 0)

    def test_missing_report_blocks_the_gate(self):
        proc = self.repo.run("gate.py")
        self.assertExit(proc, 1)
        self.assertIn("run local_review.py", proc.stdout)

    def test_no_report_in_output_fails(self):
        with open(os.path.join(self.reviewer, "fake.py"), "w") as handle:
            handle.write("print('nothing to see')\n")
        self.assertExit(self.repo.run("local_review.py"), 1)
        self.assertFalse(os.path.exists(self.report_path()))

    def test_unconfigured_reviewer_exits_two(self):
        self.repo.git("config", "--unset", "reviewkit.reviewCmd")
        self.assertExit(self.repo.run("local_review.py"), 2)

    def test_lenses_checks_and_claims_reach_the_reviewer(self):
        self.write_home("lenses/common/b-style.md",
                        "Rule beta: name things.\n")
        self.write_home("lenses/common/a-scope.md",
                        "Rule alpha: one problem per commit. {{DIFF}}\n")
        self.write_home("lenses/cpp/cpp.md", "Rule cpp: braces.\n")
        self.write_home("prompts/checks.md", "Check gamma: totals add up.\n")
        verifier = os.path.join(self.reviewer, "verify.py")
        with open(verifier, "w") as handle:
            handle.write("import sys\nsys.stdin.read()\n"
                         "print('claim: the notes list one fix')\n")
        self.repo.git("config", "reviewkit.verifyCmd",
                      "%s %s" % (sys.executable, verifier))
        self.set_report("## Findings\nNone.\n\n" + PAD * 4)
        self.assertExit(self.repo.run("local_review.py"), 0)
        seen = self.stdin_seen()
        self.assertIn("### common/a-scope.md\nRule alpha", seen)
        self.assertLess(seen.index("a-scope.md"), seen.index("b-style.md"))
        self.assertNotIn("Rule cpp", seen)
        self.assertIn("Rule alpha: one problem per commit. {{DIFF}}", seen)
        self.assertIn("Check gamma: totals add up.", seen)
        self.assertIn("claim: the notes list one fix", seen)
        self.assertIn("+fixes", seen)
        self.assertNotIn("{{LENSES}}", seen)

    def test_language_lenses_follow_the_files_or_the_setting(self):
        self.write_home("lenses/common/a.md", "Rule common.\n")
        self.write_home("lenses/cpp/cpp.md", "Rule cpp: braces.\n")
        self.write_home("lenses/python/python.md", "Rule python: docstrings.\n")
        self.set_report("## Findings\nNone.\n\n" + PAD * 4)
        self.repo.commit(CLEAN_MESSAGE, {"a/order.cc": "int x;\n"})
        self.assertExit(self.repo.run("local_review.py"), 0)
        seen = self.stdin_seen()
        self.assertIn("### common/a.md", seen)
        self.assertIn("### cpp/cpp.md\nRule cpp", seen)
        self.assertNotIn("Rule python", seen)
        self.repo.commit(CLEAN_MESSAGE, {"tool.py": "x = 1\n"})
        self.assertExit(self.repo.run(
            "local_review.py", env={"REVIEWKIT_LENSES": "python"}), 0)
        seen = self.stdin_seen().split("=====\n")[-2]
        self.assertIn("Rule python", seen)
        self.assertNotIn("Rule cpp", seen)

    def test_missing_lenses_and_checks_use_fallback_text(self):
        self.set_report("## Findings\nNone.\n\n" + PAD * 4)
        self.assertExit(self.repo.run("local_review.py"), 0)
        seen = self.stdin_seen()
        self.assertIn("(no lenses directory)", seen)
        self.assertIn("(no checks file)", seen)

    def test_prompt_file_placeholder(self):
        script = os.path.join(self.reviewer, "from_file.py")
        with open(script, "w") as handle:
            handle.write(textwrap.dedent("""\
                import os, sys
                here = os.path.dirname(os.path.abspath(__file__))
                assert sys.stdin.read() == ""
                prompt = open(sys.argv[1]).read()
                open(os.path.join(here, "stdin.txt"), "w").write(prompt)
                print("<<<LOCAL_REVIEW_REPORT")
                print(open(os.path.join(here, "report.txt")).read())
                print("LOCAL_REVIEW_REPORT>>>")
                """))
        self.repo.git("config", "reviewkit.reviewCmd",
                      "%s %s {prompt_file}" % (sys.executable, script))
        self.set_report("## Findings\nNone.\n\n" + PAD * 4)
        self.assertExit(self.repo.run("local_review.py"), 0)
        self.assertIn("Review %s" % self.repo.head()[:12], self.stdin_seen())

    def test_echoed_format_example_is_not_saved(self):
        with open(os.path.join(self.reviewer, "echo.py"), "w") as handle:
            handle.write(FAKE_REVIEWER.replace(
                'print("thinking...")',
                'print("<<<LOCAL_REVIEW_REPORT\\nexample\\n'
                'LOCAL_REVIEW_REPORT>>>")'))
        self.repo.git("config", "reviewkit.reviewCmd", "%s %s" % (
            sys.executable, os.path.join(self.reviewer, "echo.py")))
        self.set_report("## Findings\nNone.\n\n" + PAD * 4)
        self.assertExit(self.repo.run("local_review.py"), 0)
        with open(self.report_path()) as handle:
            self.assertNotIn("example", handle.read())


class SweepTest(KitTestCase):

    def test_clean_and_findings(self):
        self.feature()
        self.repo.commit("Add notes\n", {"notes.txt": "fine\n"})
        proc = self.repo.run("cq_sweep.py")
        self.assertExit(proc, 0)
        self.assertEqual(proc.stdout.strip(), "clean")

        self.repo.commit("Add the order\n", {"order.cc": (
            "#include <tuple>\n"
            "// Keep this list in sync with the rate table.\n"
            "int Total(int n) {\n"
            "  if (n < 0) return 0;\n"
            "  return n;\n"
            "}\n")})
        proc = self.repo.run("cq_sweep.py", "--strict")
        self.assertExit(proc, 1)
        self.assertIn("Keep this list in sync", proc.stdout)
        self.assertIn("without braces", proc.stdout)
        self.assertIn("<tuple> is included but nothing from it is used",
                      proc.stdout)

    def test_staged_mode(self):
        self.repo.write("long.py", "x = 1  # " + "y" * 90 + "\n")
        self.repo.git("add", "long.py")
        proc = self.repo.run("cq_sweep.py", "--staged")
        self.assertExit(proc, 0)
        self.assertIn("over reviewkit.maxCols", proc.stdout)
        proc = self.repo.run("cq_sweep.py", "--staged",
                             env={"REVIEWKIT_MAX_COLS": "0"})
        self.assertNotIn("maxCols", proc.stdout)


class WorktreeSweepTest(KitTestCase):

    def test_worktree_sees_unstaged_and_untracked_lines(self):
        self.repo.write("README.txt", "start\n// see line 12 of the docs\n")
        self.repo.write("new/tool.cc",
                        "int f(int a) {\n  if (a) return 1;\n  return 0;\n}\n")
        self.repo.write(".gitignore", "build/\n")
        self.repo.write("build/gen.cc", "  if (x) return 1;\n")
        proc = self.repo.run("cq_sweep.py", "--worktree", "--strict")
        self.assertExit(proc, 1)
        self.assertIn("new/tool.cc:2", proc.stdout)
        self.assertNotIn("build/gen.cc", proc.stdout)
        self.assertNotIn("Size over", proc.stdout)
        self.assertExit(self.repo.run("cq_sweep.py", "--staged",
                                      "--strict"), 0)

    def test_untracked_nested_repository_is_skipped(self):
        nested = Repo(os.path.join(self.repo.path, "vendor", "lib"))
        nested.write("x.cc", "  if (a) return 1;\n")
        self.repo.write("tool.cc", "  if (a) return 1;\n")
        proc = self.repo.run("cq_sweep.py", "--worktree", "--strict")
        self.assertExit(proc, 1)
        self.assertIn("tool.cc:1", proc.stdout)
        self.assertNotIn("vendor/lib", proc.stdout + proc.stderr)

    def test_clean_worktree_is_clean(self):
        proc = self.repo.run("cq_sweep.py", "--worktree", "--strict")
        self.assertExit(proc, 0)
        self.assertIn("clean", proc.stdout)


class ClaudeStopHookTest(KitTestCase):

    def hook(self, payload='{"stop_hook_active": false}'):
        return subprocess.run(
            ["sh", os.path.join(HOOKS, "claude-stop.sh")], cwd=self.repo.path,
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)

    def test_only_acts_in_opted_in_repositories(self):
        self.repo.write("a.cc", "void f(int a) {\n  if (a) return;\n}\n")
        self.assertExit(self.hook(), 0)
        self.repo.git("config", "reviewkit.home", KIT)
        proc = self.hook()
        self.assertExit(proc, 2)
        self.assertIn("a.cc:2", proc.stderr)
        self.assertExit(self.hook('{"stop_hook_active": true}'), 0)
        self.repo.git("config", "reviewkit.agentStop", "false")
        self.assertExit(self.hook(), 0)

    def test_clean_change_lets_the_agent_stop(self):
        self.repo.git("config", "reviewkit.home", KIT)
        self.repo.write("notes.txt", "fine\n")
        self.assertExit(self.hook(), 0)


class _FakeChat(BaseHTTPRequestHandler):
    """Answers /chat/completions. Models "busy", "gateway" and "bad" get
    HTTP 429, 524 and 400; "cut" gets a reply stopped at the token limit
    and "empty" a reply with no text."""

    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _FakeChat.seen.append((self.headers.get("Authorization"),
                               body["model"], body.get("max_tokens")))
        status = {"busy": 429, "gateway": 524, "bad": 400}.get(body["model"])
        if status:
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b'{"error": "refused"}')
            return
        text = "echo: %s %s" % (body["model"],
                                body["messages"][0]["content"])
        finish = "stop"
        if body["model"] == "cut":
            finish = "length"
        elif body["model"] == "empty":
            text = ""
        reply = {"choices": [{"message": {"content": text},
                              "finish_reason": finish}]}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class LlmChatTest(KitTestCase):

    def setUp(self):
        super().setUp()
        _FakeChat.seen = []
        self.server = HTTPServer(("127.0.0.1", 0), _FakeChat)
        threading.Thread(target=self.server.serve_forever,
                         daemon=True).start()
        self.url = "http://127.0.0.1:%d/v1" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def chat(self, *args, input_text="review this", env=None):
        return self.repo.run("llm_chat.py", "--base-url", self.url, *args,
                             input_text=input_text, env=env)

    def test_prints_the_reply_with_the_key_from_an_env_file(self):
        env_file = os.path.join(self.tmp, "stack.env")
        with open(env_file, "w") as handle:
            handle.write("OTHER=1\nexport PROXY_KEY = sk-test\n")
        proc = self.chat("--model", "m1", "--key-env", "PROXY_KEY",
                         "--env-file", env_file)
        self.assertExit(proc, 0)
        self.assertEqual(proc.stdout.strip(), "echo: m1 review this")
        self.assertEqual(_FakeChat.seen, [("Bearer sk-test", "m1", None)])

    def test_environment_key_wins_and_max_tokens_is_sent(self):
        env_file = os.path.join(self.tmp, "stack.env")
        with open(env_file, "w") as handle:
            handle.write("PROXY_KEY=sk-file\n")
        proc = self.chat("--model", "m1", "--key-env", "PROXY_KEY",
                         "--env-file", env_file, "--max-tokens", "64",
                         env={"PROXY_KEY": "sk-env"})
        self.assertExit(proc, 0)
        self.assertEqual(_FakeChat.seen, [("Bearer sk-env", "m1", 64)])

    def test_falls_back_on_rate_limit_and_reads_a_prompt_file(self):
        path = os.path.join(self.tmp, "prompt.md")
        with open(path, "w") as handle:
            handle.write("from file")
        proc = self.chat("--model", "busy", "--fallback", "m2",
                         "--prompt-file", path, input_text="")
        self.assertExit(proc, 0)
        self.assertIn("echo: m2 from file", proc.stdout)
        self.assertIn("trying m2", proc.stderr)

    def test_any_5xx_falls_back_but_a_4xx_does_not(self):
        proc = self.chat("--model", "gateway", "--fallback", "m2")
        self.assertExit(proc, 0)
        self.assertIn("echo: m2", proc.stdout)
        _FakeChat.seen = []
        proc = self.chat("--model", "bad", "--fallback", "m2")
        self.assertExit(proc, 1)
        self.assertIn("HTTP 400", proc.stderr)
        self.assertEqual([seen[1] for seen in _FakeChat.seen], ["bad"])

    def test_cut_off_reply_falls_back(self):
        proc = self.chat("--model", "cut", "--fallback", "m2")
        self.assertExit(proc, 0)
        self.assertEqual(proc.stdout.strip(), "echo: m2 review this")
        self.assertIn("cut: reply cut off at the token limit", proc.stderr)

    def test_empty_reply_falls_back(self):
        proc = self.chat("--model", "empty", "--fallback", "m2")
        self.assertExit(proc, 0)
        self.assertEqual(proc.stdout.strip(), "echo: m2 review this")
        self.assertIn("empty: empty reply (finish_reason stop)", proc.stderr)

    def test_empty_reply_without_fallback_exits_one(self):
        proc = self.chat("--model", "empty")
        self.assertExit(proc, 1)
        self.assertEqual(proc.stdout, "")
        self.assertIn("empty: empty reply", proc.stderr)

    def test_failure_and_empty_prompt(self):
        self.assertExit(self.chat("--model", "busy"), 1)
        self.assertExit(self.chat("--model", "m1", input_text=" "), 2)

    def test_drives_local_review_end_to_end(self):
        report = ("<<<LOCAL_REVIEW_REPORT\n## Findings\nNone.\n\n" + PAD * 4
                  + "\nLOCAL_REVIEW_REPORT>>>")
        responder = os.path.join(self.tmp, "respond.py")
        with open(responder, "w") as handle:
            handle.write("import sys\nsys.stdin.read()\nprint(%r)\n" % report)
        # The reviewer is llm_chat.py; the fake server echoes, so wrap it to
        # check that the prompt reaches the endpoint and the report is saved.
        self.repo.git("config", "reviewkit.reviewCmd",
                      "%s %s --base-url %s --model m1 >/dev/null && %s %s"
                      % (sys.executable, os.path.join(SCRIPTS, "llm_chat.py"),
                         self.url, sys.executable, responder))
        self.feature()
        self.repo.commit(CLEAN_MESSAGE, {"notes.txt": "fixes\n"})
        proc = self.repo.run("local_review.py")
        self.assertExit(proc, 0)
        self.assertIn("clean ->", proc.stdout)
        self.assertEqual([seen[1] for seen in _FakeChat.seen], ["m1"])


class LensSelectionTest(KitTestCase):

    def test_lenses_follow_file_types(self):
        self.in_repo()
        self.assertEqual(kit.lenses_for([]), ["common"])
        self.assertEqual(kit.lenses_for(["a/b.go", "README.md"]),
                         ["common", "go"])
        self.assertEqual(kit.lenses_for(["k.cu", "k.cuh", "x.proto"]),
                         ["common", "cpp", "cuda", "protobuf"])
        self.assertEqual(kit.lenses_for(["m.c", "m.h", "t.py", "u.ts"]),
                         ["common", "c", "cpp", "python", "typescript"])

    def test_kernel_tree_adds_the_kernel_lens(self):
        self.in_repo()
        self.assertEqual(kit.lenses_for(["drivers/net/x.c"]), ["common", "c"])
        for name in ("Kconfig", "MAINTAINERS"):
            self.repo.write(name, "x\n")
        self.assertEqual(kit.lenses_for(["drivers/net/x.c", "include/x.h"]),
                         ["common", "c", "kernel"])

    def test_setting_overrides_detection(self):
        self.in_repo()
        os.environ["REVIEWKIT_LENSES"] = "go, kernel"
        try:
            self.assertEqual(kit.lenses_for(["k.cu"]),
                             ["common", "go", "kernel"])
        finally:
            del os.environ["REVIEWKIT_LENSES"]


class InstallTest(KitTestCase):

    def install(self, repo_dir):
        return subprocess.run(["sh", os.path.join(HOOKS, "install.sh"),
                               repo_dir], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)

    def test_installs_three_hooks_and_they_run(self):
        proc = self.install(self.repo.path)
        self.assertExit(proc, 0)
        hooks = os.path.join(self.repo.path, ".git", "hooks")
        for name in ("pre-commit", "commit-msg", "pre-push"):
            path = os.path.join(hooks, name)
            self.assertTrue(os.stat(path).st_mode & stat.S_IXUSR, name)
            with open(path) as handle:
                self.assertIn("# review-kit hook", handle.read())
        self.assertEqual(self.repo.git("config", "reviewkit.home").strip(),
                         KIT)
        self.assertExit(self.install(self.repo.path), 0)

        self.repo.write("notes.txt", "x\n")
        self.repo.git("add", "notes.txt")
        bad = subprocess.run(
            ["git", "commit", "-q", "-m", "Add notes",
             "-m", "Co-authored-by: Copilot <bot@example.com>"],
            cwd=self.repo.path, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True)
        self.assertNotEqual(bad.returncode, 0)
        self.repo.git("commit", "-q", "-m", "Add notes")

    def test_honors_core_hooks_path(self):
        self.repo.git("config", "core.hooksPath", "custom-hooks")
        self.assertExit(self.install(self.repo.path), 0)
        self.assertTrue(os.path.isfile(os.path.join(
            self.repo.path, "custom-hooks", "pre-push")))

    def test_moves_a_foreign_hook_aside_and_chains_it(self):
        hooks = os.path.join(self.repo.path, ".git", "hooks")
        os.makedirs(hooks, exist_ok=True)
        for name in ("pre-commit", "pre-push"):
            with open(os.path.join(hooks, name), "w") as handle:
                handle.write("#!/bin/sh\necho mine-%s; cat >/dev/null\n"
                             % name)
        proc = self.install(self.repo.path)
        self.assertExit(proc, 0)
        self.assertIn("pre-commit.local", proc.stdout)
        with open(os.path.join(hooks, "pre-commit.local")) as handle:
            self.assertIn("echo mine-pre-commit", handle.read())
        with open(os.path.join(hooks, "pre-commit")) as handle:
            self.assertIn("# review-kit hook", handle.read())
        self.repo.write("notes.txt", "x\n")
        self.repo.git("add", "notes.txt")
        proc = subprocess.run(["git", "commit", "-q", "-m", "Add notes"],
                              cwd=self.repo.path, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)
        self.assertExit(proc, 0)
        self.assertIn("mine-pre-commit", proc.stdout + proc.stderr)
        # The chained pre-push gets git's stdin lines after the gate check.
        proc = subprocess.run(
            ["sh", os.path.join(hooks, "pre-push"), "origin", "url"],
            cwd=self.repo.path, input="", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True)
        self.assertExit(proc, 0)
        self.assertIn("mine-pre-push", proc.stdout)

    def test_refuses_when_a_foreign_hook_and_a_local_both_exist(self):
        hooks = os.path.join(self.repo.path, ".git", "hooks")
        os.makedirs(hooks, exist_ok=True)
        path = os.path.join(hooks, "pre-commit")
        with open(path, "w") as handle:
            handle.write("#!/bin/sh\necho mine\n")
        with open(path + ".local", "w") as handle:
            handle.write("#!/bin/sh\necho other\n")
        proc = self.install(self.repo.path)
        self.assertExit(proc, 1)
        self.assertIn(path, proc.stderr)
        with open(path) as handle:
            self.assertEqual(handle.read(), "#!/bin/sh\necho mine\n")
        self.assertFalse(os.path.exists(os.path.join(hooks, "commit-msg")))

    def test_hook_without_kit_fails_clearly(self):
        hook = os.path.join(HOOKS, "commit-msg")
        proc = subprocess.run(["sh", hook, "/nonexistent"],
                              cwd=self.repo.path, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)
        self.assertExit(proc, 1)
        self.assertIn("cannot find the kit", proc.stderr)


class SetupRepoTest(KitTestCase):

    def setup_repo(self, *args, cwd=None):
        return subprocess.run(["sh", os.path.join(HOOKS, "setup-repo.sh"),
                               *args], cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)

    def read_agents(self):
        with open(os.path.join(self.repo.path, "AGENTS.md")) as handle:
            return handle.read()

    def test_installs_hooks_and_writes_agents_md(self):
        proc = self.setup_repo(self.repo.path)
        self.assertExit(proc, 0)
        self.assertTrue(os.path.isfile(os.path.join(
            self.repo.path, ".git", "hooks", "pre-push")))
        self.assertEqual(self.repo.git("config", "reviewkit.home").strip(),
                         KIT)
        text = self.read_agents()
        self.assertTrue(text.startswith("# Instructions for coding agents"))
        self.assertNotIn("<kit>", text)
        self.assertNotIn("Copy this file", text)
        self.assertIn("## Before writing code", text)
        # Every kit path the agent is told to read or run exists.
        prefix = KIT + "/"
        paths = [word.strip("`.,:()")
                 for word in text.split() if prefix in word]
        self.assertTrue(paths)
        for path in paths:
            self.assertTrue(os.path.exists(path.rstrip("/")), path)

    def test_leaves_an_existing_agents_md_alone(self):
        self.repo.write("AGENTS.md", "# Ours\n")
        proc = self.setup_repo(self.repo.path)
        self.assertExit(proc, 0)
        self.assertEqual(self.read_agents(), "# Ours\n")
        self.assertIn("merge", proc.stdout)

    def test_points_out_a_claude_md(self):
        for name in ("CLAUDE.md", "CLAUDE.local.md"):
            self.repo.write(name, "# Claude\n")
        proc = self.setup_repo(self.repo.path)
        self.assertExit(proc, 0)
        for name in ("CLAUDE.md", "CLAUDE.local.md"):
            self.assertIn("reads %s instead of AGENTS.md" % name,
                          proc.stdout)

    def test_defaults_to_the_current_directory(self):
        proc = self.setup_repo(cwd=self.repo.path)
        self.assertExit(proc, 0)
        self.assertIn("## Before writing code", self.read_agents())

    def test_rejects_more_than_one_argument(self):
        proc = self.setup_repo(self.repo.path, self.repo.path)
        self.assertExit(proc, 2)
        self.assertIn("usage: setup-repo.sh [REPO_DIR]", proc.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo.path,
                                                     "AGENTS.md")))

    def test_rejects_a_directory_outside_git(self):
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside)
        proc = self.setup_repo(outside)
        self.assertExit(proc, 2)
        self.assertFalse(os.path.exists(os.path.join(outside, "AGENTS.md")))


if __name__ == "__main__":
    unittest.main()
