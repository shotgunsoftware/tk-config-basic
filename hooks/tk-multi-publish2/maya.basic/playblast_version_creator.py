# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaPlayblastReviewPlugin(HookBaseClass):
    """
    Plugin for creating publishes for playblast quicktimes that exist on disk
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
        return self.parent.get_icon_path("shotgun")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Playblast Review"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return (
            "Publishes a maya playblast. After upload to SG, the playblast is "
            "deleted locally."
        )

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to recieve
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
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
        return ["maya.playblast"]

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

        if "path" not in item.properties:
            log.error("Unknown file path for maya playblast.")
            return {"accepted": False}

        return {"accepted": True, "required": False, "enabled": True}

    def validate(self, log, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity. Use the logger to output further details
        around why validation has failed.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        return True

    def publish(self, log, settings, item):
        """
        Executes the publish logic for the given item and settings. Use the
        logger to give the user status updates.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        path = item.properties["path"]

        publisher = self.parent

        file_info = publisher.util.get_file_path_components(path)
        filename_no_ext = file_info["filename_no_ext"]

        version_data = {
            "project": item.context.project,
            "code": "Maya Playblast %s" % filename_no_ext.capitalize(),
            "description": item.description,
            "entity": self._get_version_entity(item)
        }

        # see if the parent has been published, and if so, attach it as a linked
        # published file
        parent_publish_data = item.parent.properties.get("sg_publish_data")
        if parent_publish_data:
            published_file = {
                "type": "PublishedFile",
                "id": parent_publish_data["id"]
            }
            version_data["published_files"] = [published_file]

        # create the version entry
        log.info("Creating version for review...")
        log.debug("Version data: %s" % (version_data,))
        version = self.parent.shotgun.create("Version", version_data)

        # upload the the movie
        log.info("Uploading content...")
        self.parent.shotgun.upload(
            "Version",
            version["id"],
            item.properties["path"],
            "sg_uploaded_movie"
        )

    def finalize(self, log, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # remove the source path
        path = item.properties["path"]
        log.info("Deleting %s" % item.properties["path"])
        sgtk.util.filesystem.safe_delete_file(path)

    def _get_version_entity(self, item):
        """
        Returns the best entity to link the version to.
        """

        if item.context.task:
            return item.context.task
        elif item.context.entity:
            return item.context.entity
        elif item.context.project:
            return item.context.project
        else:
            return None
