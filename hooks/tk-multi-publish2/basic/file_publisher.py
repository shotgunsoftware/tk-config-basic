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

HookBaseClass = sgtk.get_hook_baseclass()


class GenericFilePublishPlugin(HookBaseClass):
    """
    Plugin for creating generic publishes in Shotgun
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

        if self._get_matching_publish_type(extension, settings):
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

        # get the would-be publish name for this path.
        path_info = publisher.util.get_file_path_components(path)
        publish_name = self._get_display_name(path_info)

        # see if there are any other publishes of this path. Note the name,
        # context, and path *must* match the values supplied to register_publish
        # in the publish phase in order for this to return an accurate list of
        # previous publishes of this file.
        publishes = publisher.util.get_publishes(
            item.context,
            path,
            publish_name
        )

        if publishes:
            log.warn(
                "Found %s publishes in Shotgun with the path '%s'. If you "
                "continue, these other publishes will no longer be available "
                "to other users." % (len(publishes), path)
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
        publish_type = self._get_matching_publish_type(extension, settings)

        display_name = self._get_display_name(path_info)

        # arguments for publish registration
        args = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": path,
            "name": display_name,
            "version_number": path_info["version"],
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

        # ensure other publishes have their status cleared
        log.info("Clearing status of previous publishes...")
        publisher.util.clear_status_for_other_publishes(
            item.context, publish_data)

        # auto version the file if the setting is enabled and a version exists
        # in the file name. bump the version number by 1
        path_info = publisher.util.get_file_path_components(path)
        if settings["Auto Version"].value and path_info["version"]:
            new_version = path_info["version"] + 1
            log.info("Bumping the version to %s..." % (new_version,))
            publisher.util.copy_path_to_version(
                path,
                new_version,
                padding=path_info["version_padding"]
            )

    def _get_matching_publish_type(self, extension, settings):
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

    def _get_display_name(self, path_info):
        """
        Convenience method to ensure returned display name is consistent when
        doing validation as well as actually creating a publish.

        :param path_info: A dictionary of the form returned by the publisher's
            util.get_file_path_components()

        :return: A display name for the given path info
        """

        path = path_info["path"]
        if os.path.isdir(path):
            display_name = path_info["filename"]
        else:
            display_name = "%s.%s" % (path_info["prefix"], path_info["extension"])

        return display_name