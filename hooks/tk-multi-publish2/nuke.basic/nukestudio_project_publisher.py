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
import traceback
import sgtk
from sgtk.platform.qt import QtGui

HookBaseClass = sgtk.get_hook_baseclass()


class NukeStudioProjectPublishPlugin(HookBaseClass):
    """
    Plugin for publishing a Nuke Studio project.
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
            "publish.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Nuke Studio Project Publisher"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        This plugin will publish an open Nuke Studio project. The plugin
        requires the project be saved to a file before validation will succeed.
        The file will be published in place.
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
        return {
            "Publish Type": {
                "type": "shotgun_publish_type",
                "default": "NukeStudio Project",
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
        return ["nukestudio.project"]

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

        project = item.properties.get("project")
        if not project:
            self.logger.warn("Could not determine the project.")
            return {"accepted": False}

        path = project.path()
        checked = True

        if not path:
            # the project hasn't been saved. provide a save button and uncheck
            # the item. the project will need to be saved before validation will
            # succeed.
            self.logger.warn(
                "Unsaved changes in the session",
                extra=_get_save_as_action(project)
            )
            checked = False

        self.logger.info(
            "Nuke Studio plugin accepted project: %s." % (project.name(),))
        return {
            "accepted": True,
            "checked": checked
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

        publisher = self.parent
        project = item.properties.get("project")
        path = project.path()

        if not path:
            # the project still hasn't been saved. provide a save button.
            # validation fails since we don't want to save as the next version
            # until the current changes have been saved.
            self.logger.error(
                "Unsaved changes in the session",
                extra=_get_save_as_action(project)
            )
            return False

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(path)

        # get the publish name for this file path. this will ensure we get a
        # consistent publish name when looking up existing publishes.
        publish_name = publisher.util.get_publish_name(path)

        self.logger.info("Publish name will be: %s" % (publish_name,))

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
            conflict_info = (
                "If you continue, these conflicting publishes will no longer "
                "be available to other users via the loader:<br>"
                "<pre>%s</pre>" % (pprint.pformat(publishes),)
            )
            self.logger.warn(
                "Found %s conflicting publishes in Shotgun" %
                (len(publishes),),
                extra={
                    "action_show_more_info": {
                        "label": "Show Conflicts",
                        "tooltip": "Show the conflicting publishes in Shotgun",
                        "text": conflict_info
                    }
                }
            )

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
        project = item.properties.get("project")

        # there doesn't appear to be a way to determine if the project has
        # unsaved changes. at least if we're here we have a path. so go ahead
        # and force the save.
        try:
            self.logger.debug("Saving project: %s" % (project.name(),))
            project.save()
        except Exception, e:
            error_msg = traceback.format_exc()
            self.logger.error(
                "Failed to save project: '%s'" % (project.name(),),
                extra={
                    "action_show_more_info": {
                        "label": "Error Details",
                        "tooltip": "Show the full error tack trace",
                        "text": "<pre>%s</pre>" % (error_msg,)
                    }
                }
            )
            return

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(project.path())

        # get the publish name for this file path. this will ensure we get a
        # consistent name across version publishes of this file.
        publish_name = publisher.util.get_publish_name(path)

        # extract the version number for publishing. use 1 if no version in path
        version_number = publisher.util.get_version_number(path) or 1

        # arguments for publish registration
        self.logger.info("Registering publish...")
        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": path,
            "name": publish_name,
            "version_number": version_number,
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": settings["Publish Type"].value,
        }

        # log the publish data for debugging
        self.logger.debug(
            "Populated Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Publish Data",
                    "tooltip": "Show the complete Publish data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(publish_data),)
                }
            }
        )

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties["sg_publish_data"] = sgtk.util.register_publish(
            **publish_data)
        self.logger.info("Publish registered!")

        # now that we've published. keep a handle on the path that was published
        item.properties["path"] = path

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # get the data for the publish that was just created in SG
        publish_data = item.properties["sg_publish_data"]

        # ensure conflicting publishes have their status cleared
        publisher.util.clear_status_for_conflicting_publishes(
            item.context, publish_data)

        self.logger.info(
            "Cleared the status of all previous, conflicting publishes")

        path = item.properties["path"]
        self.logger.info(
            "Publish created for file: %s" % (path,),
            extra={
                "action_show_in_shotgun": {
                    "label": "Show Publish",
                    "tooltip": "Open the Publish in Shotgun.",
                    "entity": publish_data
                }
            }
        )


def _get_save_as_action(project):
    """
    Simple helper for returning a log action dict for saving the session
    """
    return {
        "action_button": {
            "label": "Save",
            "tooltip": "Save the current session",
            "callback": lambda: _project_save_as(project)
        }
    }


def _project_save_as(project):
    """
    A save as wrapper for the current session.

    :param path: Optional path to save the current session as.
    """

    # TODO: consider moving to engine

    import hiero

    # nuke studio/hiero don't appear to have a "save as" dialog accessible via
    # python. so open our own Qt file dialog.
    file_dialog = QtGui.QFileDialog(
        parent=hiero.ui.mainWindow(),
        caption="Save As",
        directory=project.path(),
        filter="Nuke Studio Files (*.hrox)"
    )
    file_dialog.setLabelText(QtGui.QFileDialog.Accept, "Save")
    file_dialog.setLabelText(QtGui.QFileDialog.Reject, "Cancel")
    file_dialog.setOption(QtGui.QFileDialog.DontResolveSymlinks)
    file_dialog.setOption(QtGui.QFileDialog.DontUseNativeDialog)
    if not file_dialog.exec_():
        return
    path = file_dialog.selectedFiles()[0]
    project.saveAs(path)

