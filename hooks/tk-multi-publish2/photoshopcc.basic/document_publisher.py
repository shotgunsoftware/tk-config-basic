# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import glob
import os
import re

import sgtk
from sgtk.util.filesystem import ensure_folder_exists, copy_file

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopCCDocumentPublishPlugin(HookBaseClass):
    """
    Plugin for publishing Photoshop documents in Shotgun.
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
        return os.path.join(self.disk_location, "icons", "shotgun.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish PS Document to Shotgun"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This
        can contain simple html for formatting.
        """
        return """
        Publishes Photoshop documents to shotgun.
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
        return {}

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.
        Only items matching entries in this list will be presented
        to the accept() method. Strings can contain glob patters
        such as *, for example ["maya.*", "file.maya"]
        """
        return ["photoshop.document"]

    def accept(self, log, settings, item):
        """
        Method called by the publisher to determine if an item
        is of any interest to this plugin. Only items matching
        the filters defined via the item_filters property will
        be presented to this method.

        A publish task will be generated for each item accepted
        here. Returns a dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in
                        this value at all.
            - required: If set to True, the publish task is
                        required and cannot be disabled.
            - enabled:  If True, the publish task will be
                        enabled in the UI by default.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching the keys
            returned in the settings property. The values are `Setting` instances.
        :param item: Item to process
        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # ensure there is a document in the item properties
        if not "document" in item.properties:
            return {"accepted": False}

        return {"accepted": True, "required": False, "enabled": True}

    def validate(self, log, settings, item):
        """
        Validates the given item to check that it is ok to publish.
        Returns a boolean to indicate validity. Use the logger to
        output further details around why validation has failed.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching the keys
            returned in the settings property. The values are `Setting` instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        document = item.properties["document"]
        if not document.saved:
            log.error("Document '%s' not saved." % (document.name))
            return False

        return True

    def publish(self, log, settings, item):
        """
        Executes the publish logic for the given
        item and settings. Use the logger to give
        the user status updates.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching the keys
            returned in the settings property. The values are `Setting` instances.
        :param item: Item to process
        """

        document = item.properties["document"]

        # should be saved if we're here
        path = os.path.abspath(document.fullName.fsName)

        # prepares the file for publishing and returns publish path components
        file_info = self._prepare_for_publish(path)

        # determine the publish type
        extension = file_info["extension"]

        # Create the TankPublishedFile entity in Shotgun
        # note - explicitly calling
        args = {
            "tk": self.parent.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": file_info["path"],
            "name": "%s.%s" % (file_info["prefix"], extension),
            "version_number": file_info["version"],
            "thumbnail_path": None,  # TODO: revisit
            "published_file_type": extension,
        }

        sg_data = sgtk.util.register_publish(**args)

        item.properties["shotgun_data"] = sg_data
        item.properties["shotgun_publish_id"] = sg_data["id"]

    def finalize(self, log, settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching the keys
            returned in the settings property. The values are `Setting` instances.
        :param item: Item to process
        """
        pass

    def _prepare_for_publish(self, path):
        """
        Convenience method used to prep the file for publish.

        Returns info for the path to publish. Makes a snapshot of the file
        in a ``publish`` folder next to the file's source location. The snapshot
        is the path that will be published.

        :param str path: The path to the file to publish.

        Returns publish file path info of the form::

            # source path is "/path/to/the/file/my_file.ext"
            {
                "path": "/path/to/the/file/publish/my_file.v0001.ext",
                "directory": "/path/to/the/file/publish",
                "filename": "my_file.v0001.ext",
                "filename_no_ext": "my_file.v0001",
                "prefix": "my_file",
                "version_str": "v0001",
                "version": 1,
                "extension": "ext"
            }

        """

        # extract the basic path components from the source path
        (source_directory, source_filename) = os.path.split(
            os.path.abspath(path)
        )
        (prefix, extension) = os.path.splitext(source_filename)

        # remove the dot from the extension
        extension = extension.lstrip(".")

        # construct the publish directory
        publish_directory = os.path.join(source_directory, "publish")

        # ensure the publish directory exists
        ensure_folder_exists(publish_directory)

        # get the next version to use for publishing
        version = self._get_next_version(
            publish_directory,
            prefix,
            extension
        )

        # formatted strings
        version_str = "v%04d" % (version,)
        filename_no_ext = "%s.%s" % (prefix, version_str)
        filename = "%s.%s" % (filename_no_ext, extension)
        publish_path = os.path.join(publish_directory, filename)

        # copy the source file to the publish path
        copy_file(path, publish_path)

        # return a dictionary of info about the file to be published
        return dict(
            path=publish_path,
            directory=publish_directory,
            filename=filename,
            filename_no_ext=filename_no_ext,
            prefix=prefix,
            version_str=version_str,
            version=version,
            extension=extension,
        )

    def _get_next_version(self, folder, prefix, extension):
        """
        Examines the supplied folder for files matching:

            <prefix>.v####.<extension>

        Determines the next available version number and returns it as an int.
        """

        # start with a list of 0. if there are not matching files, then the
        # max will be 0, making the next available version 1.
        versions = [0]

        # build the full glob pattern
        file_pattern = "%s.v*.%s" % (prefix, extension)
        glob_pattern = os.path.join(folder, file_pattern)

        # similarly, build a regex pattern to extract the version number from
        # matched files
        regex_pattern = re.compile(
            "%s.v(\d+)\.%s" % (prefix, extension)
        )

        # extract the version from the pattern match
        for previous_version in glob.glob(glob_pattern):
            match = re.search(regex_pattern, previous_version)
            version = int(match.group(1))
            versions.append(version)

        return max(versions) + 1
