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
import pprint
import tempfile
import uuid
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopReviewPlugin(HookBaseClass):
    """
    Plugin for sending photoshop documents to shotgun for review.
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
            "review.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Send document to Shotgun review"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        This plugin exports and uploads a jpg copy of the Photoshop document to
        Shotgun for review.
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

        # we use "video" since that's the mimetype category.
        return ["photoshop.document"]

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

        document = item.properties.get("document")
        if not document:
            self.logger.warn("Could not determine the document for item")
            return {"accepted": False}

        try:
            path = document.fullName.fsName
        except RuntimeError:
            path = None

        checked = True

        if not document.saved or not path:
            # the document hasn't been saved. provide a save button and uncheck
            # the item. the document will need to be saved before validation
            # will succeed.
            self.logger.warn(
                "Unsaved changes for document: %s" % (document.name,),
                extra=_get_save_action(document)
            )
            checked = False

        self.logger.info(
            "Photoshop Version upload plugin accepted document: %s" %
            (document.name,)
        )
        return {
            "accepted": True,
            "checked": checked
        }

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        document = item.properties["document"]
        path = document.fullName.fsName

        if not document.saved or not path:
            # the document still hasn't been saved. provide a save button.
            # validation fails since we don't want to save as the next version
            # until the current changes have been saved.
            self.logger.error(
                "Unsaved changes in the session",
                extra=_get_save_action(document)
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

        publisher = self.parent
        engine = publisher.engine
        document = item.properties["document"]

        with engine.context_changes_disabled():

            # remember the active document so that we can restore it.
            previous_active_document = engine.adobe.app.activeDocument

            # make the document being processed the active document
            engine.adobe.app.activeDocument = document

            # path to a temp jpg file
            jpg_path = os.path.join(
                tempfile.gettempdir(),
                "%s_sgtk.jpg" % uuid.uuid4().hex
            )

            # jpg file/options
            jpg_file = engine.adobe.File(jpg_path)
            jpg_options = engine.adobe.JPEGSaveOptions
            jpg_options.quality = 12

            # save a jpg copy of the document
            document.saveAs(jpg_file, jpg_options, True)

            # restore the active document
            engine.adobe.app.activeDocument = previous_active_document

        # use the original path for the version display name
        path = document.fullName.fsName
        publish_name = publisher.util.get_publish_name(path)

        # populate the version data to send to SG
        self.logger.info("Creating Version...")
        version_data = {
            "project": item.context.project,
            "code": publish_name,
            "description": item.description,
            "entity": self._get_version_entity(item)
        }

        publish_data = item.properties.get("sg_publish_data")

        # if the file was published, add the publish data to the version
        if publish_data:
            version_data["published_files"] = [publish_data]

        # log the version data for debugging
        self.logger.debug(
            "Populated Version data...",
            extra={
                "action_show_more_info": {
                    "label": "Version Data",
                    "tooltip": "Show the complete Version data dictionary",
                    "text": "<pre>%s</pre>" % (
                    pprint.pformat(version_data),)
                }
            }
        )

        # create the version
        self.logger.info("Creating version for review...")
        version = self.parent.shotgun.create("Version", version_data)

        # stash the version info in the item just in case
        item.properties["sg_version_data"] = version

        # upload the jpg copy to SG
        self.logger.info("Uploading content...")
        self.parent.shotgun.upload(
            "Version",
            version["id"],
            jpg_path,
            "sg_uploaded_movie"
        )
        self.logger.info("Upload complete!")

        # go ahead and update the publish thumbnail (if there was one)
        if publish_data:
            self.logger.info("Updating publish thumbnail...")
            self.parent.shotgun.upload_thumbnail(
                publish_data["type"],
                publish_data["id"],
                jpg_path
            )
            self.logger.info("Publish thumbnail updated!")

        item.properties["jpg_path"] = jpg_path

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        version = item.properties["sg_version_data"]

        self.logger.info(
            "Verison uploaded for photoshop document",
            extra={
                "action_show_in_shotgun": {
                    "label": "Show Version",
                    "tooltip": "Reveal the version in Shotgun.",
                    "entity": version
                }
            }
        )

        jpg_path = item.properties["jpg_path"]

        # remove the tmp file
        try:
            os.remove(jpg_path)
        except Exception:
            self.logger.warn("Unable to remove temp file: %s" % (jpg_path,))
            pass

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


def _get_save_action(document):
    """
    Simple helper for returning a log action dict for saving the session
    """
    return {
        "action_button": {
            "label": "Save",
            "tooltip": "Save the current session",
            "callback": lambda: document.save()
        }
    }