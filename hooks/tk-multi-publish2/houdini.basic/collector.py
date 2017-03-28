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
import hou

HookBaseClass = sgtk.get_hook_baseclass()


class HoudiniSessionCollector(HookBaseClass):
    """
    Collector that operates on the houdini session
    """

    def process_current_scene(self, parent_item):
        """
        Analyzes the current Houdini session and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """
        # create an item representing the current maya session
        item = self.collect_current_houdini_session(parent_item)

        # look for caches
        self.collect_alembic_caches(item)

    def collect_current_houdini_session(self, parent_item):
        """
        Creates an item that represents the current houdini session.

        :param parent_item: Parent Item instance
        :returns: Item of type maya.session
        """

        publisher = self.parent

        # get the path to the current file
        path = hou.hipFile.path()

        # determine the display name for the item
        if path:
            path = os.path.abspath(path)
            display_name = os.path.basename(path)
        else:
            display_name = "untitled.hip"
            # more pythonic empty file path
            path = None

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "houdini.file",
            "Current Houdini File",
            display_name
        )

        session_item.properties["path"] = path
        session_item.set_icon_from_path(publisher.get_icon_path("houdini"))

        return session_item

    def collect_alembic_caches(self, parent_item):
        """
        Creates items for all alembic output rops.

        :param parent_item: Parent Item instance
        :param str project_root: The houdini project root to search for alembics

        :returns: List of alembic cache items
        """

        # use the property on the parent to locate alembic caches
        items = []

        publisher = self.parent

        # get all rop/sop alembic nodes in the session
        alembic_nodes = hou.nodeType(
            hou.ropNodeTypeCategory(),
            "alembic"
        ).instances()

        publisher.logger.debug(
            "Found alembic nodes: %s" %
            ([n.path() for n in alembic_nodes])
        )

        for alembic_node in alembic_nodes:

            publisher.logger.debug(
                "Processing alembic node: %s" %
                (alembic_node.path(),)
            )

            # get the output cache path
            cache_path = alembic_node.parm("filename").eval()

            if os.path.exists(cache_path):
                publisher.logger.debug("Path exists: %s" % (cache_path,))

                node_name = alembic_node.name()

                # get file path parts for display
                file_info = publisher.util.get_file_path_components(cache_path)

                # create and populate the item
                item = parent_item.create_item(
                    "cache.alembic",
                    "Alembic Cache",
                    "%s > %s" % (node_name, file_info["filename_no_ext"])
                )
                item.properties["path"] = cache_path
                item.set_icon_from_path(publisher.get_icon_path("alembic"))
                items.append(item)
            else:
                publisher.logger.debug("Path doesn't exist: %s" % (cache_path,))

        return items







        publisher = self.parent

        # look for alembic files in the cache folder
        for filename in os.listdir(cache_dir):
            cache_path = os.path.join(cache_dir, filename)

            # ensure this is an alembic cache
            if not cache_path.endswith(".abc"):
                continue

            # get file path parts for display
            file_info = publisher.util.get_file_path_components(cache_path)

            # create and populate the item
            item = parent_item.create_item(
                "cache.alembic",
                "Alembic Cache",
                file_info["filename_no_ext"]
            )
            item.properties["path"] = cache_path
            item.set_icon_from_path(publisher.get_icon_path("alembic"))
            items.append(item)

        return items

