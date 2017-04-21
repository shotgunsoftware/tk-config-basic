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
import MaxPlus
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MaxSessionCollector(HookBaseClass):
    """
    Collector that operates on the max session. Should inherit from the basic
    collector hook.
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the current session open in Max and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        publisher = self.parent

        path = MaxPlus.FileManager.GetFileNameAndPath()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Max Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "3dsmax.session",
            "3dsmax Session",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "3dsmax.png"
        )
        session_item.set_icon_from_path(icon_path)

        self.logger.info("Collected current 3dsMax session")

        return session_item
