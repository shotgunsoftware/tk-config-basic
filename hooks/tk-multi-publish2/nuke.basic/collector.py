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

HookBaseClass = sgtk.get_hook_baseclass()


class NukeSessionCollector(HookBaseClass):
    """
    Collector that operates on the current nuke/nukestudio session. Should
    inherit from the basic collector hook.
    """

    def process_current_scene(self, parent_item):
        """
        Analyzes the current session open in Nuke/NukeStudio and parents a
        subtree of items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        publisher = self.parent
        engine = publisher.engine

        if hasattr(engine, "studio_enabled") and engine.studio_enabled:
            # running nuke studio
            self._process_current_nukestudio_session(parent_item)
        else:
            # running nuke
            self._process_current_nuke_session(parent_item)

    def _process_current_nuke_session(self, parent_item):
        """
        Analyzes the current session open in Nuke and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """

        import nuke

        publisher = self.parent

        # get the current path
        path = nuke.root().name()

        # determine the display name for the item
        if path and path != "Root":
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
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

    def _process_current_nukestudio_session(self, parent_item):
        """
        Analyzes the current session open in NukeStudio and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        import hiero.core

        # go ahead and build the path to the icon for use by any projects
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "nukestudio.png"
        )

        for project in hiero.core.projects():

            # create the session item for the publish hierarchy
            session_item = parent_item.create_item(
                "nukestudio.project",
                "Nuke Studio Project",
                project.name()
            )
            session_item.set_icon_from_path(icon_path)

            # add the project object to the properties so that the publish
            # plugins know which open project to associate with this item
            session_item.properties["project"] = project

        # TODO: only the current project should be enabled
        # get the active project. if it can be determined and matches this
        # item's project, then it should be enabled.
        #active_project = hiero.ui.activeSequence().project()
        #if active_project and active_project.guid() == project.guid():
            #enabled = True
