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
import maya.cmds as cmds
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaSessionCollector(HookBaseClass):
    """
    Collector that operates on the maya session. Should inherit from the basic
    collector hook.
    """

    def process_file(self, parent_item, path):
        """
        Analyzes the given file and creates one or more items to represent it.

        :param parent_item: Root item instance
        :param path: Path to analyze
        :returns: The main item that was created
        """

        # run base class logic to set basic properties for us
        item = super(MayaSessionCollector, self).process_file(parent_item, path)

        if item.type == "file.maya":

            publisher = self.parent
            file_info = publisher.util.get_file_path_components(path)

            # this is a maya file. see if we can find associated files to
            # publish from the project root
            folder = file_info["folder"]
            if os.path.basename(folder) == "scenes":

                # assume parent level is workspace root. add it to properties
                project_root = os.path.dirname(folder)
                item.properties["project_root"] = project_root

                # collect associated files
                self.collect_alembic_caches(item, project_root)
                self.collect_playblasts(item, project_root)

        return item

    def process_current_scene(self, parent_item):
        """
        Analyzes the current session open in Maya and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # create an item representing the current maya session
        item = self.collect_current_maya_session(parent_item)
        project_root = item.properties["project_root"]

        # if we can determine a project root, collect other files to publish
        if project_root:
            self.collect_playblasts(item, project_root)
            self.collect_alembic_caches(item, project_root)

    def collect_current_maya_session(self, parent_item):
        """
        Creates an item that represents the current maya session.

        :param parent_item: Parent Item instance
        :returns: Item of type maya.session
        """

        publisher = self.parent

        # get the path to the current file
        path = cmds.file(query=True, sn=True)

        # determine the display name for the item
        if path:
            display_name = publisher.util.get_publish_name(path)
        else:
            display_name = "Current Maya Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "maya.session",
            "Maya File",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "maya.png"
        )
        session_item.set_icon_from_path(icon_path)

        # discover the project root which helps in discovery of other
        # publishable items
        project_root = cmds.workspace(q=True, rootDirectory=True)
        session_item.properties["project_root"] = project_root

        return session_item

    def collect_alembic_caches(self, parent_item, project_root):
        """
        Creates items for alembic caches

        Looks for a 'project_root' property on the parent item, and if such
        exists, look for alembic caches in a 'cache/alembic' subfolder.

        :param parent_item: Parent Item instance
        :param str project_root: The maya project root to search for alembics
        """

        # ensure the alembic cache dir exists
        cache_dir = os.path.join(project_root, "cache", "alembic")
        if not os.path.exists(cache_dir):
            return

        # look for alembic files in the cache folder
        for filename in os.listdir(cache_dir):
            cache_path = os.path.join(cache_dir, filename)

            # do some early pre-processing to ensure the file is of the right
            # type. use the base class item info method to see what the item
            # type would be.
            item_info = self._get_item_info(filename)
            if item_info["item_type"] != "file.alembic":
                continue

            # allow the base class to collect and create the item. it knows how
            # to handle alembic files
            super(MayaSessionCollector, self).process_file(
                parent_item,
                cache_path
            )

    def collect_playblasts(self, parent_item, project_root):
        """
        Creates items for quicktime playblasts.

        Looks for a 'project_root' property on the parent item, and if such
        exists, look for movie files in a 'movies' subfolder.

        :param parent_item: Parent Item instance
        :param str project_root: The maya project root to search for playblasts
        """

        # ensure the movies dir exists
        movies_dir = os.path.join(project_root, "movies")
        if not os.path.exists(movies_dir):
            return

        # look for movie files in the movies folder
        for filename in os.listdir(movies_dir):

            # do some early pre-processing to ensure the file is of the right
            # type. use the base class item info method to see what the item
            # type would be.
            item_info = self._get_item_info(filename)
            if item_info["item_type"] != "file.video":
                continue

            movie_path = os.path.join(movies_dir, filename)

            # allow the base class to collect and create the item. it knows how
            # to handle movie files
            super(MayaSessionCollector, self).process_file(
                parent_item,
                movie_path
            )


