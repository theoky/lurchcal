# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""Unit tests for TaskParser using deterministic Zim fixtures."""

import tempfile
import unittest
from pathlib import Path

from kivy.config import ConfigParser

from lurchcal.TaskParser import TaskParser

from tests.zim_test_utils import initialize_zim_sqlite


class TestTaskParserWithZimFixture(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "fixture_zim.sqlite"
        initialize_zim_sqlite(self.db_path)

        self.config = ConfigParser()
        self.config.add_section("tasks")
        self.config.set("tasks", "def_task_len", "30")
        self.config.set("tasks", "min_task_split", "60")
        self.parser = TaskParser(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_zim_tasks_splits_and_filters(self):
        tasks = self.parser.parse_zim_tasks(str(self.db_path))
        descriptions = [task.description for task in tasks]

        self.assertEqual(
            descriptions,
            [
                "Write summary",
                "st: Long Focus Task ~2h~ @Deep",
                "Long Focus Task ~2h~ @Deep",
            ],
        )

        self.assertEqual([task.duration for task in tasks], [30, 60, 60])
        self.assertEqual([task.subid for task in tasks], [0, 1, 0])

        for task in tasks:
            self.assertEqual(task.source_name, "Work")
            self.assertNotIn("Waiting Task", task.description)

        deep_tags = [task.tags for task in tasks[1:]]
        self.assertTrue(all(tag_list == ["deep"] for tag_list in deep_tags))

    def test_parse_task_description_from_fixture(self):
        description = "Long Focus Task ~2h~a @Deep"
        duration, is_default, assign_duration, tags = self.parser.parse_task_description(description)

        self.assertEqual(duration, 120)
        self.assertFalse(is_default)
        self.assertTrue(assign_duration)
        self.assertEqual(tags, ["deep"])


if __name__ == "__main__":
    unittest.main()
