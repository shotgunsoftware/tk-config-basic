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
import os

from sgtk.util.filesystem import ensure_folder_exists, copy_file

HookBaseClass = sgtk.get_hook_baseclass()


class HoudiniFilePublishPlugin(HookBaseClass):
    """
    Plugin for publishing a houdini file
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
        return self.parent.get_icon_path("publish")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish Houdini File"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return (
            "Publishes a houdini file."
        )

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
        return {
            "Publish Type": {
                "type": "shotgun_publish_type",
                "default": "Houdini File",
                "description": "SG publish type to associate publishes with."
            },
        }

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["houdini.file"]

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
        if item.properties["path"] is None:
            # TODO: try to get path here in order to allow saving while
            # the publisher is open
            log.error("Please save your scene before you continue!")
            return False

        # ensure the publish destination is created and that we can determine
        # the next available publish version. We do this before the actual
        # publish and before creating the version directory so that multiple
        # documents from the same folder being published at the same time can
        # share the same version number. this keeps a close association between
        # files published from the same work area. we don't wait until the
        # publish phase to determine the version because it would mean each
        # file being published would bump the version independently.

        log.info("Validating publish folder and version...")
        publisher = self.parent

        path = item.properties["path"]
        file_info = publisher.util.get_file_path_components(path)

        # ensure the publish folder exists
        publish_folder = os.path.join(file_info["folder"], "publish")
        log.debug("Ensuring publish folder exists: '%s'" % (publish_folder,))
        ensure_folder_exists(publish_folder)

        # get the next available version within the publish folder
        publish_version = publisher.util.get_next_version_folder(publish_folder)

        # add publish version and publish version folder to the item properties.
        item.properties["publish_folder"] = publish_folder
        item.properties["publish_version"] = publish_version

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

        publisher = self.parent

        path = item.properties["path"]
        file_info = publisher.util.get_file_path_components(path)

        # retrieve the publish folder and version populated during validation
        publish_folder = item.properties["publish_folder"]
        publish_version = item.properties["publish_version"]

        # build the path to the next available version subfolder that we will
        # copy the source file to and publish from
        publish_version_folder = os.path.join(
            publish_folder,
            "v%03d" % (publish_version,)
        )

        ensure_folder_exists(publish_version_folder)

        # get the full destination path for the file to publish
        publish_path = os.path.join(
            publish_version_folder,
            file_info["filename"]
        )

        # copy the source file to the new destination
        log.info("Copying to publish folder: %s" % (publish_version_folder,))
        copy_file(path, publish_path)

        # update the file info for the new publish path
        file_info = publisher.util.get_file_path_components(publish_path)

        # determine the publish type
        extension = file_info["extension"]

        # Create the TankPublishedFile entity in Shotgun
        # note - explicitly calling
        args = {
            "tk": self.parent.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": publish_path,
            "name": "%s.%s" % (file_info["prefix"], extension),
            "version_number": publish_version,
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": settings["Publish Type"].value,
        }
        log.debug("Publishing: %s" % (args,))

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties["sg_publish_data"] = sgtk.util.register_publish(**args)

        # add the full path to the publish version folder to the item properties
        item.properties["publish_version_folder"] = publish_version_folder

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
        pass

