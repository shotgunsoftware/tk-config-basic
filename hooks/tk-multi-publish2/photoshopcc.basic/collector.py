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


class PhotoshopCCSceneCollector(HookBaseClass):
    """
    Collector that operates on the photoshop cc active document.
    """

    def process_current_scene(self, parent_item):
        """
        Analyzes the open documents in Photoshop and creates publish items
        parented under the supplied item.

        :param parent_item: Root item instance
        """

        # get a handle on the photoshop cc engine
        publisher = self.parent
        engine = publisher.engine

        engine.logger.debug(
            "Checking current PS session for items to publish...")

        # get the active document name
        try:
            active_doc_name = engine.adobe.app.activeDocument.name
        except RuntimeError:
            engine.logger.debug("No active document found.")
            active_doc_name = None

        items_to_create = []

        # iterate over all open documents and add them as publish items
        for document in engine.adobe.app.documents:

            engine.logger.debug(
                "Processing PS document: %s" % (document.name,))

            # now set the item's type icon to display in the hierarchy
            icon_path = publisher.get_icon_path("photoshop")

            # build a list of properties for use by matching plugins
            properties = dict(document=document)

            if active_doc_name and active_doc_name == document.name:
                # this is the active document. make sure it is checked and
                # expanded by default
                properties["default_checked"] = True
                properties["default_expanded"] = True
                is_active_doc = True
            else:
                # not the active document. uncheck and collapse by default
                properties["default_checked"] = False
                properties["default_expanded"] = False
                is_active_doc = False

            item_info = {
                "properties": properties,
                "icon_path": icon_path,
            }

            if is_active_doc:
                # make the active document show up first in the list
                items_to_create.insert(0, item_info)
            else:
                items_to_create.append(item_info)

        # now create the top-level items in the publish hierarchy
        for item_info in items_to_create:

            # create a publish item for the document
            document_item = parent_item.create_item(
                "photoshop.document",
                "Photoshop Document",
                item_info["properties"]["document"].name,
            )

            document_item.properties.update(item_info["properties"])
            document_item.set_icon_from_path(item_info["icon_path"])
