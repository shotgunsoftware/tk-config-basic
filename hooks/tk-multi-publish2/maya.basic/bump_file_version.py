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
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaBumpFileVersionPlugin(HookBaseClass):
    """
    Plugin for creating the next version of a file.
    """

    @property
    def session_path(self):
        """
        Returns the path to the current
        :return:
        """
        return cmds.file(query=True, sn=True)

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["maya.session"]

    def session_save_as(self, path):
        """
        A save as wrapper for the current session.

        :param path: Optional path to save the current session as.
        """

        if not path:
            path = cmds.fileDialog(
                mode=1, title="Save As", directoryMask='*.ma')

        if not path:
            # no path supplied and none returned via file dialog
            return

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
