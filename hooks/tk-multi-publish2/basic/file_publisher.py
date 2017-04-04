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
from sgtk.util.filesystem import copy_file, copy_folder

HookBaseClass = sgtk.get_hook_baseclass()


class BasicFilePublishPlugin(HookBaseClass):
    """
    Plugin for creating generic publishes in Shotgun
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
        config_path = self.parent.sgtk.pipeline_configuration.get_path()
        return os.path.join(config_path, "config", "icons", "publish.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish files to Shotgun"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        Publishes files/folders to shotgun. Supports any file or folder type
        if the "Publish all file types" setting is <tt>True</tt>, otherwise
        limited by the extensions in the "File Types" setting.

        This plugin will recognize version numbers of the form <tt>.v###</tt>
        in the file or folder name and will publish with that version number to
        Shotgun. If the "Auto Version" setting is <tt>True</tt>, the plugin will
        automatically copy thie file/folder to the next version number after
        publishing.
        """

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
        return {
            "File Types": {
                "type": "list",
                "default": "[]",
                "description": (
                    "List of file types to include. Each entry in the list "
                    "is a list in which the first entry is the Shotgun "
                    "published file type and subsequent entries are file "
                    "extensions that should be associated.")
            },
            "Publish all file types": {
                "type": "bool",
                "default": False,
                "description": (
                    "If set to True, all files will be published, even if "
                    "their extension has not been declared in the file types "
                    "setting.")
            },
            "Auto Version": {
                "type": "bool",
                "default": True,
                "description": (
                    "If set to True, the file will be automatically saved to "
                    "the next version after publish."
                )
            },
            # TODO: revisit default states for settings ^
        }

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["file.*"]

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

        publisher = self.parent

        path = item.properties["path"]
        path_info = publisher.util.get_file_path_components(path)
        extension = path_info["extension"]

        if self._get_publish_type(extension, settings):
            return {"accepted": True, "required": False, "enabled": True}
        else:
            return {"accepted": False}

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

        publisher = self.parent
        path = item.properties.get("path")
        if not path:
            log.error("Unknown path for item.")
            return False

        # get the publish name for this file path. this will ensure we get a
        # consistent publish name when looking up existing publishes.
        publish_name = publisher.execute_hook_method(
            "path_info",
            "get_publish_name",
            path=path
        )

        log.info("Publish name will be: %s" % (publish_name,))

        # see if there are any other publishes of this path with a status.
        # Note the name, context, and path *must* match the values supplied to
        # register_publish in the publish phase in order for this to return an
        # accurate list of previous publishes of this file.
        publishes = publisher.util.get_conflicting_publishes(
            item.context,
            path,
            publish_name,
            filters=["sg_status_list", "is_not", None]
        )

        if publishes:
            log.warn(
                "Found %s conflicting publishes in Shotgun with the path '%s'. "
                "If you continue, these conflicting publishes will no longer "
                "be available to other users via the loader." %
                (len(publishes), path)
            )

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

        path = item.properties["path"]
        publisher = self.parent

        # get the publish path components
        path_info = publisher.util.get_file_path_components(path)

        # determine the publish type
        extension = path_info["extension"]

        # get the publish type
        publish_type = self._get_publish_type(extension, settings)

        # get the publish name for this file path. this will ensure we get a
        # consistent name across version publishes of this file.
        publish_name = publisher.execute_hook_method(
            "path_info",
            "get_publish_name",
            path=path
        )

        # extract the version number for publishing. use 1 if no version in path
        version_number = publisher.execute_hook_method(
            "path_info", "get_version_number", path=path) or 1

        # arguments for publish registration
        args = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": path,
            "name": publish_name,
            "version_number": version_number,
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": publish_type,
        }
        log.debug("Publishing: %s" % (args,))

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties["sg_publish_data"] = sgtk.util.register_publish(**args)

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

        publisher = self.parent
        path = item.properties["path"]

        # get the data for the publish that was just created in SG
        publish_data = item.properties["sg_publish_data"]

        # ensure conflicting publishes have their status cleared
        log.info("Clearing status of conflicting publishes...")
        publisher.util.clear_status_for_conflicting_publishes(
            item.context, publish_data)

        if not settings["Auto Version"].value:
            return

        log.info("Auto versioning path: %s ..." % (path,))

        # if we're here, auto version was requested. get the path to the next
        # version.
        next_version_path = publisher.execute_hook_method(
            "path_info",
            "get_next_version_path",
            path=path
        )

        if not next_version_path:
            log.warn("Could not determine next version path for: %s" % (path,))
            return

        if os.path.exists(next_version_path):
            log.warn("Path already exists: %s" % (next_version_path,))
            return

        # if here, all good to copy the file/folder.
        if os.path.isdir(path):
            # folder
            copy_folder(path, next_version_path)
        else:
            # file
            copy_file(path, next_version_path)

        log.info("Copied published path to: %s ..." % (next_version_path,))

    def _get_publish_type(self, extension, settings):
        """
        Get a publish type for the supplied extension and publish settings.

        :param extension: The file extension to find a publish type for
        :param settings: The publish settings defining the publish types

        :return: A publish type or None if one could not be found.
        """

        # ensure lowercase and no dot
        if extension:
            extension = extension.lstrip(".").lower()

            for type_def in settings["File Types"].value:

                publish_type = type_def[0]
                file_extensions = type_def[1:]

                if extension in file_extensions:
                    # found a matching type in settings. use it!
                    return publish_type

        if settings["Publish all file types"].value:
            # we're publishing anything and everything!

            if extension:
                # publish type is based on extension
                publish_type = "%s File" % extension.capitalize()
            else:
                # no extension, assume it is a folder
                publish_type = "Folder"

            return publish_type

        # no publish type identified!
        return None
