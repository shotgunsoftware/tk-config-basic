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


class PhotoshopVersionUpPlugin(HookBaseClass):
    """
    Plugin for creating the next version of a file.
    """

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
            "version_up.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Save the file to the next version"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        Detect the version number in the photoshop document path and save it to
        the next available version number. The plugin will only be available to
        photoshop documents where a version number can be detected in the path.
        The plugin will only create the next available version if the new path
        does not already exist.
        """

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["photoshop.document"]

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

    def accept(self, log, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                        all.
            - required: If set to True, the publish task is required and cannot
                        be disabled.
            - enabled:  If True, the publish task will be enabled in the UI by
                        default.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        document = item.properties["document"]
        if not document.saved:
            log.error("Document '%s' has not been saved." % (document.name,))
            return {"accepted": False}

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(
            os.path.abspath(document.fullName.fsName))

        publisher = self.parent

        # can't version up if we don't know the path
        if not path:
            return {"accepted": False}

        version_number = publisher.util.get_version_number(path)
        if version_number is None:
            # no version number detected in the file name
            return {"accepted": False}

        return {"accepted": True, "required": False, "enabled": True}

    def validate(self, log, settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity. Use the logger to output further
        details around why validation has failed.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        document = item.properties["document"]

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(
            os.path.abspath(document.fullName.fsName))

        if not path:
            log.error("Session is not saved.")
            return False

        publisher = self.parent
        next_version_path = publisher.util.get_next_version_path(path)

        # nothing to do if the next version path can't be determined or if it
        # already exists.
        if not next_version_path:
            log.error("Could not determine the next version path.")
            return False
        elif os.path.exists(next_version_path):
            log.error("The next version of the path already exists")
            return False

        # insert the path into the properties for use during the publish phase
        item.properties["next_version_path"] = next_version_path

        return True

    def publish(self, log, settings, item):
        """
        Executes the publish logic for the given item and settings.

        Use the logger to give the user status updates.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        engine = self.parent.engine
        document = item.properties["document"]

        # remember the active document so that we can restore it.
        self._active_document = engine.adobe.app.activeDocument

        # make the document being processed the active document
        engine.adobe.app.activeDocument = document

        # get the next version path and save the document
        next_version_path = item.properties["next_version_path"]
        document.saveAs(engine.adobe.File(next_version_path))
        log.info("Saved to: %s" % (next_version_path,))

    def finalize(self, log, settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # restore the active document if need be
        if hasattr(self, '_active_document'):
            engine = self.parent.engine
            engine.adobe.app.activeDocument = self._active_document
