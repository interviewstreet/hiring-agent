import json
import os
import shutil
import stat
import tempfile
import unittest

from models import CliLLMProvider, ModelProvider


class CliLLMProviderSmokeTests(unittest.TestCase):
    def _fake_cli(self, stdout: str) -> str:
        temp_dir = tempfile.mkdtemp(prefix="cli_provider_smoke_")
        script_path = os.path.join(temp_dir, "fake_cli")
        with open(script_path, "w", encoding="utf-8") as script:
            script.write("#!/bin/sh\n")
            script.write("cat >/dev/null\n")
            script.write(f"printf '%s' {json.dumps(stdout)}\n")
        os.chmod(
            script_path,
            os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )
        self.addCleanup(lambda: os.path.exists(temp_dir) and shutil.rmtree(temp_dir))
        return script_path

    def test_claude_code_structured_output_envelope_is_unwrapped(self):
        command = self._fake_cli('{"structured_output":{"name":"Ada"}}')
        provider = CliLLMProvider(
            backend=ModelProvider.CLAUDE_CODE.value,
            command=command,
        )

        response = provider.chat(
            model="claude-code",
            messages=[{"role": "user", "content": "Return a name."}],
            format={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )

        self.assertEqual(json.loads(response["message"]["content"]), {"name": "Ada"})

    def test_codex_structured_output_accepts_raw_json(self):
        command = self._fake_cli('{"name":"Ada"}')
        provider = CliLLMProvider(
            backend=ModelProvider.CODEX.value,
            command=command,
        )

        response = provider.chat(
            model="codex-cli",
            messages=[
                {"role": "system", "content": "Only return JSON."},
                {"role": "user", "content": "Return a name."},
            ],
            format={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )

        self.assertEqual(json.loads(response["message"]["content"]), {"name": "Ada"})


if __name__ == "__main__":
    unittest.main()
