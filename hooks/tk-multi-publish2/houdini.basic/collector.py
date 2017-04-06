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
        # create an item representing the current houdini session
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
            display_name = publisher.util.get_publish_name(path)
        else:
            display_name = "Current Houdini Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "houdini.session",
            "Current Houdini Session",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "houdini.png"
        )
        session_item.set_icon_from_path(icon_path)

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

            # ensure the alembic cache dir exists
            if not os.path.exists(cache_path):
                continue

            # do some early pre-processing to ensure the file is of the right
            # type. use the base class item info method to see what the item
            # type would be.
            item_info = self._get_item_info(cache_path)
            if item_info["item_type"] != "file.alembic":
                continue

            # allow the base class to collect and create the item. it knows how
            # to handle alembic files
            super(HoudiniSessionCollector, self).process_file(
                parent_item,
                cache_path
            )
