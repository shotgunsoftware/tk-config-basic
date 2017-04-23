# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import maya.cmds as cmds
import maya.mel as mel
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaEnsureSavedPlugin(HookBaseClass):
    """
    Plugin for publishing an open maya session.
    """

    @property
    def session_path(self):
        """
        Returns the path to the current
        :return:
        """
        return cmds.file(query=True, sn=True)

    @property
    def has_unsaved_changes(self):
        """
        Returns True if the session has unsaved changes, False otherwise.
        :return:
        """
        return cmds.file(q=True, modified=True)

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["maya.session"]

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

        # warn if the project root can't be determined
        project_root = cmds.workspace(q=True, rootDirectory=True)
        item.properties["project_root"] = project_root

        # warn if no project root could be determined.
        if not project_root:
            self.logger.warning(
                "Your session is not part of a maya project.",
                extra={
                    "action_button": {
                        "label": "Set Project",
                        "tooltip": "Set the maya project",
                        "callback": lambda: mel.eval('setProject ""')
                    }
                }
            )

        # rely on the base class session save plugin to do the rest
        return super(MayaEnsureSavedPlugin, self).validate(settings, item)

    def session_save_as(self):
        """
        Implements the base class abstract method to save the current maya
        session.

        :returns: The path of the saved session.
        """

        path = cmds.fileDialog(mode=1, title="Save As", directoryMask='*.ma')

        if not path:
            # no path supplied and none returned via file dialog
            return None

        # Maya can choose the wrong file type so we should set it here
        # explicitly based on the extension
        maya_file_type = None
        if path.lower().endswith(".ma"):
            maya_file_type = "mayaAscii"
        elif path.lower().endswith(".mb"):
            maya_file_type = "mayaBinary"

        cmds.file(rename=path)

        # save the scene:
        if maya_file_type:
            cmds.file(save=True, force=True, type=maya_file_type)
        else:
            cmds.file(save=True, force=True)

        return path
