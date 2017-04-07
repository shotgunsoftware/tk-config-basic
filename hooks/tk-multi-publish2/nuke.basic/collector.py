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
import nuke
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class NukeSessionCollector(HookBaseClass):
    """
    Collector that operates on the nuke session. Should inherit from the basic
    collector hook.
    """

    def process_current_scene(self, parent_item):
        """
        Analyzes the current session open in Nuke and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """

        publisher = self.parent

        # get the current path
        path = nuke.root().name()

        # determine the display name for the item
        if path:
            display_name = publisher.util.get_publish_name(path)
        else:
            display_name = "Current Nuke Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "nuke.session",
            "Nuke Script",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "nuke.png"
        )
        session_item.set_icon_from_path(icon_path)

        return session_item
