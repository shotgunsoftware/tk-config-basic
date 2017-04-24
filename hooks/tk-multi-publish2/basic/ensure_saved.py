# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class EnsureSavedPlugin(HookBaseClass):
    """
    Abstract plugin hook for ensuring the current DCC session is saved.
    Subclasses must implement the DCC-specific properties in order for publish
    phase methods to function properly.
    """

    @property
    def session_path(self):
        """
        The path to the current session on disk. Can be ``None`` if the session
        has not been saved.
        """
        raise NotImplementedError(
            "Subclass plugin hook has not defined the 'session_path' property.")

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "save.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Ensure Session Saved"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        This plugin will ensure the current session is saved.
        """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        return {}

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        raise NotImplementedError(
            "Subclass plugin hook has not defined the 'item_filters' property.")

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        if self.has_unsaved_changes or not self.session_path:
            # the session has unsaved changes. provide a save button. the
            # session will need to be saved before validation will succeed.
            self.logger.warn(
                "Unsaved changes in the session",
                extra=self._get_save_as_action()
            )

        self.logger.info(
            "Ensure saved plugin accepted the current session.")
        return {
            "accepted": True,
            "checked": True,
            "enabled": False   # can't un-check this one. save is required.
        }

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        if self.has_unsaved_changes or not self.session_path:
            # the session still requires saving. provide a save button.
            # validation fails since we don't want to save as the next version
            # until the current changes have been saved.
            self.logger.error(
                "Unsaved changes in the session",
                extra=self._get_save_as_action()
            )
            return False

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        # TODO: auto save setting?
        pass

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        pass

    def session_save_as(self):
        """
        Abstract method to save the current session.
        :return: Returns the path to the saved file
        """
        raise NotImplementedError(
            "Subclass plugin hook has not defined the 'session_path' property.")

    def _get_save_as_action(self):
        """
        Simple helper for returning a log action dict for saving the session
        """
        return {
            "action_button": {
                "label": "Save",
                "tooltip": "Save the current session",
                "callback": self.session_save_as
            }
        }
