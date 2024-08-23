# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""

from threading import Thread, Lock
from time import sleep
from datetime import datetime

from kivy.app import App
from kivy.uix.settings import (
    Settings,
    SettingsWithTabbedPanel,
    SettingsWithSpinner,
    SettingsWithSidebar,
)
from kivy.logger import Logger, LOG_LEVELS
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.config import ConfigParser, Config

from lurchcal import create_task_appointments

from Task import Task

# <Row@Label>:
#     text_size: self.width, None
#     size_hint_y: None
#     height: self.texture_size[1]
#     font_size: dp(20)
#     halgin: left


# We first define our GUI
kv = """
BoxLayout:
    orientation: 'vertical'
    BoxLayout:
        size_hint: 1, .1
        Button:
            text: 'Create task list page'
            on_release: app.start_task_creation()
            id: create
        Button:
            text: 'Create task appointments'
            on_release: app.start_task_creation_appts()
            id: create_appts        
    Button:
        text: 'Configure app (or press F1)'
        size: self.texture_size
        size_hint: 1, .1
        on_release: app.open_settings()
    Label:
        id: label
        size: self.texture_size
        size_hint: 1, .1
        text: 'Progress:'
    ProgressBar:
        id: progress
        value: 0
        max: 6
        size_hint: 1, .1
    Label:
        size: self.texture_size
        size_hint: 1, .1
        text: 'Unscheduled tasks'        
    RecycleView:
        id: rv
        scroll_type: ['bars', 'content']
        scroll_wheel_distance: dp(114)
        bar_width: dp(10)
        viewclass: 'Label'
        RecycleBoxLayout:
            default_size: None, dp(56)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            spacing: dp(0)
"""


class LurchCalApp(App):
    def build(self):
        """
        Build and return the root widget.
        """
        self.settings_cls = SettingsWithSidebar

        self.tlock = Lock()
        self.parsed_config = {}

        # TBD self.icon = 'myicon.png'

        self.build_parsed_config()

        root = Builder.load_string(kv)
        return root

    def split(self, text, sep=","):
        try:
            split_text = text.split(",")
            return [part.strip() for part in split_text]
        except Exception as err:
            pass
        return []

    def read_time(self, time_str):
        try:
            res = datetime.strptime(time_str, "%H:%M")
            return res.time()
        except Exception as err:
            pass
        return datetime.strptime("12:00").time()

    def build_parsed_config(self):
        self.parsed_config["tag_order"] = self.split(
            self.config.get("tags", "tag_order")
        )
        self.parsed_config["tag_projects"] = self.split(
            self.config.get("tags", "tag_projects")
        )
        self.parsed_config["tag_ignore_appt"] = self.split(
            self.config.get("tags", "tag_ignore_appt")
        )
        self.parsed_config["tags_to_create_appt"] = self.split(
            self.config.get("tags", "tags_to_create_appt")
        )
        self.parsed_config["tags_future"] = self.split(
            self.config.get("tags", "tags_future")
        )

        self.parsed_config["lunch_break_time"] = self.read_time(
            self.config.get("appt", "lunch_break_time")
        )
        self.parsed_config["before_noon_break_time"] = self.read_time(
            self.config.get("appt", "before_noon_break_time")
        )
        self.parsed_config["start_of_day"] = self.read_time(
            self.config.get("appt", "start_of_day")
        )

    def build_config(self, config):
        """
        Set the default values for the configs sections.
        """
        config.setdefaults(
            "appt",
            {
                "min_task_len_4_appt": 15,
                "lunch_break": 30,
                "short_break": 15,
                "short_break_after_ilm": 1,
                "days_for_scheduling": 7,
                "lunch_break_time": "12:00",
                "before_noon_break_time": "10:00",
                "start_of_day": "9:00",
                "hours_per_day": 9,
            },
        )

        config.setdefaults(
            "tasks",
            {
                "def_task_len": 6,
                "min_task_split": 60,
            },
        )

        config.setdefaults(
            "tags",
            {
                "ilm": "ilm",
                "tag_order": "akquise, legal, mail",
                "tag_projects": "",
                # Text from summaries which can be ignored for tasks
                "tag_ignore_appt": "focus time, no ext.* appt.*, ^blocked$",
                "tags_to_create_appt": "appt",
                "tags_future": "future",
            },
        )

        # TBD File chooser, e.g. https://stackoverflow.com/questions/26028235/python-kivy-how-to-use-filechooser-access-files-outside-c-drive
        config.setdefaults(
            "zim",
            {
                "path_exe": "zim.exe",
                "path_wiki": "zim_wiki",
                "path_db": "c:\.db",
                "path_page": "c:\Geplante_Tasks.txt",
            },
        )

    def build_settings(self, settings):
        """
        Add our custom section to the default configuration object.
        """
        settings.add_json_panel(
            "LurchCal Settings", self.config, "settings_lurchcal.json"
        )

    def on_config_change(self, config, section, key, value):
        """
        Respond to changes in the configuration.
        """
        self.build_parsed_config()

        Logger.debug(
            "LurchCalApp.py: App.on_config_change: {0}, {1}, {2}, {3}".format(
                config, section, key, value
            )
        )

    def close_settings(self, settings=None):
        """
        The settings panel has been closed.
        """
        Logger.debug("LurchCalApp.py: App.close_settings: {0}".format(settings))
        super(LurchCalApp, self).close_settings(settings)

    def cb_update(self):
        progress = self.root.ids.progress
        progress.value = progress.value + 1

    def create_task_appointments_wrapper(self):
        with self.tlock:
            self.root.ids.create.disabled = True
            self.root.ids.create_appts.disabled = True
            progress = self.root.ids.progress
            progress.value = 0
            try:
                unscheduled_tasks = create_task_appointments(
                    self.cb_update, self.create_appts, self.config, self.parsed_config
                )

                self.root.ids.rv.data = [
                    {"text": str(t.description)} for t in unscheduled_tasks
                ]
            except Exception as err:
                self.root.ids.rv.data = [
                    {"text": "Exception raised!"},
                    {"text": str(err.hresult) + ", " + err.strerror},
                    {"text": "If error: -2147221005, Invalid class string: Outlook installed?"},
                ]

            sleep(1)
            self.root.ids.create.disabled = False
            self.root.ids.create_appts.disabled = False
            progress.value = 0

    def start_task_creation(self):
        Logger.debug("LurchCalApp.py: App.start_task_creation")
        try:
            self.create_appts = False
            Thread(target=self.create_task_appointments_wrapper).start()
        except Exception as err:
            Logger.exception("Exception", exc_info=err)

    def start_task_creation_appts(self):
        Logger.debug("LurchCalApp.py: App.start_task_creation_appts")
        try:
            self.create_appts = True
            Thread(target=self.create_task_appointments_wrapper).start()
        except Exception as err:
            Logger.exception("Exception", exc_info=err)


if __name__ == "__main__":
    config = ConfigParser()
    config.read("lurchal.ini")

    #    Logger.setLevel(LOG_LEVELS["warning"])

    Config.set("kivy", "exit_on_escape", "0")

    Window.size = (800, 600)
    LurchCalApp().run()
